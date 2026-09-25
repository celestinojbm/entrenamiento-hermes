#!/usr/bin/env python3
"""Autenticación del supervisor con firma ASIMÉTRICA (propuesta para issue #3).

Problema que resuelve respecto al HMAC: con HMAC hay que provisionar un secreto
compartido, y eso obliga a mover el secreto de la máquina de Hermes a la del
supervisor (o al revés). Este módulo evita exactamente eso usando capacidades
**ya disponibles** en ambas máquinas: firmas SSH de OpenSSH (`ssh-keygen -Y`),
presentes en Linux (probado con 10.2p1) y en Windows (probado con 9.5p2, la
OpenSSH que ya trae Windows y que el usuario ya usa: tiene `authorized_keys`).

Cómo funciona:

  1. El supervisor genera SU par de claves en SU máquina. La privada **nunca
     sale de ahí**:
        ssh-keygen -t ed25519 -f ~/.ssh/hermes_orden -C supervisor
  2. Solo viaja la clave PÚBLICA. Se guarda en el allowlist de Hermes:
        puente/allowed_signers    con la línea:
          supervisor ssh-ed25519 AAAAC3Nza...
  3. Para emitir una orden, el supervisor firma la carga canónica:
        ssh-keygen -Y sign -f ~/.ssh/hermes_orden -n hermes-order orden.json
  4. El puente verifica con la pública:
        ssh-keygen -Y verify -f allowed_signers -I supervisor -n hermes-order -s sig

Ventajas sobre el HMAC: no hay secreto compartido, no se puede suplantar al
supervisor desde la máquina de Hermes, y la revocación es borrar una línea del
allowlist. El namespace `hermes-order` separa estas firmas de cualquier otra cosa
que esas claves firmen (git, SSH, etc.).

Estado: **mecanismo implementado y probado**; **no activado** para el supervisor
real porque todavía no hay una clave pública suya provisionada. No se declara
conexión por esto.
"""
from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from pathlib import Path

NAMESPACE = "hermes-order"
CABECERA = "-----BEGIN SSH SIGNATURE-----"
PIE = "-----END SSH SIGNATURE-----"


def ssh_keygen_disponible() -> str | None:
    return shutil.which("ssh-keygen")


def empaquetar_firma(firma_b64: str) -> str:
    """Vuelve a poner el armazón PEM que `ssh-keygen -Y verify` espera."""
    cuerpo = (firma_b64 or "").strip()
    if cuerpo.startswith(CABECERA):
        return cuerpo if cuerpo.endswith(PIE) else cuerpo + "\n" + PIE
    lineas = [cuerpo[i:i + 70] for i in range(0, len(cuerpo), 70)]
    return "\n".join([CABECERA, *lineas, PIE]) + "\n"


def desempaquetar_firma(contenido: str) -> str:
    """Quita el armazón para poder llevar la firma dentro del JSON de la orden."""
    lineas = [l.strip() for l in (contenido or "").splitlines()]
    return "".join(l for l in lineas if l and not l.startswith("-----"))


def verificar_ssh(orden: dict, ruta_allowed: Path, firma_b64: str,
                  firmante: str, namespace: str = NAMESPACE) -> tuple[bool, str]:
    """Verifica la firma SSH de la orden contra el allowlist de claves públicas."""
    exe = ssh_keygen_disponible()
    if exe is None:
        return False, "no hay ssh-keygen disponible para verificar"
    if not ruta_allowed.exists():
        return False, f"no existe el allowlist de claves públicas: {ruta_allowed}"
    if not firmante:
        return False, "la orden no indica firmante"
    if not firma_b64:
        return False, "la orden no trae firma SSH"

    # La firma debe ir sobre la MISMA carga canónica que se firma con HMAC.
    from auth import canonico

    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        (t / "payload").write_bytes(canonico(orden))
        (t / "sig").write_text(empaquetar_firma(firma_b64), encoding="utf-8")
        proc = subprocess.run(
            [exe, "-Y", "verify", "-f", str(ruta_allowed), "-I", firmante,
             "-n", namespace, "-s", str(t / "sig")],
            stdin=open(t / "payload", "rb"), capture_output=True, text=True, timeout=30,
        )
    if proc.returncode == 0:
        return True, f"firma SSH válida de {firmante!r}"
    detalle = (proc.stderr or proc.stdout or "").strip().splitlines()
    return False, f"firma SSH rechazada: {detalle[-1] if detalle else 'sin detalle'}"


def _cli() -> int:
    import argparse
    import json
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    ap = argparse.ArgumentParser(description="Firmas SSH de órdenes del puente")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("generar-clave", help="genera el par del supervisor (solo la privada se queda aquí)")
    p_gen.add_argument("--destino", default=str(Path.home() / ".ssh" / "hermes_orden"))
    p_gen.add_argument("--firmante", default="supervisor")

    p_fir = sub.add_parser("firmar", help="firma un JSON de orden y lo imprime")
    p_fir.add_argument("archivo")
    p_fir.add_argument("--clave", default=str(Path.home() / ".ssh" / "hermes_orden"))
    p_fir.add_argument("--firmante", default="supervisor")

    p_ver = sub.add_parser("verificar", help="verifica una orden firmada")
    p_ver.add_argument("archivo")
    p_ver.add_argument("--allowed", required=True)

    args = ap.parse_args()

    if args.cmd == "generar-clave":
        destino = Path(args.destino)
        if destino.exists():
            print(f"ya existe {destino}; no se toca")
            return 1
        subprocess.run([ssh_keygen_disponible() or "ssh-keygen", "-t", "ed25519",
                        "-f", str(destino), "-C", "supervisor-hermes-orden", "-N", ""],
                       check=True)
        pub = Path(str(destino) + ".pub").read_text(encoding="utf-8").strip().split()
        print(f"\nClave PÚBLICA (esto es lo único que se comparte):\n{args.firmante} {' '.join(pub[:2])}")
        return 0

    if args.cmd == "firmar":
        from auth import canonico
        orden = json.loads(Path(args.archivo).read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "orden.json").write_bytes(canonico(orden))
            subprocess.run([ssh_keygen_disponible() or "ssh-keygen", "-Y", "sign",
                            "-f", args.clave, "-n", NAMESPACE, str(t / "orden.json")],
                           check=True, capture_output=True, text=True)
            firma = desempaquetar_firma((t / "orden.json.sig").read_text(encoding="utf-8"))
        orden["firmante"] = args.firmante
        orden["firma"] = firma
        print("```hermes-order")
        print(json.dumps(orden, ensure_ascii=False, indent=2))
        print("```")
        return 0

    orden = json.loads(Path(args.archivo).read_text(encoding="utf-8"))
    ok, motivo = verificar_ssh(orden, Path(args.allowed), orden.get("firma", ""), orden.get("firmante", ""))
    print(("VÁLIDA: " if ok else "RECHAZADA: ") + motivo)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
