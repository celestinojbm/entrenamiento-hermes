#!/usr/bin/env python3
"""Autenticación verificable de órdenes (issue #3).

Problema que resuelve: el supervisor y Hermes publican en GitHub con la **misma
cuenta**, así que el autor de un comentario no autentica nada. La solución es una
firma **HMAC-SHA256** con un secreto compartido que nunca toca GitHub.

  * El secreto vive solo en disco local: `~/.hermes/bridge/secreto` (chmod 600).
  * La firma cubre la **serialización canónica** de la orden: JSON con claves
    ordenadas y sin espacios, de todos los campos menos `firma`.
  * La comparación es en tiempo constante (`hmac.compare_digest`).
  * `emitida_en` es obligatorio y se cubre con la firma: una orden caducada no
    se ejecuta (defensa básica antirreplay).
  * Sin firma válida la orden NO se ejecuta; se registra como no autenticada.

Provisionar el secreto (una vez):

    python3 puente/auth.py init        # crea el secreto si no existe

Firmar una orden (en la máquina, por quien emite):

    python3 puente/firmar-orden.py orden.json
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

CAMPOS_FIRMABLES = ("id_orden", "tipo", "accion", "parametros", "emitida_en")
CAMPO_FIRMA = "firma"
MAX_ANTIGUEDAD = timedelta(hours=24)


def ruta_secreto(base: Path) -> Path:
    return Path(os.environ.get("PUENTE_SECRETO", base / "secreto"))


def init_secreto(path: Path) -> bool:
    """Crea el secreto si no existe. Devuelve True si lo creó."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(secrets.token_hex(32) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return True


def leer_secreto(path: Path) -> bytes | None:
    try:
        valor = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return valor.encode() if valor else None


def canonico(orden: dict) -> bytes:
    """Serialización canónica: solo los campos firmables, claves ordenadas.

    Se construye explícitamente para no depender del orden ni del contenido extra
    que pueda añadir quien publica el comentario.
    """
    limpio = {k: orden.get(k) for k in CAMPOS_FIRMABLES if k in orden}
    return json.dumps(limpio, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def firmar(orden: dict, secreto: bytes) -> str:
    return hmac.new(secreto, canonico(orden), hashlib.sha256).hexdigest()


def verificar(orden: dict, secreto: bytes | None, ahora: datetime | None = None) -> tuple[bool, str]:
    """Devuelve (válida, motivo). Nunca lanza: un error es un fallo cerrado."""
    if secreto is None:
        return False, "no hay secreto local provisionado: no puede autenticarse el origen"
    firma = orden.get(CAMPO_FIRMA)
    if not isinstance(firma, str) or not firma:
        return False, "la orden no trae firma"
    faltan = [c for c in ("id_orden", "tipo", "accion", "emitida_en") if c not in orden]
    if faltan:
        return False, f"faltan campos firmables: {', '.join(faltan)}"
    esperada = firmar(orden, secreto)
    if not hmac.compare_digest(esperada, firma.lower()):
        return False, "firma inválida"
    # Antirreplay básico: caducidad de la orden.
    try:
        emitida = datetime.fromisoformat(str(orden["emitida_en"]).replace("Z", "+00:00"))
        if emitida.tzinfo is None:
            emitida = emitida.replace(tzinfo=timezone.utc)
    except ValueError:
        return False, "emitida_en no es una fecha ISO válida"
    ref = ahora or datetime.now(timezone.utc)
    if ref - emitida > MAX_ANTIGUEDAD:
        return False, f"orden caducada (más de {int(MAX_ANTIGUEDAD.total_seconds() // 3600)} h)"
    if emitida - ref > timedelta(minutes=10):
        return False, "orden con fecha futura"
    return True, "firma válida"


def _main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Autenticación de órdenes del puente")
    ap.add_argument("accion", choices=["init", "estado", "firmar"])
    ap.add_argument("archivo", nargs="?")
    ap.add_argument("--base", default=str(Path.home() / ".hermes" / "bridge"))
    args = ap.parse_args()

    base = Path(args.base)
    path = ruta_secreto(base)

    if args.accion == "init":
        creado = init_secreto(path)
        print(f"secreto {'creado' if creado else 'ya existía'} en {path} (chmod 600)")
        print("No se imprime el valor. Para firmar órdenes usa puente/firmar-orden.py")
        return 0

    if args.accion == "estado":
        sec = leer_secreto(path)
        print(f"secreto: {'presente' if sec else 'AUSENTE'} en {path}")
        print(f"longitud: {len(sec) * 4 if sec else 0} bits")
        return 0

    # firmar
    if not args.archivo:
        print("faltó el archivo JSON de la orden")
        return 2
    sec = leer_secreto(path)
    if sec is None:
        print("no hay secreto: ejecuta primero `auth.py init`")
        return 2
    orden = json.loads(Path(args.archivo).read_text(encoding="utf-8"))
    orden[CAMPO_FIRMA] = firmar(orden, sec)
    print(json.dumps(orden, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
