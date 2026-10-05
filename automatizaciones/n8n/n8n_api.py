#!/usr/bin/env python3
"""Cliente mínimo de la API pública de n8n (sin dependencias externas).

La clave se lee del entorno y, si no está, del ámbito de USUARIO del registro de Windows.
Nunca se imprime ni se escribe en ningún archivo.
"""
from __future__ import annotations
import json
import os
import ssl
import subprocess
import urllib.error
import urllib.request

BASE = os.environ.get("N8N_BASE", "https://N8N_HOST:8443")


def clave() -> tuple:
    k = os.environ.get("N8N_API_KEY", "")
    if k:
        return k, "entorno"
    try:
        p = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                            "[Environment]::GetEnvironmentVariable('N8N_API_KEY','User')"],
                           capture_output=True, text=True, timeout=25)
        k = (p.stdout or "").strip()
        if k:
            return k, "ámbito de usuario"
    except Exception:
        pass
    return "", ""


def _req(metodo: str, ruta: str, cuerpo=None, timeout=30):
    k, _ = clave()
    if not k:
        raise RuntimeError("sin N8N_API_KEY")
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(f"{BASE}{ruta}", data=datos, method=metodo,
                                 headers={"X-N8N-API-KEY": k, "Accept": "application/json",
                                          "Content-Type": "application/json"})
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"HTTP {e.code} en {metodo} {ruta}: {detalle}") from None


def get(ruta: str, **kw):
    return _req("GET", ruta, **kw)


def post(ruta: str, cuerpo=None, **kw):
    return _req("POST", ruta, cuerpo, **kw)


def patch(ruta: str, cuerpo=None, **kw):
    return _req("PATCH", ruta, cuerpo, **kw)


def put(ruta: str, cuerpo=None, **kw):
    return _req("PUT", ruta, cuerpo, **kw)


if __name__ == "__main__":
    import sys
    k, origen = clave()
    print("  clave:", f"presente ({len(k)} caracteres, {origen})" if k else "AUSENTE")
    if k and len(sys.argv) > 1:
        print(json.dumps(get(sys.argv[1]), ensure_ascii=False)[:1200])
