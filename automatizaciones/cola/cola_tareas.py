#!/usr/bin/env python3
"""Cola persistente de trabajo + ejecutor determinista (HomeLab).

Qué resuelve:
  * Cola en SQLite (sin servicios nuevos): tarea, proyecto, tipo, prioridad, dependencias,
    permisos, estado, criterio de aceptación y evidencia.
  * Reclamación ATÓMICA de una tarea (BEGIN IMMEDIATE + UPDATE ... RETURNING): dos ejecutores
    simultáneos no pueden llevarse la misma tarea.
  * Arriendo: una tarea 'en_curso' cuyo arriendo caduca se considera abandonada y vuelve a
    'pendiente' al arrancar (recuperación tras un reinicio o una caída).
  * Tareas bloqueadas NO consumen intentos ni llamadas: quedan en 'bloqueada' (dependencia sin
    cumplir) o 'esperando' (con hora de reintento) y el ejecutor las salta sin tocarlas.
  * Reglas deterministas: funciona sin Jev. `--con-jev` solo AÑADIRÍA una sugerencia de
    prioridad; por defecto está apagado y ninguna cifra simulada entra en conclusiones.

Detener el ejecutor: Ctrl+C o simplemente no ejecutarlo. La cola, los estados y la evidencia
viven en disco; al volver a ejecutar continúa donde estaba. Borrar `cola.db` es un reinicio
explícito del historial, no una parada normal.
"""
from __future__ import annotations
import datetime
import hashlib
import json
import os
import re
import shutil
import sqlite3
import ssl
import subprocess
import sys
import urllib.request

BASE = os.environ.get("COLA_BASE") or os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes", "automation", "cola")
DB = os.environ.get("COLA_DB") or os.path.join(BASE, "cola.db")
EVID = os.path.join(BASE, "evidencia")
ARRIENDO_S = int(os.environ.get("COLA_ARRIENDO_S", "300"))     # caducidad del arriendo
N8N_KEY = os.environ.get("N8N_API_KEY", "")

ESTADOS = ("pendiente", "en_curso", "hecha", "fallida", "bloqueada", "esperando")


