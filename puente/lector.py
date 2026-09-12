#!/usr/bin/env python3
"""Lector local del puente GitHub <-> Hermes (issue #3).

Diseño de esta primera entrega — deliberadamente acotado:

  * NO usa LLM. Es un proceso de sondeo puro. Sin novedades: sale en silencio
    (stdout vacío), de modo que es compatible con un job `--no-agent` de Hermes
    o con cron del sistema sin gastar un solo token.
  * NO ejecuta texto arbitrario. Las órdenes aceptadas se resuelven contra un
    enumerado cerrado de acciones (`acciones_permitidas`). El contenido del
    comentario es SIEMPRE dato, nunca código.
  * NO se autentica el origen. El autor de un comentario no prueba quién lo
    escribió (supervisor y Hermes publican con la misma cuenta), así que por
    defecto solo se reconocen acciones inocuas y cualquier otra orden queda
    registrada como "pendiente de confirmación humana", sin ejecutarse.
  * NO procesa histórico al arrancar: la primera ejecución fija el cursor en el
    último comentario existente y no procesa nada.
  * Idempotente: deduplicación por ID de comentario Y por ID de orden, con
    bloqueo exclusivo (flock) para que dos ejecuciones no se solapen.

Uso:  python3 lector.py [--config RUTA] [--verbose]
Salida: silencio total si no hay novedades; texto solo si hay algo que reportar.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, date
from pathlib import Path

BASE = Path(os.environ.get("PUENTE_HOME", Path.home() / ".hermes" / "bridge"))
CONFIG_PATH = BASE / "config.json"
ESTADO_PATH = BASE / "estado.json"
LOCK_PATH = BASE / ".lock"
LOG_DIR = BASE / "logs"

# Marca que identifica los comentarios escritos por este puente. Se usa para no
# tratarlos nunca como órdenes entrantes (evita bucles de comentarios).
MARCADOR_PROPIO = "<!-- hermes-puente:v1 -->"

# Bloque de orden aceptado: un cercado ```hermes-order ... ``` con JSON dentro.
RE_ORDEN = re.compile(r"```hermes-order\s*\n(.*?)\n```", re.DOTALL)

GH_EXE_WINDOWS = "/mnt/c/Program Files/GitHub CLI/gh.exe"

ACCIONES_INOCUAS = {"ping"}


def log(msg: str, verbose: bool = True) -> None:
    """Escribe en el log rotativo por día. Nunca imprime secretos."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    línea = f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}\n"
    try:
        with open(LOG_DIR / f"{date.today().isoformat()}.log", "a", encoding="utf-8") as fh:
            fh.write(línea)
    except OSError:
        pass
    if verbose:
        print(línea, end="")


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
    """Acceso a la API de GitHub sin crear credenciales nuevas.

    Orden de preferencia: `gh` del PATH > `gh.exe` ya autenticado de Windows >
    `curl` con GH_TOKEN del entorno. Si no hay ninguno, el lector no puede
    trabajar y lo dice (no inventa resultados).
    """

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

    def api(self, endpoint: str, metodo: str = "GET", campos: dict | None = None,
            cuerpo: dict | None = None, paginar: bool = False) -> object:
        if self.modo in ("gh", "gh.exe"):
            args = self.base + ["api", endpoint, "--method", metodo]
            if paginar:
                args += ["--paginate"]
            if campos:
                for k, v in campos.items():
                    args += ["-f", f"{k}={v}"]
            if cuerpo is not None:
                args += ["--input", "-"]
                proc = subprocess.run(args, input=json.dumps(cuerpo), capture_output=True, text=True, timeout=60)
            else:
                proc = subprocess.run(args, capture_output=True, text=True, timeout=60)
            if proc.returncode != 0:
                raise RuntimeError(f"gh fallo ({proc.returncode}): {proc.stderr.strip()[:300]}")
            salida = proc.stdout.strip()
            if not salida:
                return None
            # --paginate puede devolver varios arrays concatenados
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

        # modo curl
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
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode() or "null")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"GitHub HTTP {e.code} en {endpoint}") from None


