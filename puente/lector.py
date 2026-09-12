#!/usr/bin/env python3
"""Lector y ejecutor local del puente GitHub <-> Hermes (issue #3).

Cambios de esta versión (v2) respecto a la primera entrega:

  1. AUTENTICACIÓN VERIFICABLE. Las órdenes llevan firma HMAC-SHA256 con un
     secreto que nunca toca GitHub (`auth.py`). El autor de un comentario no
     autentica nada; la firma sí. Sin firma válida no se ejecuta.
  2. ESTADO PERSISTIDO ANTES DE EJECUTAR. La orden se marca `en_curso` y se
     escribe a disco ANTES de lanzar nada. Si el proceso muere a mitad, la
     siguiente pasada ve la orden huérfana y la deja BLOQUEADA en vez de
     repetirla (un efecto externo incierto no se reintenta a ciegas).
  3. RECONCILIACIÓN DE PUBLICACIONES. Acuse y resultado se encolan en un buzón
     de salida. Si publicar falla o el proceso muere antes de confirmar, la
     siguiente pasada lo reintenta, y antes de publicar comprueba por marca si el
     comentario YA existe: nunca se duplica.
  4. COLA POR LÍMITE. Si se alcanza el presupuesto diario o el máximo de órdenes,
     la orden NO se descarta: queda en cola y se retoma al día siguiente. El
     límite se reinicia a medianoche de America/New_York.

El lector sigue sin usar LLM en el sondeo: sin novedades no imprime nada. El
gasto solo puede ocurrir en la acción `tarea_local`, con presupuesto explícito.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auth  # noqa: E402
import auth_ssh  # noqa: E402
import presupuesto  # noqa: E402

BASE = Path(os.environ.get("PUENTE_HOME", Path.home() / ".hermes" / "bridge"))
CONFIG_PATH = BASE / "config.json"
ESTADO_PATH = BASE / "estado.json"
LIBRO_PATH = BASE / "presupuesto.json"
LOCK_PATH = BASE / ".lock"
LOG_DIR = BASE / "logs"

MARCADOR_PROPIO = "<!-- hermes-puente:v1"
RE_ORDEN = re.compile(r"```hermes-order\s*\n(.*?)\n```", re.DOTALL)
GH_EXE_WINDOWS = "/mnt/c/Program Files/GitHub CLI/gh.exe"

ACCIONES_INOCUAS = {"ping", "tarea_local"}

# Prompt FIJO del ejecutor: deliberadamente escrito en el código y sin
# parámetros del comentario. Permitir texto arbitrario convertiría el puente en
# un ejecutor de órdenes libres, que es justo lo prohibido.
PROMPT_TAREA_LOCAL = (
    "Tarea local pequena y reversible del puente de supervision. Responde SOLO con una "
    "frase que indique: la fecha y hora UTC actual y la version de Python del interprete. "
    "No uses ninguna herramienta, no escribas ficheros y no hagas peticiones de red."
)


def log(msg: str, verbose: bool = True) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    linea = f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}\n"
    try:
        with (LOG_DIR / f"{date.today().isoformat()}.log").open("a", encoding="utf-8") as fh:
            fh.write(linea)
    except OSError:
        pass
    if verbose:
        print(linea, end="")


def cargar_json(path: Path, defecto: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(defecto)


def guardar_json_atomico(path: Path, datos: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(datos, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class Transporte:
    """Acceso a GitHub sin crear credenciales nuevas."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        if shutil.which("gh"):
            self.modo, self.base = "gh", ["gh"]
        elif Path(GH_EXE_WINDOWS).exists():
            self.modo, self.base = "gh.exe", [GH_EXE_WINDOWS]
        elif os.environ.get("GH_TOKEN"):
            self.modo, self.base = "curl", []
        else:
            self.modo, self.base = "ninguno", []

    def disponible(self) -> bool:
        return self.modo != "ninguno"

    def api(self, endpoint: str, metodo: str = "GET", cuerpo: dict | None = None,
            paginar: bool = False) -> object:
        if self.modo in ("gh", "gh.exe"):
            args = self.base + ["api", endpoint, "--method", metodo]
            if paginar:
                args += ["--paginate"]
            if cuerpo is not None:
                args += ["--input", "-"]
                proc = subprocess.run(args, input=json.dumps(cuerpo), capture_output=True, text=True, timeout=90)
            else:
                proc = subprocess.run(args, capture_output=True, text=True, timeout=90)
            if proc.returncode != 0:
                raise RuntimeError(f"gh fallo ({proc.returncode}): {proc.stderr.strip()[:300]}")
            salida = proc.stdout.strip()
            if not salida:
                return None
            if paginar and salida.startswith("["):
                trozos, buf, prof = [], "", 0
                for ch in salida:
                    buf += ch
                    if ch in "[{":
                        prof += 1
                    elif ch in "]}":
                        prof -= 1
                        if prof == 0:
                            trozos.append(json.loads(buf))
                            buf = ""
                if trozos and all(isinstance(t, list) for t in trozos):
                    return [e for t in trozos for e in t]
                return trozos[0] if trozos else []
            return json.loads(salida)

        token = os.environ.get("GH_TOKEN", "")
        url = f"https://api.github.com/{endpoint.lstrip('/')}"
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = urllib.request.Request(url, data=datos, method=metodo)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "hermes-puente-local")
        if datos:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode() or "null")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"GitHub HTTP {e.code} en {endpoint}") from None


