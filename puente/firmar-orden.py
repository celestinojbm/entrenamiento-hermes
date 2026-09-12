#!/usr/bin/env python3
"""Firma una orden del puente y la imprime lista para publicar como comentario.

Uso (en la máquina, por quien emite la orden):

    python3 puente/firmar-orden.py --accion tarea_local --id mi-orden-001
    python3 puente/firmar-orden.py orden.json          # firma un JSON existente

Requiere el secreto provisionado: `python3 puente/auth.py init`.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth import CAMPO_FIRMA, firmar, leer_secreto, ruta_secreto  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("archivo", nargs="?", help="JSON de la orden (si se omite, se construye)")
    ap.add_argument("--id", dest="id_orden", default=f"ord-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}")
    ap.add_argument("--accion", default="tarea_local")
    ap.add_argument("--parametros", default="{}", help="JSON de parámetros")
    ap.add_argument("--base", default=str(Path.home() / ".hermes" / "bridge"))
    args = ap.parse_args()

    if args.archivo:
        orden = json.loads(Path(args.archivo).read_text(encoding="utf-8"))
    else:
        orden = {
            "id_orden": args.id_orden,
            "tipo": "orden",
            "accion": args.accion,
            "parametros": json.loads(args.parametros),
        }
    orden.setdefault("emitida_en", datetime.now(timezone.utc).isoformat(timespec="seconds"))

    secreto = leer_secreto(ruta_secreto(Path(args.base)))
    if secreto is None:
        print("no hay secreto local: ejecuta primero `python3 puente/auth.py init`", file=sys.stderr)
        return 2

    orden[CAMPO_FIRMA] = firmar(orden, secreto)
    print("```hermes-order")
    print(json.dumps(orden, ensure_ascii=False, indent=2))
    print("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
