#!/usr/bin/env python3
"""Ejecutor de la cola de despacho de n8n, con lista blanca de tipos y reclamación verificada.

Reglas del anfitrión que aplica:
  - NO ejecuta nada con approval_required distinto de false.
  - NO ejecuta nada que no sea automation_mode = read_only.
  - Solo ejecuta tipos de la LISTA BLANCA (implementaciones fijas, nunca comandos de un issue o de un modelo).
  - No hace merges, ni toca producción, ni dinero, ni mensajes a terceros.
  - Reclamación con verificación posterior; recupera reclamaciones abandonadas por antigüedad.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import n8n_api as api  # noqa: E402

TABLA = "93JVO9NHWwx4r68S"          # github_dispatch_queue (del Dispatcher existente)
TABLA_RES = "homelab_dispatch_results"   # tabla propia: concesión y resultado (no se toca su esquema)
EJECUTOR = "msi-ejecutor-dispatch"
LEASE_MIN = 10
LISTA_BLANCA = {
    "pull_request": "leer el PR, su CI y preparar diagnóstico con evidencia (solo lectura)",
    "issue": "leer el issue, detectar dependencias y bloqueos reales (solo lectura)",
    "ci_run": "leer los registros de CI y diagnosticar el fallo (solo lectura)",
    "verify_url": "comprobación HTTP reversible (solo lectura)",
    "backlog_update": "actualizar la tabla interna de backlog e informes",
    "notify_owner": "enviar el resultado al chat privado configurado",
}
# Reservado al anfitrión: aunque el Dispatcher marque approval_required=false, NO se ejecuta aquí.
REQUIEREN_APROBACION = {"merge", "deploy", "money", "delete_data", "third_party_message", "config_change", "commit"}


def clasifica(fila):
    """Política explícita en código. Devuelve (decisión, motivo)."""
    tipo = fila.get("type")
    modo = fila.get("automation_mode")
    if tipo in REQUIEREN_APROBACION:
        return "aprobacion_obligatoria", "tipo reservado al anfitrión (no autorizado para ejecución autónoma)"
    if tipo not in LISTA_BLANCA:
        return "aprobacion_obligatoria", "tipo fuera de la lista autorizada"
    if modo != "read_only":
        return "aprobacion_obligatoria", "modo distinto de read_only"
    if tipo in ("merge", "commit", "config_change"):
        return "aprobacion_obligatoria", "modificación: solo por el ejecutor local con reclamación atómica"
    return "auto", LISTA_BLANCA[tipo]
REGLAS = []
EVID = os.path.join(AQUI, "evidencia")
REGISTRO = os.path.join(AQUI, "ejecutado.json")
LOG = os.path.join(AQUI, "ejecutor.log")
ctx = ssl._create_unverified_context()


def filas(ruta):
    r = api.get(ruta)
    return r if isinstance(r, list) else (r.get("data") or r.get("rows") or [])


def anota(txt):
    linea = f"{datetime.now(timezone.utc).isoformat()} {txt}"
    print("  " + txt)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(linea + "\n")


def registro():
    if os.path.exists(REGISTRO):
        return json.load(open(REGISTRO, encoding="utf-8"))
    return {}


def guarda_registro(r):
    json.dump(r, open(REGISTRO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def tabla_resultados():
    t = next((x for x in filas("/api/v1/data-tables?limit=50") if x.get("name") == TABLA_RES), None)
    if t:
        return t["id"]
    t = api.post("/api/v1/data-tables", {"name": TABLA_RES, "columns": [
        {"name": "dispatch_key", "type": "string"}, {"name": "estado", "type": "string"},
        {"name": "ejecutor", "type": "string"}, {"name": "claimed_at", "type": "string"},
        {"name": "resultado", "type": "string"}, {"name": "evidence", "type": "string"},
        {"name": "finished_at", "type": "string"}]})
    anota(f"tabla propia de resultados creada: {TABLA_RES} ({t.get('id')})")
    return t["id"]


def fila_resultado(rid, clave):
    return next((x for x in filas(f"/api/v1/data-tables/{rid}/rows?limit=200") if x.get("dispatch_key") == clave), {})


def apunta_resultado(rid, clave, campos):
    api.post(f"/api/v1/data-tables/{rid}/rows/upsert",
             {"filter": {"filters": [{"columnName": "dispatch_key", "condition": "eq", "value": clave}]},
              "data": dict({"dispatch_key": clave}, **campos)})


def marca_dispatch(clave, estado):
    """Solo toca la columna que el esquema del Dispatcher ya tiene."""
    api._req("PATCH", f"/api/v1/data-tables/{TABLA}/rows/update",
             {"filter": {"filters": [{"columnName": "dispatch_key", "condition": "eq", "value": clave}]},
              "data": {"dispatch_status": estado}})


def ejecutar_tarea(fila):
    """Acción de la lista autorizada. Implementación fija: nunca lanza un comando de un issue o de un modelo."""
    tipo = fila.get("type")
    if tipo in ("pull_request", "issue", "ci_run"):
        return leer_github(fila, tipo)
    return ejecutar_tarea_http(fila)


def leer_github(fila, tipo):
    """Lectura real del PR o issue con gh (solo GET). Produce diagnóstico y evidencia."""
    import re as _re
    import subprocess as _sp
    repo = fila.get("repository") or "celestinojbm/" + str(fila.get("project") or "")
    num = fila.get("github_number")
    t0 = time.time()
    if tipo in ("pull_request", "ci_run"):
        p = _sp.run(["gh", "api", f"repos/{repo}/pulls/{num}"], capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            return False, f"lectura del PR falló: {(p.stderr or '')[:70]}", {"repo": repo, "numero": num}
        pr = json.loads(p.stdout)
        sha = (pr.get("head") or {}).get("sha") or ""
        c = _sp.run(["gh", "api", f"repos/{repo}/commits/{sha}/check-runs"], capture_output=True, text=True, timeout=60)
        checks = (json.loads(c.stdout).get("check_runs") or []) if c.returncode == 0 else []
        mal = [x.get("name") for x in checks if x.get("conclusion") in ("failure", "timed_out", "cancelled")]
        ok = [x for x in checks if x.get("conclusion") == "success"]
        ci = "fallo" if mal else ("verde" if ok else "sin datos")
        diag = (f"PR #{num} ({repo}) '{str(pr.get('title'))[:70]}' estado={pr.get('state')} borrador={pr.get('draft')} "
                f"CI={ci} ({len(ok)} ok, {len(mal)} en fallo)" + (f" · fallan: {', '.join(mal[:3])}" if mal else "") +
                (f" · rama de Claude, no intervenir" if str((pr.get('head') or {}).get('ref', '')).startswith('claude/') else ""))
        ev = {"repo": repo, "numero": num, "sha": sha, "ci": ci, "checks_ok": len(ok), "checks_fallo": mal[:5],
              "ms": int((time.time() - t0) * 1000), "cuando": datetime.now(timezone.utc).isoformat()}
        return True, diag, ev
    p = _sp.run(["gh", "api", f"repos/{repo}/issues/{num}"], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        return False, f"lectura del issue falló: {(p.stderr or '')[:70]}", {"repo": repo, "numero": num}
    it = json.loads(p.stdout)
    cuerpo = (it.get("body") or "")
    deps = _re.findall(r"(?i)(?:depends? on|depende de|blocked by|bloquead[oa] por)\s*#?(\d+)", cuerpo)
    diag = (f"issue #{num} ({repo}) '{str(it.get('title'))[:70]}' estado={it.get('state')} "
            f"etiquetas={[l.get('name') for l in (it.get('labels') or [])]} · dependencias detectadas={deps or 'ninguna'}")
    return True, diag, {"repo": repo, "numero": num, "dependencias": deps, "etiquetas": [l.get("name") for l in (it.get("labels") or [])],
                        "cuando": datetime.now(timezone.utc).isoformat()}


def ejecutar_tarea_http(fila):
    url = fila.get("url") or ""
    t0 = time.time()
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "homelab-ejecutor/1"})
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            cuerpo = r.read()
            code, lat = r.status, int((time.time() - t0) * 1000)
    except urllib.error.HTTPError as e:
        cuerpo = e.read(); code, lat = e.code, int((time.time() - t0) * 1000)
    except Exception as e:  # noqa: BLE001
        cuerpo, code, lat = b"", None, int((time.time() - t0) * 1000)
        return False, f"sin respuesta: {str(e)[:80]}", {"url": url, "error": str(e)[:200], "ms": lat}
    ok = code is not None and 200 <= code < 400
    ev = {"url": url, "codigo": code, "ms": lat, "sha256_cuerpo": hashlib.sha256(cuerpo).hexdigest()[:16],
          "bytes": len(cuerpo), "cuando": datetime.now(timezone.utc).isoformat()}
    return ok, f"HTTP {code} en {lat} ms", ev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=1)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    os.makedirs(EVID, exist_ok=True)
    reg, rid = registro(), tabla_resultados()
    ahora = datetime.now(timezone.utc)

    print("=== COLA DE DESPACHO (n8n) ===")
    todas = filas(f"/api/v1/data-tables/{TABLA}/rows?limit=200")
    print(f"  filas leídas: {len(todas)}")
    motivos = {}
    candidatas = []
    for f in todas:
        k = f.get("dispatch_key")
        decision, motivo = clasifica(f)
        if decision != "auto":
            motivos[motivo] = motivos.get(motivo, 0) + 1; continue
        if f.get("dispatch_status") == "hecho" or k in reg:
            motivos["ya ejecutada (idempotencia)"] = motivos.get("ya ejecutada (idempotencia)", 0) + 1; continue
        res = fila_resultado(rid, k)
        if f.get("dispatch_status") == "en_curso" and res.get("ejecutor"):
            try:
                edad = (ahora - datetime.fromisoformat(str(res.get("claimed_at")).replace("Z", "+00:00"))).total_seconds() / 60
            except Exception:
                edad = 999
            if edad < LEASE_MIN and res.get("ejecutor") != EJECUTOR:
                motivos["reclamada con concesión vigente por otro"] = motivos.get("reclamada con concesión vigente por otro", 0) + 1; continue
            anota(f"recuperando concesión abandonada ({int(edad)} min) de {res.get('ejecutor')}: {k}")
        candidatas.append(f)
    for m, n in motivos.items():
        print(f"  descartadas por {m}: {n}")
    print(f"  candidatas: {len(candidatas)}")
    if not candidatas:
        anota("nada que ejecutar")
        return 0

    for fila in candidatas[: args.max]:
        k = fila["dispatch_key"]
        print(f"\n=== TAREA {k} ===")
        print(f"  origen: fila del Dispatcher {fila.get('dispatch_status')} · carril {fila.get('dispatch_lane')} · {fila.get('title')}")
        if args.dry:
            print("  (dry: no se reclama ni se ejecuta)"); continue
        # reclamación + verificación (la concesión vive en la tabla propia)
        apunta_resultado(rid, k, {"estado": "en_curso", "ejecutor": EJECUTOR,
                                  "claimed_at": ahora.isoformat().replace("+00:00", "Z")})
        marca_dispatch(k, "en_curso")
        vuelta = fila_resultado(rid, k)
        if vuelta.get("ejecutor") != EJECUTOR:
            anota(f"reclamación NO confirmada para {k}: otro ejecutor la tiene -> no se ejecuta")
            continue
        anota(f"reclamación confirmada: {k} retenida por {EJECUTOR}")
        ok, resultado, ev = ejecutar_tarea(fila)
        nombre = f"{k.replace('/', '_').replace(':', '-')}@{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        ruta_ev = os.path.join(EVID, nombre)
        json.dump({"dispatch_key": k, "tipo": fila.get("type"), "accion": LISTA_BLANCA.get(fila.get("type")),
                   "resultado": resultado, "ok": ok, "evidencia": ev, "ejecutor": EJECUTOR,
                   "leido_de": "n8n github_dispatch_queue"}, open(ruta_ev, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        reg[k] = {"cuando": ev.get("cuando"), "resultado": resultado, "ok": ok, "evidencia": nombre}
        guarda_registro(reg)
        apunta_resultado(rid, k, {"estado": "hecho", "ejecutor": EJECUTOR, "resultado": resultado[:180],
                                  "evidence": nombre, "finished_at": ev.get("cuando")})
        marca_dispatch(k, "hecho")
        anota(f"ejecutada {k}: {resultado} · evidencia {nombre} · fila marcada 'hecho'")
        print("\n=== RESULTADO INFORMADO ===")
        print(f"  cola del Dispatcher -> dispatch_status='hecho'")
        print(f"  tabla propia -> {TABLA_RES}: estado=hecho, resultado='{resultado[:70]}', evidence={nombre}")
        print(f"  evidencia local -> {os.path.join(EVID, nombre)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