def comentarios(t: Transporte, repo: str, issue: int, desde_id: int | None) -> list[dict]:
    """Comentarios del issue, del más antiguo al más nuevo."""
    endpoint = f"repos/{repo}/issues/{issue}/comments?per_page=100&sort=created&direction=asc"
    datos = t.api(endpoint, paginar=True)
    if not isinstance(datos, list):
        return []
    if desde_id is None:
        return datos
    # El cursor es un ID de comentario; nos quedamos con lo estrictamente posterior.
    return [c for c in datos if int(c.get("id", 0)) > desde_id]


def firmar_cuerpo(texto: str) -> str:
    return f"{texto}\n\n{MARCADOR_PROPIO}"


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
    faltan = [k for k in ("id_orden", "tipo", "accion") if k not in datos]
    if faltan:
        return {"_invalida": f"faltan campos obligatorios: {', '.join(faltan)}"}
    if datos.get("tipo") != "orden":
        return {"_invalida": f"tipo no soportado: {datos.get('tipo')!r}"}
    return datos


def ejecutar_accion(accion: str, parametros: dict, config: dict) -> dict:
    """Resuelve una acción contra un enumerado CERRADO. Nada de shell."""
    permitidas = set(config.get("acciones_permitidas", [])) & ACCIONES_INOCUAS
    if accion not in permitidas:
        return {"ejecutada": False, "motivo": f"accion {accion!r} no está en la allowlist inocua"}
    if accion == "ping":
        # Resultado determinista e inocuo: no depende del contenido del comentario.
        return {
            "ejecutada": True,
            "accion": "ping",
            "resultado": {
                "pong": True,
                "hostname": os.uname().nodename,
                "python": sys.version.split()[0],
                "lector_version": config.get("version", 1),
                "ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
        }
    return {"ejecutada": False, "motivo": "acción no implementada"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(CONFIG_PATH))
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="no publica nada en GitHub")
    args = ap.parse_args()

    BASE.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # --- bloqueo exclusivo: si ya hay un lector corriendo, salimos en silencio ---
    lock_fh = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("otra ejecución está en curso; salgo", args.verbose)
        return 0

    config = cargar_json(Path(args.config), {})
    estado = cargar_json(ESTADO_PATH, {})
    estado.setdefault("ultimo_comentario_id", {})      # repo#issue -> id
    estado.setdefault("procesados", [])                # ids de comentario ya vistos
    estado.setdefault("ordenes", {})                   # id_orden -> registro
    estado.setdefault("contadores", {})                # fecha -> nº de órdenes
    estado.setdefault("bloqueos", [])                  # fallos repetidos visibles
    # Un issue sin comentarios NO deja cursor, así que "no hay cursor" no sirve
    # como señal de "ya inicializado": haría que cada arranque se creyera el
    # primero y se saltara la primera orden real. Se marca explícitamente.
    estado.setdefault("inicializados", [])

    # Dos formas de pausar, ambas sin desinstalar nada:
    if config.get("pausa") or (BASE / "PAUSA").exists():
        log("puente en PAUSA (config.json o fichero PAUSA); salgo sin sondear", args.verbose)
        return 0

    t = Transporte(args.verbose)
    if not t.disponible():
        log("BLOQUEO: no hay transporte a GitHub (ni gh, ni gh.exe, ni GH_TOKEN)", True)
        return 2

    hoy = date.today().isoformat()
    max_dia = int(config.get("limites", {}).get("max_ordenes_por_dia", 20))
    hechas_hoy = int(estado["contadores"].get(hoy, 0))

    salidas: list[str] = []
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

            # Una sola consulta por issue; sin novedades no se escribe nada.
            log(f"{clave}: {len(nuevos)} comentario(s) nuevo(s) tras cursor={cursor}", args.verbose)

            if clave not in estado["inicializados"]:
                # No se procesa histórico: fijamos cursor en el último existente.
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
                    estado["procesados"].append(cid)   # es nuestro: ni orden ni resultado
                    continue
                orden = parsear_orden(cuerpo)
                if orden is None:
                    estado["procesados"].append(cid)
                    continue

                id_orden = str(orden.get("id_orden", "")).strip()
                if orden.get("_invalida"):
                    estado["procesados"].append(cid)
                    estado["bloqueos"].append({
                        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "comentario": cid, "motivo": orden["_invalida"],
                    })
                    salidas.append(f"ORDEN INVALIDA en {clave} (comentario {cid}): {orden['_invalida']}")
                    continue

                # dedup por id_orden además del id de comentario
                if id_orden in estado["ordenes"]:
                    estado["procesados"].append(cid)
                    log(f"orden {id_orden} ya procesada; duplicado ignorado", args.verbose)
                    continue

                # límite diario
                if hechas_hoy >= max_dia:
                    estado["procesados"].append(cid)
                    estado["bloqueos"].append({
                        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "orden": id_orden, "motivo": f"límite diario alcanzado ({max_dia})",
                    })
                    salidas.append(f"BLOQUEO: límite diario de {max_dia} órdenes alcanzado; orden {id_orden} no ejecutada")
                    continue

                accion = str(orden.get("accion", ""))
                params = orden.get("parametros") or {}
                # El origen NO está autenticado: solo se reconocen acciones inocuas.
                res = ejecutar_accion(accion, params, config)
                if res["ejecutada"]:
                    hechas_hoy += 1
                    estado["contadores"][hoy] = hechas_hoy

                registro = {
                    "id_orden": id_orden,
                    "comentario": cid,
                    "autor": (c.get("user") or {}).get("login"),
                    "accion": accion,
                    "estado": "entregado" if res["ejecutada"] else "pendiente_confirmacion_humana",
                    "resultado": res,
                    "origen_autenticado": False,
                    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
                estado["ordenes"][id_orden] = registro
                estado["procesados"].append(cid)

                if not args.dry_run:
                    acuse = (
                        f"### Acuse de recibo — orden `{id_orden}`\n\n"
                        f"- **Estado:** `{registro['estado']}`\n"
                        f"- **Comentario de origen:** `{cid}`\n"
                        f"- **Acción solicitada:** `{accion}`\n"
                        f"- **Origen autenticado:** **no** — el autor del comentario no prueba su origen; "
                        f"por eso solo se reconocen acciones de la allowlist inocua.\n"
                    )
                    t.api(f"repos/{repo}/issues/{issue}/comments", "POST",
                          cuerpo={"body": firmar_cuerpo(acuse)})
                    if res["ejecutada"]:
                        cuerpo_res = (
                            f"### Resultado — orden `{id_orden}`\n\n"
                            f"```json\n{json.dumps(res['resultado'], ensure_ascii=False, indent=2)}\n```\n\n"
                            f"Acción inocua ejecutada una sola vez. Sin efectos externos.\n"
                        )
                    else:
                        cuerpo_res = (
                            f"### Resultado — orden `{id_orden}`\n\n"
                            f"No ejecutada: {res['motivo']}.\n\n"
                            f"Requiere confirmación humana explícita (el origen no está autenticado).\n"
                        )
                    t.api(f"repos/{repo}/issues/{issue}/comments", "POST",
                          cuerpo={"body": firmar_cuerpo(cuerpo_res)})

                salidas.append(f"{clave}: orden {id_orden} -> {registro['estado']}")

            # avanzar cursor al último visto
            if nuevos:
                estado["ultimo_comentario_id"][clave] = int(nuevos[-1]["id"])

    guardar_json_atomico(ESTADO_PATH, estado)
    for s in salidas:
        print(s)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # nunca revienta el cron en silencio
        log(f"ERROR NO CONTROLADO: {type(exc).__name__}: {exc}", True)
        sys.exit(1)