def comentarios(t: Transporte, repo: str, issue: int, desde_id: int | None) -> list[dict]:
    endpoint = f"repos/{repo}/issues/{issue}/comments?per_page=100&sort=created&direction=asc"
    datos = t.api(endpoint, paginar=True)
    if not isinstance(datos, list):
        return []
    if desde_id is None:
        return datos
    return [c for c in datos if int(c.get("id", 0)) > desde_id]


def parsear_orden(cuerpo: str) -> dict | None:
    m = RE_ORDEN.search(cuerpo or "")
    if not m:
        return None
    try:
        datos = json.loads(m.group(1))
    except json.JSONDecodeError:
        return {"_invalida": "JSON no parseable dentro del bloque hermes-order"}
    if not isinstance(datos, dict):
        return {"_invalida": "el bloque hermes-order debe contener un objeto JSON"}
    for k in ("id_orden", "tipo", "accion"):
        if k not in datos:
            return {"_invalida": f"faltan campos obligatorios: {k}"}
    if datos.get("tipo") != "orden":
        return {"_invalida": f"tipo no soportado: {datos.get('tipo')!r}"}
    return datos


# --------------------------------------------------------------- publicaciones
def marca_pub(pub_id: str) -> str:
    return f"{MARCADOR_PROPIO} pub={pub_id} -->"


def ya_publicado(t: Transporte, repo: str, issue: int, pub_id: str) -> bool:
    """Reconciliación: ¿este comentario ya se publicó? (evita duplicados)."""
    try:
        existentes = t.api(f"repos/{repo}/issues/{issue}/comments?per_page=100", paginar=True)
    except RuntimeError:
        return False
    if not isinstance(existentes, list):
        return False
    return any(f"pub={pub_id}" in (c.get("body") or "") for c in existentes)


def encolar_publicacion(estado: dict, repo: str, issue: int, pub_id: str, cuerpo: str) -> None:
    if any(p["pub_id"] == pub_id for p in estado["publicaciones_pendientes"]):
        return
    estado["publicaciones_pendientes"].append({
        "pub_id": pub_id, "repo": repo, "issue": issue, "cuerpo": cuerpo,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "intentos": 0,
    })


def vaciar_publicaciones(t: Transporte, estado: dict, dry_run: bool, verbose: bool) -> int:
    """Reintenta el buzón de salida. Devuelve cuántas se publicaron."""
    if dry_run:
        return 0
    pendientes, hechas = estado["publicaciones_pendientes"], 0
    restantes = []
    for pub in pendientes:
        if ya_publicado(t, pub["repo"], pub["issue"], pub["pub_id"]):
            log(f"publicación {pub['pub_id']} ya estaba en GitHub: reconciliada", verbose)
            hechas += 1
            continue
        try:
            t.api(f"repos/{pub['repo']}/issues/{pub['issue']}/comments", "POST",
                  cuerpo={"body": f"{pub['cuerpo']}\n\n{marca_pub(pub['pub_id'])}"})
            hechas += 1
            log(f"publicación {pub['pub_id']} enviada", verbose)
        except RuntimeError as e:
            pub["intentos"] += 1
            restantes.append(pub)
            log(f"publicación {pub['pub_id']} falló (intento {pub['intentos']}): {e}", True)
    estado["publicaciones_pendientes"] = restantes
    return hechas