def ahora() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _con() -> sqlite3.Connection:
    os.makedirs(BASE, exist_ok=True)
    c = sqlite3.connect(DB, isolation_level=None, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""CREATE TABLE IF NOT EXISTS tareas (
        id TEXT PRIMARY KEY, proyecto TEXT NOT NULL, titulo TEXT NOT NULL, tipo TEXT NOT NULL,
        prioridad INTEGER NOT NULL DEFAULT 50, depende_de TEXT, permisos TEXT NOT NULL DEFAULT 'local',
        estado TEXT NOT NULL DEFAULT 'pendiente', criterio TEXT NOT NULL,
        evidencia TEXT, motivo TEXT, intentos INTEGER NOT NULL DEFAULT 0,
        reclamada_por TEXT, reclamada_en TEXT, reintentar_en TEXT,
        creada_en TEXT, actualizada_en TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, tarea TEXT, tipo TEXT, detalle TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS ajustes (clave TEXT PRIMARY KEY, valor TEXT)""")
    return c


def ajuste(clave: str, valor: str = None, con=None):
    """Lee (valor=None) o escribe un ajuste de la cola."""
    propio = con is None
    c = con or _con()
    if valor is None:
        f = c.execute("SELECT valor FROM ajustes WHERE clave=?", (clave,)).fetchone()
        r = f["valor"] if f else None
    else:
        c.execute("INSERT INTO ajustes (clave,valor) VALUES (?,?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
                  (clave, valor))
        r = valor
    if propio:
        c.close()
    return r


def evento(c, tarea, tipo, detalle="") -> None:
    c.execute("INSERT INTO eventos (ts,tarea,tipo,detalle) VALUES (?,?,?,?)", (ahora(), tarea, tipo, detalle))


# ------------------------------------------------------------------ siembra
TAREAS_AUTORIZADAS = [
    dict(id="hl-backlog-proyectos", proyecto="proyectos", titulo="Backlog consolidado por proyecto desde GitHub",
         tipo="backlog_proyectos", prioridad=70, depende_de=None, permisos="lectura_red + escritura_tabla_n8n",
         criterio="el backlog se regenera con datos reales de GitHub (PR/issues abiertos), con origen, prioridad, "
                  "dependencia, criterio y ejecutor, y queda escrito en la tabla homelab_backlog con evidencia local",
         params={}),
    dict(id="hl-salud-kuma", proyecto="homelab", titulo="Salud de Uptime Kuma (443)", tipo="salud_servicio",
         prioridad=80, depende_de=None, permisos="lectura_red",
         criterio="responde la página de Kuma sin error de red",
         params={"url": "https://desktop-uu4cmub.tail4043e9.ts.net/", "codigos": [200, 302], "nombre": "Uptime Kuma"}),
    dict(id="hl-salud-n8n", proyecto="homelab", titulo="Salud de n8n (8443/healthz)", tipo="salud_servicio",
         prioridad=80, depende_de=None, permisos="lectura_red",
         criterio="healthz devuelve status ok",
         params={"url": "https://desktop-uu4cmub.tail4043e9.ts.net:8443/healthz", "codigos": [200],
                 "contiene": "ok", "nombre": "n8n"}),
    dict(id="hl-salud-hermes", proyecto="homelab", titulo="Salud del Hermes remoto (10000)", tipo="salud_servicio",
         prioridad=70, depende_de=None, permisos="lectura_red",
         criterio="api/health responde ok y auth_required",
         params={"url": "https://desktop-uu4cmub.tail4043e9.ts.net:10000/api/health", "codigos": [200],
                 "contiene": '"ok":true', "nombre": "Hermes remoto"}),
    dict(id="hl-salud-demos", proyecto="fluvia", titulo="Demos locales responden (3302/3322/3332/3382)",
         tipo="salud_servicio", prioridad=60, depende_de=None, permisos="lectura_red",
         criterio="las cuatro instancias devuelven 200 en /login",
         params={"url": "http://127.0.0.1:3302/login", "codigos": [200], "nombre": "demo 3302",
                 "ademas": ["http://127.0.0.1:3322/login", "http://127.0.0.1:3332/login", "http://127.0.0.1:3382/login"]}),
    dict(id="hl-respaldos", proyecto="homelab", titulo="Verificar que los respaldos existen y son legibles",
         tipo="verificar_respaldo", prioridad=70, depende_de=None, permisos="lectura_disco",
         criterio="los artefactos existen, son legibles y su hash queda registrado — NO es una restauración probada",
         params={"rutas": ["automation/github-pr-notifier.py", "automation/github_pr_fetch.py",
                           "docs/drafts/n8n-github-pr-avisos-v4.2.json", "automation/jev/jev_adapter.py",
                           "automation/jev/jev_eval_set.json"]}),
    dict(id="hl-config-snapshot", proyecto="homelab", titulo="Instantánea de la configuración de Hermes",
         tipo="respaldo_config", prioridad=65, depende_de=None, permisos="lectura_disco",
         criterio="se crea la copia con hash y su instrucción de restauración — restauración NO probada",
         params={"origen": "config.yaml", "destino": "docs/drafts/config-snapshots"}),
    dict(id="hl-restauracion-aislada", proyecto="homelab",
         titulo="Recuperación de artefactos en entorno aislado (no es restauración completa de n8n)",
         tipo="restauracion_aislada", prioridad=75, depende_de=None, permisos="lectura_disco",
         criterio="en un directorio temporal: el JSON exportado se parsea, el código de su nodo compila con node --check, "
                  "el estado restaurado del notificador alimenta una pasada en seco, y los originales quedan con el mismo hash. "
                  "ALCANCE: recuperación de artefactos de la MSI; la restauración completa de n8n (con su clave de cifrado y "
                  "credenciales) queda PENDIENTE y no se declara probada",
         params={}),
    dict(id="hl-validar-artefactos", proyecto="homelab", titulo="Validar artefactos de automatización",
         tipo="validar_artefactos", prioridad=72, depende_de=None, permisos="lectura_disco",
         criterio="todos los .py compilan, todos los .json parsean, la base pasa integrity_check y la evidencia parsea",
         params={}),
    dict(id="hl-cierre-pendientes", proyecto="homelab", titulo="Cerrar pendientes sin accesos ausentes",
         tipo="cierre_pendientes", prioridad=68, depende_de=None, permisos="lectura_disco",
         criterio="manifiesto de borradores obsoletos creado (sin borrar), 0 secretos detectados y rollback documentado",
         params={}),
    dict(id="hl-inspeccion-n8n", proyecto="homelab", titulo="Inspeccionar Triage/Controller y planificador n8n",
         tipo="inspeccionar_n8n", prioridad=90, depende_de=None, permisos="n8n:workflow:read",
         criterio="para cada workflow: disparador real, última ejecución, trabajo y próximo disparo",
         params={}),
    dict(id="hl-cierre-avisos", proyecto="homelab", titulo="Cerrar circuito de avisos (reutilizando lo existente)",
         tipo="inspeccionar_n8n", prioridad=85, depende_de="hl-inspeccion-n8n", permisos="n8n:workflow:write",
         criterio="un mensaje de prueba identificado llega al chat privado y se comprueba la recepción",
         params={}),
]


def sembrar() -> int:
    c = _con()
    nuevas = 0
    for t in TAREAS_AUTORIZADAS:
        existe = c.execute("SELECT 1 FROM tareas WHERE id=?", (t["id"],)).fetchone()
        if existe:
            continue
        c.execute("""INSERT INTO tareas (id, proyecto, titulo, tipo, prioridad, depende_de, permisos,
                     estado, criterio, creada_en, actualizada_en)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (t["id"], t["proyecto"], t["titulo"], t["tipo"], t["prioridad"], t["depende_de"],
                   t["permisos"], "pendiente", t["criterio"], ahora(), ahora()))
        # parámetros técnicos con su propio tipo de evento (no confundir con el título)
        c.execute("INSERT INTO eventos (ts,tarea,tipo,detalle) VALUES (?,?,?,?)",
                  (ahora(), t["id"], "parametros", json.dumps(t["params"], ensure_ascii=False)))
        evento(c, t["id"], "sembrada", t["titulo"])
        nuevas += 1
    print(f"  tareas sembradas: {nuevas} (ya existían {len(TAREAS_AUTORIZADAS) - nuevas})")
    c.close()
    return nuevas


# ------------------------------------------------------------------ recuperación
def recuperar_abandonadas() -> int:
    """Tareas en_curso cuyo arriendo caducó -> pendiente (recuperación tras caída/reinicio)."""
    c = _con()
    limite = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=ARRIENDO_S)).isoformat(timespec="seconds")
    filas = c.execute("SELECT id, reclamada_en, reclamada_por FROM tareas WHERE estado='en_curso' AND reclamada_en < ?",
                      (limite,)).fetchall()
    for f in filas:
        c.execute("UPDATE tareas SET estado='pendiente', reclamada_por=NULL, reclamada_en=NULL, actualizada_en=? WHERE id=?",
                  (ahora(), f["id"]))
        evento(c, f["id"], "recuperada", f"arriendo caducado (lo tenía {f['reclamada_por']} desde {f['reclamada_en']})")
        print(f"  recuperada: {f['id']} (abandonada por {f['reclamada_por']} el {f['reclamada_en']})")
    # desbloquear dependencias cumplidas y reintentos vencidos
    for f in c.execute("SELECT id, depende_de FROM tareas WHERE estado='bloqueada'").fetchall():
        if f["depende_de"]:
            dep = c.execute("SELECT estado FROM tareas WHERE id=?", (f["depende_de"],)).fetchone()
            if dep and dep["estado"] == "hecha":
                c.execute("UPDATE tareas SET estado='pendiente', motivo=NULL, actualizada_en=? WHERE id=?", (ahora(), f["id"]))
                evento(c, f["id"], "desbloqueada", f"dependencia {f['depende_de']} cumplida")
                print(f"  desbloqueada: {f['id']}")
    for f in c.execute("SELECT id FROM tareas WHERE estado='esperando' AND reintentar_en <= ?", (ahora(),)).fetchall():
        c.execute("UPDATE tareas SET estado='pendiente', reintentar_en=NULL, actualizada_en=? WHERE id=?", (ahora(), f["id"]))
        evento(c, f["id"], "reintento_listo", "hora de reintento alcanzada")
    c.close()
    return len(filas)


