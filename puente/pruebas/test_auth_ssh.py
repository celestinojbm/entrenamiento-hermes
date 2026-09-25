#!/usr/bin/env python3
"""Pruebas de la autenticación asimétrica del supervisor (issue #3, propuesta).

Ejercita el mecanismo completo con `ssh-keygen -Y`, que está disponible tanto en
Linux como en la OpenSSH que ya trae Windows. No hay ningún secreto compartido:
la clave privada se queda en el lado del supervisor y el puente solo guarda la
pública.

Uso: python3 puente/pruebas/test_auth_ssh.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "puente"))

import auth_ssh  # noqa: E402

TMP = Path("/tmp/puente-test-ssh")
resultados: list[tuple[str, bool, str]] = []


def registrar(nombre: str, ok: bool, detalle: str) -> None:
    resultados.append((nombre, ok, detalle))
    print(f"{'OK  ' if ok else 'FALLO'}  {nombre}\n      {detalle}")


def correr_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(RAIZ / "puente" / "auth_ssh.py"), *args],
                          capture_output=True, text=True, timeout=60)


def main() -> int:
    if shutil.which("ssh-keygen") is None:
        print("ssh-keygen no disponible: se omite")
        return 0
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)

    # 1. el supervisor genera su par; la privada no sale de su lado
    r = correr_cli("generar-clave", "--destino", str(TMP / "hermes_orden"), "--firmante", "supervisor")
    privada = TMP / "hermes_orden"
    publica = TMP / "hermes_orden.pub"
    registrar("S1 se genera el par de claves del supervisor",
              r.returncode == 0 and privada.exists() and publica.exists(),
              f"privada={privada.name} publica={publica.name}")

    # 2. solo la pública viaja al allowlist
    allowed = TMP / "allowed_signers"
    pub = publica.read_text(encoding="utf-8").split()
    allowed.write_text(f"supervisor {pub[0]} {pub[1]}\n", encoding="utf-8")
    registrar("S2 el allowlist contiene SOLO la clave pública",
              allowed.exists() and "PRIVATE" not in allowed.read_text(encoding="utf-8"),
              f"{allowed.read_text(encoding='utf-8').strip()[:60]}…")

    # 3. firma de una orden
    orden = {"id_orden": "ord-ssh-001", "tipo": "orden", "accion": "ping", "parametros": {},
             "emitida_en": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (TMP / "orden.json").write_text(json.dumps(orden, ensure_ascii=False), encoding="utf-8")
    r = correr_cli("firmar", str(TMP / "orden.json"), "--clave", str(privada), "--firmante", "supervisor")
    bloque = re.search(r"```hermes-order\s*\n(.*?)\n```", r.stdout, re.S)
    firmada = json.loads(bloque.group(1)) if bloque else {}
    (TMP / "firmada.json").write_text(json.dumps(firmada, ensure_ascii=False), encoding="utf-8")
    registrar("S3 la orden se firma y se empaqueta para el comentario",
              bool(firmada.get("firma")) and firmada.get("firmante") == "supervisor",
              f"firmante={firmada.get('firmante')} firma={str(firmada.get('firma'))[:32]}…")

    # 4. verificación con la pública
    ok, motivo = auth_ssh.verificar_ssh(firmada, allowed, firmada.get("firma", ""), firmada.get("firmante", ""))
    registrar("S4 la firma se verifica con la clave pública", ok, motivo)

    # 5. manipular la orden invalida la firma
    manip = dict(firmada, accion="tarea_local")
    ok5, motivo5 = auth_ssh.verificar_ssh(manip, allowed, manip.get("firma", ""), manip.get("firmante", ""))
    registrar("S5 cambiar la acción invalida la firma", not ok5, motivo5[:90])

    # 6. otra clave no puede validarla
    correr_cli("generar-clave", "--destino", str(TMP / "otro"), "--firmante", "impostor")
    pub2 = (TMP / "otro.pub").read_text(encoding="utf-8").split()
    allowed2 = TMP / "allowed_impostor"
    allowed2.write_text(f"supervisor {pub2[0]} {pub2[1]}\n", encoding="utf-8")
    ok6, motivo6 = auth_ssh.verificar_ssh(firmada, allowed2, firmada.get("firma", ""), firmada.get("firmante", ""))
    registrar("S6 otra clave pública no puede validar la orden", not ok6, motivo6[:90])

    # 7. sin allowlist no se puede verificar (fallo cerrado)
    ok7, motivo7 = auth_ssh.verificar_ssh(firmada, TMP / "no-existe", firmada.get("firma", ""), "supervisor")
    registrar("S7 sin allowlist → fallo cerrado", not ok7, motivo7)

    # 8. la clave privada no se copia al repositorio
    # Excluimos el directorio de salidas de prueba para evitar falsos positivos:
    # los archivos de bateria-*.txt contienen literalmente "PRIVATE KEY"
    # como parte de sus propios mensajes de reporte, no claves reales.
    repo = RAIZ / "puente"
    salidas_dir = repo / "pruebas" / "salidas"
    def _es_salida(p: Path) -> bool:
        try:
            p.relative_to(salidas_dir)
            return True
        except ValueError:
            return False
    filtrados = [p for p in repo.rglob("*") if p.is_file()
                 and p.stat().st_size < 4096
                 and not _es_salida(p)
                 and b"PRIVATE KEY" in p.read_bytes()]
    registrar("S8 ninguna clave privada en el repositorio", not filtrados,
              f"archivos con 'PRIVATE KEY': {[p.name for p in filtrados] or 'ninguno'}")

    fallos = [n for n, ok, _ in resultados if not ok]
    print(f"\nresumen: {len(resultados) - len(fallos)}/{len(resultados)} pruebas OK")
    if fallos:
        print("fallos:", ", ".join(fallos))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