# ------------------------------------------------------------------ ejecución
def ejecutar_accion(accion: str, config: dict, libro: dict, estado: dict) -> dict:
    """Resuelve una acción contra un enumerado CERRADO. Nada de shell libre."""
    permitidas = set(config.get("acciones_permitidas", [])) & ACCIONES_INOCUAS
    if accion not in permitidas:
        return {"ejecutada": False, "motivo": f"accion {accion!r} no está en la allowlist"}

    if accion == "ping":
        return {"ejecutada": True, "coste_usd": 0.0, "resultado": {
            "pong": True, "hostname": os.uname().nodename, "python": sys.version.split()[0],
            "ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}}

    if accion == "tarea_local":
        limites = config.get("limites", {})
        if not limites.get("worker_llm_habilitado"):
            return {"ejecutada": False, "motivo": "el ejecutor con LLM está en pausa"}
        limite = limites.get("presupuesto_usd")
        res = presupuesto.reserva(config)
        max_intentos = max(1, int(limites.get("max_intentos_por_orden", 3)))
        max_turns = int(limites.get("max_turns_ejecucion", 4))
        plazo = int(limites.get("max_duracion_ejecucion_s", 45))
        hermes = shutil.which("hermes") or str(Path.home() / ".local" / "bin" / "hermes")

        # Presupuesto segmentado: cada intento —el inicial y cada reintento— es un
        # segmento que se reserva ANTES y se liquida DESPUÉS. Un reintento no es
        # gratis: si la reserva del siguiente intento no cabe en el margen, no se
        # lanza. Es lo que impide rebasar el techo durante la ejecución y no solo
        # al leer el coste al final.
        intentos: list[dict] = []
        salida = ""
        coste_total = 0.0
        ejecutada = False

        for intento in range(1, max_intentos + 1):
            autorizado, motivo = presupuesto.puede_iniciar(libro, limite, res)
            if not autorizado:
                intentos.append({"intento": intento, "autorizado": False, "motivo": motivo})
                break

            # Acotado del intento. IMPORTANTE Y MEDIDO: en Hermes NO existe hoy un
            # tope duro de iteraciones por ejecución que se pueda imponer desde
            # fuera. Se comprobó:
            #   · `HERMES_MAX_ITERATIONS=1` NO acota: el agente hizo 3 llamadas de
            #     herramienta (config.yaml gana sobre esa variable — hay un test en
            #     el propio Hermes, tests/gateway/test_config_env_bridge_authority.py).
            #   · `agent.max_turns: 1` en un HERMES_HOME sellado tampoco: 3 llamadas.
            # Por eso estas dos variables se pasan como MEJOR ESFUERZO, no como
            # garantía. La garantía real de esta acción es: reserva autorizada
            # antes de arrancar (arriba), corte duro por plazo con SIGKILL del
            # grupo de procesos (abajo), liquidación del coste real y bloqueo por
            # exceso o por coste desconocido.
            entorno = dict(os.environ,
                           HERMES_MAX_ITERATIONS=str(max_turns),
                           HERMES_AGENT_TIMEOUT=str(plazo))
            t0 = time.time()
            rc, out = None, ""
            proc = None
            try:
                proc = subprocess.Popen([hermes, "-z", PROMPT_TAREA_LOCAL, "--pass-session-id"],
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, env=entorno, start_new_session=True)
                try:
                    out, _ = proc.communicate(timeout=plazo)
                    rc = proc.returncode
                except subprocess.TimeoutExpired:
                    # Corte duro: mata el grupo entero, no solo el padre.
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        proc.kill()
                    out, _ = proc.communicate()
                    rc = -9
                    out = (out or "") + "\n[corte duro por plazo del puente]"
            finally:
                time.sleep(2)   # que Hermes termine de persistir la sesión

            seg = presupuesto.liquidar(libro, t0, {"intento": intento, "accion": accion}, limite, res)
            coste_total += seg["coste_usd"]
            intentos.append({"intento": intento, "autorizado": True, "exit": rc,
                             "coste_usd": seg["coste_usd"], "exceso": seg["exceso"],
                             "sesiones": len(seg["sesiones"])})
            if seg["exceso"] or seg["coste_desconocido"]:
                break           # fallo cerrado: no se sigue gastando
            if rc == 0:
                ejecutada = True
                salida = (out or "").strip()[:500]
                break

        libro["_sucio"] = True
        detalle = {
            "salida": salida,
            "intentos": intentos,
            "intentos_usados": len(intentos),
            "coste_usd": round(coste_total, 8),
            "acumulado_dia_usd": libro["gastado_usd"],
            "limite_dia_usd": limite,
            "reserva_por_intento_usd": res,
            "restante_usd": presupuesto.restante(libro, limite),
            "dia_presupuesto": libro["dia"],
            "exceso": libro.get("exceso", False),
        }
        if ejecutada:
            return {"ejecutada": True, "coste_usd": round(coste_total, 8), "resultado": detalle}
        ultimo = intentos[-1]["motivo"] if intentos and not intentos[-1].get("autorizado") else "sin éxito"
        return {"ejecutada": False, "coste_usd": round(coste_total, 8),
                "requiere_cola": bool(intentos and not intentos[-1].get("autorizado")),
                "motivo": f"no se completó en {len(intentos)} intento(s): {ultimo}",
                "resultado": detalle}
    return {"ejecutada": False, "motivo": "acción no implementada"}


# --------------------------------------------------------------- proceso orden
def procesar_orden(t: Transporte, config: dict, estado: dict, libro: dict,
                   orden: dict, cid: str, repo: str, issue: int, salidas: list[str],
                   verbose: bool) -> dict:
    """Decide y (si procede) ejecuta una orden. Persiste ANTES de ejecutar."""
    id_orden = str(orden["id_orden"])
    accion = str(orden["accion"])
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # --- autenticación verificable (firma HMAC) ---
    if config.get("auth", {}).get("requerida", True):
        esquema = str(config.get("auth", {}).get("esquema", "hmac-sha256")).lower()
        if esquema in ("ssh-signature", "ssh"):
            # Firma asimétrica: el puente solo guarda la clave PÚBLICA del
            # supervisor (allowlist), nunca su clave privada. Ver auth_ssh.py.
            ruta_allowed = Path(config["auth"].get("allowed_signers", BASE / "allowed_signers"))
            valida, motivo = auth_ssh.verificar_ssh(
                orden, ruta_allowed, orden.get("firma", ""), orden.get("firmante", ""))
        else:
            valida, motivo = auth.verificar(orden, auth.leer_secreto(auth.ruta_secreto(BASE)))
        if not valida:
            registro = {"id_orden": id_orden, "comentario": cid, "accion": accion,
                        "estado": "no_autenticada", "motivo": motivo, "ts": ahora,
                        "origen_autenticado": False}
            estado["ordenes"][id_orden] = registro
            estado["bloqueos"].append({"ts": ahora, "orden": id_orden, "motivo": f"no autenticada: {motivo}"})
            pref = f"na-{id_orden}"
            encolar_publicacion(estado, repo, issue, f"{pref}-a",
                f"### Orden rechazada — `{id_orden}`\n\n"
                f"- **Estado:** `no_autenticada`\n- **Motivo:** {motivo}\n"
                f"- **Acción solicitada:** `{accion}`\n\n"
                f"La firma HMAC no es válida, así que el puente no ejecuta nada.")
            salidas.append(f"{id_orden}: NO AUTENTICADA ({motivo})")
            return registro

    # --- límite diario de órdenes ---
    limites = config.get("limites", {})
    hoy = presupuesto.dia_actual()
    hechas_hoy = int(estado["contadores"].get(hoy, 0))
    max_dia = int(limites.get("max_ordenes_por_dia", 20))
    if hechas_hoy >= max_dia:
        return _encolar(estado, orden, cid, repo, issue, "límite diario de órdenes alcanzado", salidas, ahora)

    # --- persistir el reclamo ANTES de ejecutar ---
    estado["ordenes"][id_orden] = {
        "id_orden": id_orden, "comentario": cid, "accion": accion,
        "estado": "en_curso", "reclamada_ts": ahora, "origen_autenticado": True,
    }
    guardar_json_atomico(ESTADO_PATH, estado)          # <-- antes de ejecutar
    log(f"reclamo persistido para {id_orden} antes de ejecutar", verbose)

    res = ejecutar_accion(accion, config, libro, estado)
    if libro.pop("_sucio", False):
        presupuesto.guardar_libro(LIBRO_PATH, libro)

    if res.get("requiere_cola"):
        return _encolar(estado, orden, cid, repo, issue, res.get("motivo", "límite alcanzado"), salidas, ahora)

    if res["ejecutada"]:
        hechas_hoy += 1
        estado["contadores"][hoy] = hechas_hoy
        estado_orden = "entregado"
    else:
        estado_orden = "bloqueado"

    registro = {
        "id_orden": id_orden, "comentario": cid, "accion": accion,
        "estado": estado_orden, "resultado": res, "origen_autenticado": True, "ts": ahora,
        "coste_usd": res.get("coste_usd", 0.0),
    }
    estado["ordenes"][id_orden] = registro
    if estado_orden == "bloqueado":
        estado["bloqueos"].append({"ts": ahora, "orden": id_orden, "motivo": res.get("motivo", "sin detalle")})

    acuse = (f"### Acuse de recibo — orden `{id_orden}`\n\n"
             f"- **Estado:** `{estado_orden}`\n- **Comentario de origen:** `{cid}`\n"
             f"- **Acción:** `{accion}`\n- **Origen autenticado:** **sí** (firma HMAC válida)\n")
    if res.get("coste_usd") is not None:
        acuse += f"- **Coste:** {res.get('coste_usd', 0):.8f} USD\n"
    encolar_publicacion(estado, repo, issue, f"{id_orden}-a", acuse)

    if res["ejecutada"]:
        cuerpo_res = (f"### Resultado — orden `{id_orden}`\n\n"
                      f"```json\n{json.dumps(res['resultado'], ensure_ascii=False, indent=2)}\n```\n\n"
                      f"Tarea local pequeña y reversible: sin efectos externos.\n")
    else:
        cuerpo_res = (f"### Resultado — orden `{id_orden}`\n\n"
                      f"No ejecutada: {res.get('motivo', 'sin motivo')}.\n")
    encolar_publicacion(estado, repo, issue, f"{id_orden}-r", cuerpo_res)
    salidas.append(f"{repo}#{issue}: orden {id_orden} -> {estado_orden}")
    return registro


def _encolar(estado: dict, orden: dict, cid: str, repo: str, issue: int, motivo: str,
             salidas: list[str], ahora: str) -> dict:
    """Encola la orden para el día siguiente en vez de descartarla."""
    id_orden = str(orden["id_orden"])
    estado["cola"][id_orden] = {
        "orden": orden, "comentario": cid, "repo": repo, "issue": issue, "motivo": motivo,
        "dia_cola": presupuesto.dia_actual(), "ts": ahora,
    }
    estado["ordenes"][id_orden] = {"id_orden": id_orden, "comentario": cid,
                                   "accion": str(orden.get("accion")), "estado": "pendiente",
                                   "motivo": motivo, "ts": ahora, "origen_autenticado": True}
    estado["bloqueos"].append({"ts": ahora, "orden": id_orden, "motivo": f"en cola: {motivo}"})
    salidas.append(f"orden {id_orden} ENCOLADA para el próximo día ({motivo})")
    return estado["ordenes"][id_orden]


def retomar_cola(t: Transporte, config: dict, estado: dict, libro: dict,
                 salidas: list[str], verbose: bool) -> None:
    """Retoma al día siguiente las órdenes que quedaron en cola."""
    hoy = presupuesto.dia_actual()
    meses = [k for k, v in estado["cola"].items() if v.get("dia_cola") != hoy]
    for id_orden in meses:
        item = estado["cola"].pop(id_orden)
        repo, issue = item.get("repo"), item.get("issue")
        if not repo or issue is None:
            log(f"orden encolada {id_orden} sin repo/issue; se deja en cola", True)
            estado["cola"][id_orden] = item
            continue
        log(f"retomando orden encolada {id_orden} del día {item.get('dia_cola')}", verbose)
        procesar_orden(t, config, estado, libro, item["orden"], item.get("comentario", ""),
                       repo, issue, salidas, verbose)


def reconciliar_interrumpidas(estado: dict, salidas: list[str]) -> None:
    """Órdenes marcadas `en_curso` de una ejecución que murió: NO se reintentan."""
    for id_orden, reg in estado["ordenes"].items():
        if reg.get("estado") == "en_curso":
            reg["estado"] = "bloqueado_interrumpido"
            reg["motivo"] = ("el proceso murió tras reclamar la orden y antes de registrar el "
                             "resultado; no se reintenta para no repetir efectos inciertos")
            estado["bloqueos"].append({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                       "orden": id_orden, "motivo": reg["motivo"]})
            salidas.append(f"BLOQUEO: orden {id_orden} interrumpida; requiere revisión manual")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(CONFIG_PATH))
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    BASE.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    lock_fh = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("otra ejecución está en curso; salgo", args.verbose)
        return 0

    config = cargar_json(Path(args.config), {})
    estado = cargar_json(ESTADO_PATH, {})
    estado.setdefault("ultimo_comentario_id", {})
    estado.setdefault("inicializados", [])
    estado.setdefault("procesados", [])
    estado.setdefault("ordenes", {})
    estado.setdefault("cola", {})
    estado.setdefault("publicaciones_pendientes", [])
    estado.setdefault("contadores", {})
    estado.setdefault("bloqueos", [])
    libro = presupuesto.cargar_libro(LIBRO_PATH)

    if config.get("pausa") or (BASE / "PAUSA").exists():
        log("puente en PAUSA (config.json o fichero PAUSA); salgo sin sondear", args.verbose)
        return 0

    t = Transporte(args.verbose)
    if not t.disponible():
        log("BLOQUEO: no hay transporte a GitHub (ni gh, ni gh.exe, ni GH_TOKEN)", True)
        return 2

    salidas: list[str] = []

    # 1. reconciliar órdenes interrumpidas (antes de nada)
    reconciliar_interrumpidas(estado, salidas)

    # 2. vaciar el buzón de publicaciones pendientes
    publicadas = vaciar_publicaciones(t, estado, args.dry_run, args.verbose)
    if publicadas:
        salidas.append(f"publicaciones reconciliadas: {publicadas}")

    # 3. retomar la cola del día anterior
    retomar_cola(t, config, estado, libro, salidas, args.verbose)

    # 4. sondear comentarios nuevos
    repos = config.get("repos_vigilados", [])
    permitidos = config.get("issues_permitidos", {})
    for repo in repos:
        for issue in permitidos.get(repo, []):
            clave = f"{repo}#{issue}"
            cursor = estado["ultimo_comentario_id"].get(clave)
            try:
                nuevos = comentarios(t, repo, issue, cursor)
            except RuntimeError as e:
                log(f"error consultando {clave}: {e}", True)
                continue
            log(f"{clave}: {len(nuevos)} comentario(s) nuevo(s) tras cursor={cursor}", args.verbose)

            if clave not in estado["inicializados"]:
                todos = comentarios(t, repo, issue, None)
                estado["ultimo_comentario_id"][clave] = int(todos[-1]["id"]) if todos else 0
                estado["inicializados"].append(clave)
                log(f"{clave}: primera ejecución — cursor fijado en "
                    f"{estado['ultimo_comentario_id'][clave]}, sin procesar histórico", True)
                continue

            for c in nuevos:
                cid = str(c.get("id"))
                if cid in estado["procesados"]:
                    continue
                cuerpo = c.get("body") or ""
                if MARCADOR_PROPIO in cuerpo:
                    estado["procesados"].append(cid)
                    continue
                orden = parsear_orden(cuerpo)
                if orden is None:
                    estado["procesados"].append(cid)
                    continue
                if orden.get("_invalida"):
                    estado["procesados"].append(cid)
                    estado["bloqueos"].append({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                               "comentario": cid, "motivo": orden["_invalida"]})
                    salidas.append(f"ORDEN INVALIDA en {clave} ({cid}): {orden['_invalida']}")
                    continue
                id_orden = str(orden.get("id_orden", "")).strip()
                if id_orden in estado["ordenes"]:
                    estado["procesados"].append(cid)
                    log(f"orden {id_orden} ya registrada; duplicado ignorado", args.verbose)
                    continue
                estado["procesados"].append(cid)
                procesar_orden(t, config, estado, libro, orden, cid, repo, issue,
                               salidas, args.verbose)

            if nuevos:
                estado["ultimo_comentario_id"][clave] = int(nuevos[-1]["id"])

    # 5. publicar lo que quedó encolado en esta pasada
    vaciar_publicaciones(t, estado, args.dry_run, args.verbose)

    guardar_json_atomico(ESTADO_PATH, estado)
    if libro.pop("_sucio", False):
        presupuesto.guardar_libro(LIBRO_PATH, libro)
    for s in salidas:
        print(s)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        log(f"ERROR NO CONTROLADO: {type(exc).__name__}: {exc}", True)
        sys.exit(1)