# ------------------------------------------------------------------ reclamación atómica
def reclamar(ejecutor: str):
    c = _con()
    try:
        c.execute("BEGIN IMMEDIATE")
        fila = c.execute("""SELECT id FROM tareas
                            WHERE estado='pendiente'
                              AND (depende_de IS NULL OR depende_de IN (SELECT id FROM tareas WHERE estado='hecha'))
                            ORDER BY prioridad DESC, creada_en ASC LIMIT 1""").fetchone()
        if not fila:
            c.execute("COMMIT")
            return None
        tid = fila["id"]
        cur = c.execute("""UPDATE tareas SET estado='en_curso', reclamada_por=?, reclamada_en=?,
                           intentos=intentos+1, actualizada_en=? WHERE id=? AND estado='pendiente'
                           RETURNING id, tipo, titulo, criterio, intentos""",
                        (ejecutor, ahora(), ahora(), tid))
        t = cur.fetchone()
        c.execute("COMMIT")
        if t:
            evento(c, tid, "reclamada", f"intento {t['intentos']} por {ejecutor}")
            return dict(t)
        return None
    except Exception:
        try:
            c.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        c.close()


def cerrar(tid: str, estado: str, evidencia: str = "", motivo: str = "", reintentar_en: str = None) -> None:
    assert estado in ESTADOS, estado
    c = _con()
    c.execute("""UPDATE tareas SET estado=?, evidencia=?, motivo=?, reintentar_en=?, reclamada_por=NULL,
                 reclamada_en=NULL, actualizada_en=? WHERE id=?""",
              (estado, evidencia, motivo, reintentar_en, ahora(), tid))
    evento(c, tid, estado, (motivo or evidencia or "")[:200])
    c.close()


# ------------------------------------------------------------------ manejadores (deterministas)
def _http(url: str, timeout=12):
    ctx = ssl._create_unverified_context()      # certificado del tailnet
    req = urllib.request.Request(url, headers={"User-Agent": "hermes-cola/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read(400).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001
        return 0, str(e)[:120]


def h_salud_servicio(params: dict) -> tuple:
    urls = [params["url"]] + list(params.get("ademas") or [])
    detalles, ok = [], True
    for u in urls:
        codigo, cuerpo = _http(u)
        bien = codigo in params["codigos"] and (params.get("contiene", "") in cuerpo)
        ok &= bien
        detalles.append({"url": u, "codigo": codigo, "cumple": bien,
                         "muestra": (cuerpo[:80] if cuerpo else "")})
    return ok, {"comprobaciones": detalles}


def h_verificar_respaldo(params: dict) -> tuple:
    raiz = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes")
    res, ok = [], True
    for rel in params["rutas"]:
        p = os.path.join(raiz, rel.replace("/", os.sep))
        if os.path.isfile(p):
            h = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
            res.append({"ruta": rel, "bytes": os.path.getsize(p), "sha256_16": h, "legible": True})
        else:
            res.append({"ruta": rel, "existe": False})
            ok = False
    return ok, {"artefactos": res}


def h_respaldo_config(params: dict) -> tuple:
    raiz = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes")
    origen = os.path.join(raiz, params["origen"])
    destino = os.path.join(raiz, params["destino"].replace("/", os.sep))
    os.makedirs(destino, exist_ok=True)
    sello = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    copia = os.path.join(destino, f"config-{sello}.yaml")
    shutil.copy2(origen, copia)
    h = hashlib.sha256(open(copia, "rb").read()).hexdigest()
    with open(os.path.join(destino, f"config-{sello}.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Instantánea de configuración\n\ncopia: {os.path.basename(copia)}\nsha256: {h}\n"
                 f"momento: {sello}\n\nRestaurar (rollback de cualquier hook futuro):\n"
                 f"    copy /Y \"{copia}\" \"{origen}\"\n")
    return True, {"copia": copia, "sha256": h}


def h_inspeccionar_n8n(params: dict) -> tuple:
    if not N8N_KEY:
        return "bloqueada", {"accion_unica": "crear la clave de API en "
                            "https://desktop-uu4cmub.tail4043e9.ts.net:8443/settings/api (Settings → n8n API) "
                            "con solo-lectura de workflows y ejecuciones, y guardarla como variable de entorno del usuario",
                            "no_consumir_calls": True}
    req = urllib.request.Request("https://desktop-uu4cmub.tail4043e9.ts.net:8443/api/v1/workflows?limit=50",
                                 headers={"X-N8N-API-KEY": N8N_KEY, "User-Agent": "hermes-cola/1"})
    try:
        with urllib.request.urlopen(req, timeout=20, context=ssl._create_unverified_context()) as r:
            datos = json.loads(r.read().decode("utf-8", "replace"))
        wfs = [{"nombre": w.get("name"), "activo": w.get("active"), "id": w.get("id"),
                "disparadores": [n.get("type") for n in (w.get("nodes") or []) if "trigger" in str(n.get("type"))]}
               for w in (datos.get("data") or [])]
        return True, {"workflows": wfs}
    except Exception as e:  # noqa: BLE001
        return False, {"error": str(e)[:140]}


def h_restauracion_aislada(params: dict) -> tuple:
    """Restauración real en entorno aislado: no toca los originales (se verifica el hash)."""
    import tempfile
    raiz = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes")
    wf = os.path.join(raiz, "docs", "drafts", "n8n-github-pr-avisos-v4.2.json")
    estado = os.path.join(raiz, "automation", "github-notifier-state.json")
    ntf = os.path.join(raiz, "automation", "github-pr-notifier.py")
    firma = {p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:16] for p in (wf, estado, ntf) if os.path.isfile(p)}
    pasos, ok = [], True
    with tempfile.TemporaryDirectory(prefix="restaura-") as td:
        # 1) el artefacto exportado se restaura y su código compila
        copia = os.path.join(td, "flujo.json")
        shutil.copy2(wf, copia)
        try:
            flujo = json.load(open(copia, encoding="utf-8"))
            nodo = next(n for n in flujo["nodes"] if n["type"] == "n8n-nodes-base.code")
            js = os.path.join(td, "nodo.js")
            open(js, "w", encoding="utf-8").write(nodo["parameters"]["jsCode"])
            r = subprocess.run(["node", "--check", js], capture_output=True, text=True)
            pasos.append({"paso": "workflow exportado restaurado y código del nodo compila",
                          "ok": r.returncode == 0, "detalle": (r.stderr or "")[:120]})
            ok &= r.returncode == 0
            pasos.append({"paso": "nodos del flujo", "ok": True,
                          "detalle": f"{len(flujo['nodes'])} nodos, activo={flujo.get('active')}"})
        except Exception as e:  # noqa: BLE001
            pasos.append({"paso": "workflow exportado", "ok": False, "detalle": str(e)[:120]})
            ok = False
        # 2) el estado del notificador se restaura en un entorno aislado y se usa en seco
        try:
            copia_estado = os.path.join(td, "estado.json")
            shutil.copy2(estado, copia_estado)
            env = dict(os.environ, NTF_STATE=copia_estado)
            r = subprocess.run([sys.executable, ntf, "--show-state"], capture_output=True, text=True, env=env, timeout=60)
            pasos.append({"paso": "estado restaurado del notificador se carga y resume",
                          "ok": r.returncode == 0, "detalle": (r.stdout or r.stderr).strip()[:110]})
            ok &= r.returncode == 0
        except Exception as e:  # noqa: BLE001
            pasos.append({"paso": "estado restaurado", "ok": False, "detalle": str(e)[:120]})
            ok = False
    firma2 = {p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:16] for p in firma}
    intactos = firma == firma2
    pasos.append({"paso": "originales intactos tras la prueba", "ok": intactos, "detalle": json.dumps(firma)})
    return (ok and intactos), {"pasos": pasos, "originales": firma}


def h_validar_artefactos(params: dict) -> tuple:
    raiz = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes")
    py_ok, py_mal, js_ok, js_mal = [], [], [], []
    for base, _, ficheros in os.walk(os.path.join(raiz, "automation")):
        for f in ficheros:
            p = os.path.join(base, f)
            if f.endswith(".py"):
                r = subprocess.run([sys.executable, "-m", "py_compile", p], capture_output=True, text=True)
                (py_ok if r.returncode == 0 else py_mal).append(os.path.relpath(p, raiz))
            elif f.endswith(".json"):
                try:
                    json.load(open(p, encoding="utf-8"))
                    js_ok.append(os.path.relpath(p, raiz))
                except Exception:
                    js_mal.append(os.path.relpath(p, raiz))
    c = sqlite3.connect(DB)
    integridad = c.execute("PRAGMA integrity_check").fetchone()[0]
    tareas = c.execute("SELECT count(*) FROM tareas").fetchone()[0]
    c.close()
    evid_mal = []
    ev = os.path.join(raiz, "automation", "cola", "evidencia")
    for f in os.listdir(ev) if os.path.isdir(ev) else []:
        if f.endswith(".json"):
            try:
                json.load(open(os.path.join(ev, f), encoding="utf-8"))
            except Exception:
                evid_mal.append(f)
    ok = (not py_mal) and (not js_mal) and integridad == "ok" and not evid_mal
    return ok, {"python_ok": len(py_ok), "python_mal": py_mal, "json_ok": len(js_ok), "json_mal": js_mal,
                "integridad_base": integridad, "tareas_en_base": tareas, "evidencia_mal": evid_mal}


def h_cierre_pendientes(params: dict) -> tuple:
    raiz = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes")
    drafts = os.path.join(raiz, "docs", "drafts")
    obsoletos = sorted(f for f in os.listdir(drafts) if "SUPERADO" in f.upper())
    manifiesto = os.path.join(drafts, "borradores-obsoletos.md")
    with open(manifiesto, "w", encoding="utf-8") as fh:
        fh.write("# Borradores obsoletos identificados (NO se borra nada)\n\n")
        for f in obsoletos:
            fh.write(f"- {f}\n")
        fh.write("\nSustituidos por: n8n-github-pr-avisos-v4.2.json (vigente).\n")
    patron = re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}|sk-[A-Za-z0-9]{20,}|\b\d{8,10}:[A-Za-z0-9_-]{30,}")
    marcadores_sinteticos = ("ABCDEF", "012345", "EJEMPLO", "XXXX", "secreto1234")
    hallazgos, revisar = [], []
    for base, _, ficheros in os.walk(os.path.join(raiz, "automation")):
        for f in ficheros:
            if f.endswith((".py", ".json", ".md", ".log")):
                p = os.path.join(base, f)
                try:
                    for i, linea in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
                        m = patron.search(linea)
                        if not m:
                            continue
                        etiqueta = "sintético (valor de ejemplo para probar el saneado)" \
                            if any(k in m.group(0).upper() for k in marcadores_sinteticos) else "REVISAR"
                        reg = {"fichero": os.path.relpath(p, raiz), "linea": i, "coincidencia": m.group(0)[:12] + "…",
                               "veredicto": etiqueta}
                        hallazgos.append(reg)
                        if etiqueta == "REVISAR":
                            revisar.append(reg)
                except Exception:
                    pass
    doc = open(os.path.join(raiz, "docs", "drafts", "homelab-cierre-automatizaciones.md"), encoding="utf-8").read().lower()
    rollback_doc = ("reinicio explícito del historial" in doc or "reinicio explícito del historial" in doc) and ("conserva" in doc)
    ok = (not revisar) and rollback_doc
    return ok, {"manifiesto": os.path.relpath(manifiesto, raiz), "obsoletos": len(obsoletos),
                "hallazgos": hallazgos, "sin_explicar": revisar, "rollback_documentado": rollback_doc}


def h_backlog_proyectos(params: dict) -> tuple:
    """Ejecuta el constructor de backlog real (solo lectura de GitHub + escritura en la tabla de n8n)."""
    guion = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backlog", "backlog_proyectos.py")
    r = subprocess.run([sys.executable, guion], capture_output=True, text=True, timeout=900)
    salida = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"insertedRows\D+(\d+)", salida)
    resumen = [l.strip() for l in salida.splitlines() if re.match(r"^\s{2}\S+\s+\d+ elementos", l)]
    ok = r.returncode == 0 and bool(m)
    return ok, {"inseridas": int(m.group(1)) if m else 0, "proyectos": resumen[:10],
                "codigo_salida": r.returncode, "cola_de_la_salida": salida[-400:]}


MANEJADORES = {"salud_servicio": h_salud_servicio, "verificar_respaldo": h_verificar_respaldo,
               "respaldo_config": h_respaldo_config, "inspeccionar_n8n": h_inspeccionar_n8n,
               "restauracion_aislada": h_restauracion_aislada, "validar_artefactos": h_validar_artefactos,
               "cierre_pendientes": h_cierre_pendientes,
               "backlog_proyectos": h_backlog_proyectos}


def marcar_bloqueadas() -> int:
    """Tareas 'pendiente' cuya dependencia no está hecha -> 'bloqueada'. NO consumen intentos."""
    c = _con()
    filas = c.execute("""SELECT id, depende_de FROM tareas
                         WHERE estado='pendiente' AND depende_de IS NOT NULL
                           AND depende_de NOT IN (SELECT id FROM tareas WHERE estado='hecha')""").fetchall()
    for f in filas:
        dep = c.execute("SELECT estado FROM tareas WHERE id=?", (f["depende_de"],)).fetchone()
        c.execute("UPDATE tareas SET estado='bloqueada', motivo=?, actualizada_en=? WHERE id=?",
                  (f"espera a {f['depende_de']} (estado {dep['estado'] if dep else 'inexistente'})", ahora(), f["id"]))
        evento(c, f["id"], "bloqueada", f"dependencia {f['depende_de']} sin cumplir (sin gastar intentos)")
        print(f"  bloqueada sin gastar intentos: {f['id']} (espera a {f['depende_de']})")
    c.close()
    return len(filas)


def ejecutar(max_tareas: int = 10, con_jev: bool = False, ejecutor: str = None) -> int:
    ejecutor = ejecutor or f"{os.uname().nodename if hasattr(os, 'uname') else 'msi'}:{os.getpid()}"
    os.makedirs(EVID, exist_ok=True)
    marcar_bloqueadas()
    recuperar_abandonadas()
    hechas = 0
    for _ in range(max_tareas):
        t = reclamar(ejecutor)
        if not t:
            break
        params = {}
        c = _con()
        ev = c.execute("SELECT detalle FROM eventos WHERE tarea=? AND tipo='parametros' ORDER BY id DESC LIMIT 1",
                       (t["id"],)).fetchone()
        c.close()
        if ev and ev["detalle"]:
            try:
                params = json.loads(ev["detalle"])
            except Exception:
                params = {}
        manejador = MANEJADORES.get(t["tipo"])
        if not manejador:
            cerrar(t["id"], "fallida", motivo=f"sin manejador para tipo {t['tipo']}")
            continue
        try:
            res = manejador(params)
        except Exception as e:  # noqa: BLE001
            cerrar(t["id"], "esperando", motivo=f"error: {str(e)[:120]}",
                   reintentar_en=(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)).isoformat(timespec="seconds"))
            continue
        estado = "hecha" if res[0] is True else ("bloqueada" if res[0] == "bloqueada" else "fallida")
        detalle = res[1] if isinstance(res[1], dict) else {"detalle": str(res[1])}
        ruta = os.path.join(EVID, f"{t['id']}-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')}.json")
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump({"tarea": t["id"], "titulo": t["titulo"], "criterio": t["criterio"],
                       "estado": estado, "cuando": ahora(), "ejecutor": ejecutor,
                       "resultado": detalle}, fh, ensure_ascii=False, indent=1)
        motivo = ""
        reintentar = None
        if estado == "bloqueada":
            motivo = detalle.get("accion_unica", "bloqueada")
            # no consume reintentos: no vuelve a 'pendiente'
        elif estado == "fallida":
            reintentar = None
        cerrar(t["id"], estado, evidencia=os.path.relpath(ruta, BASE), motivo=motivo, reintentar_en=reintentar)
        hechas += 1
        print(f"  [{estado:9}] {t['id']:20} {t['titulo'][:52]}  -> {os.path.basename(ruta)}")
        if estado == "bloqueada":
            print(f"             bloqueo: {motivo[:110]}")
    return hechas


# ------------------------------------------------------------------ generación y programación
PERIODOS_MIN = {"backlog_proyectos": 360, "salud_servicio": 30, "verificar_respaldo": 1440, "respaldo_config": 10080}
LOG_PROG = os.path.join(BASE, "programador.log")
TAREA_WINDOWS = "Hermes-Cola-HomeLab"


def _insertar(c, t, tid=None) -> None:
    tid = tid or t["id"]
    c.execute("""INSERT INTO tareas (id, proyecto, titulo, tipo, prioridad, depende_de, permisos,
                 estado, criterio, creada_en, actualizada_en) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
              (tid, t["proyecto"], t["titulo"], t["tipo"], t["prioridad"], t["depende_de"],
               t["permisos"], "pendiente", t["criterio"], ahora(), ahora()))
    c.execute("INSERT INTO eventos (ts,tarea,tipo,detalle) VALUES (?,?,?,?)",
              (ahora(), tid, "parametros", json.dumps(t["params"], ensure_ascii=False)))
    evento(c, tid, "generada", t["titulo"])


def generar() -> int:
    """Próximas tareas: una instancia por ventana de tiempo para las periódicas, y las únicas que falten.

    Evita duplicados por construcción: el id lleva la ventana (`base@ventana`) y además se comprueba
    que no haya ya una instancia pendiente del mismo servicio.
    """
    c = _con()
    creadas = 0
    for t in TAREAS_AUTORIZADAS:
        periodos = PERIODOS_MIN.get(t["tipo"])
        if not periodos:
            if not c.execute("SELECT 1 FROM tareas WHERE id=?", (t["id"],)).fetchone():
                _insertar(c, t)
                creadas += 1
            continue
        ventana = int(datetime.datetime.now(datetime.timezone.utc).timestamp() // (periodos * 60))
        tid = f"{t['id']}@{ventana}"
        if c.execute("SELECT 1 FROM tareas WHERE id=?", (tid,)).fetchone():
            continue                                     # ya generada en esta ventana
        encurso = c.execute("SELECT 1 FROM tareas WHERE id LIKE ? AND estado IN ('pendiente','en_curso','esperando')",
                            (t["id"] + "@%",)).fetchone()
        if encurso:
            continue                                     # ya hay una pendiente de este servicio
        _insertar(c, t, tid)
        creadas += 1
    for t in TAREAS_AUTORIZADAS:                         # textos de criterio al día
        c.execute("UPDATE tareas SET criterio=? WHERE id=? AND criterio<>?", (t["criterio"], t["id"], t["criterio"]))
    c.close()
    return creadas


def registrar(msg: str) -> None:
    os.makedirs(BASE, exist_ok=True)
    with open(LOG_PROG, "a", encoding="utf-8") as fh:
        fh.write(f"{ahora()} {msg}\n")


def ciclo() -> int:
    """Una pasada del PROGRAMADOR: genera lo siguiente y ejecuta. Un solo programador por cola."""
    quien = ajuste("programador") or "local"
    if quien != "local":
        registrar(f"ciclo omitido: el programador designado es '{quien}' (no se crean dos)")
        print(f"  programador designado: {quien}; el ejecutor local no actúa (evita dos programadores)")
        return 0
    n = generar()
    registrar(f"ciclo del programador: {n} tareas generadas; arrancando ejecución")
    print(f"  generadas {n} tareas; ejecutando (disparo del programador)")
    hecho = ejecutar(max_tareas=5, ejecutor="programador-local")
    registrar(f"ciclo terminado: {hecho} tareas procesadas")
    return 0


def programar(minutos: int = 15) -> int:
    ajuste("programador", "local")
    cmd = f'"{sys.executable}" "{os.path.abspath(__file__)}" ciclo'
    p = subprocess.run(["schtasks", "/Create", "/TN", TAREA_WINDOWS, "/SC", "MINUTE", "/MO", str(minutos),
                        "/TR", cmd, "/F"], capture_output=True, text=True, encoding="cp850", errors="replace")
    salida = (p.stdout or p.stderr).strip().splitlines()
    print("  ", salida[-1] if salida else "(sin salida)")
    registrar(f"programador local registrado: cada {minutos} min como '{TAREA_WINDOWS}'")
    return 0 if p.returncode == 0 else 1


def desprogramar() -> int:
    p = subprocess.run(["schtasks", "/Delete", "/TN", TAREA_WINDOWS, "/F"], capture_output=True, text=True)
    registrar("programador local retirado; la cola, los pendientes y la configuración se conservan")
    salida = (p.stdout or p.stderr).strip().splitlines()
    print("  ", salida[-1] if salida else "(sin salida)")
    return 0 if p.returncode == 0 else 1


def estado() -> int:
    c = _con()
    filas = c.execute("SELECT * FROM tareas ORDER BY prioridad DESC, id").fetchall()
    print("  id                    prio estado      intentos depende_de           título")
    for f in filas:
        print(f"  {f['id']:20} {f['prioridad']:4} {f['estado']:11} {f['intentos']:8} {str(f['depende_de'] or '-'):20} {f['titulo'][:44]}")
    pend = sum(1 for f in filas if f["estado"] in ("pendiente", "esperando"))
    print(f"  total {len(filas)} · pendientes/esperando {pend} · evidencia en {os.path.relpath(EVID, BASE)}")
    c.close()
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "estado":
        sys.exit(estado())
    if a[0] == "sembrar":
        sys.exit(0 if sembrar() >= 0 else 1)
    if a[0] == "recuperar":
        recuperar_abandonadas()
        sys.exit(estado())
    if a[0] == "ejecutar":
        n = int(a[a.index("--max") + 1]) if "--max" in a else 10
        sys.exit(0 if ejecutar(max_tareas=n, con_jev="--con-jev" in a) >= 0 else 1)
    if a[0] == "generar":
        print(f"  tareas generadas: {generar()}")
        sys.exit(estado())
    if a[0] == "ciclo":
        sys.exit(ciclo())
    if a[0] == "programar":
        sys.exit(programar(int(a[1]) if len(a) > 1 and a[1].isdigit() else 15))
    if a[0] == "desprogramar":
        sys.exit(desprogramar())
    if a[0] == "programador":
        ajuste("programador", a[1] if len(a) > 1 else "local")
        print(f"  programador designado: {ajuste('programador')} (solo uno actúa sobre esta cola)")
        sys.exit(0)
    if a[0] == "caida-simulada":       # deja una tarea con arriendo viejo (prueba de recuperación)
        tid = a[1]
        c = _con()
        viejo = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=ARRIENDO_S + 600)).isoformat(timespec="seconds")
        c.execute("UPDATE tareas SET estado='en_curso', reclamada_por='proceso-caido', reclamada_en=? WHERE id=?", (viejo, tid))
        evento(c, tid, "caida_simulada", "arriendo antiguo dejado a propósito")
        print(f"  {tid} queda 'en_curso' con arriendo de {viejo} (como si el proceso hubiera muerto)")
        c.close()
        sys.exit(0)
    print("uso: cola_tareas.py [estado|sembrar|recuperar|ejecutar [--max N] [--con-jev]|caida-simulada <id>]")
    sys.exit(2)
