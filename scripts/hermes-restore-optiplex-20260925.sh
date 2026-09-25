#!/usr/bin/env bash
# Hermes original -> OptiPlex WSL. Does NOT alter the backup, n8n, cron or gateway.
set -euo pipefail
umask 077

BACKUP="$HOME/homelab/backups/hermes-migration-2026-09-21"
DEST="$HOME/.hermes"
ARCHIVE="$BACKUP/Ubuntu-Hermes-Full-2026-09-21.tar"

echo "== Hermes OptiPlex: preflight =="
test -f "$ARCHIVE" || { echo "ERROR: no se encuentra el TAR original."; exit 1; }
test -f "$BACKUP/database-snapshots/state-2026-09-21.db" || { echo "ERROR: falta state.db."; exit 1; }
test -f "$BACKUP/database-snapshots/kanban-2026-09-21.db" || { echo "ERROR: falta kanban.db."; exit 1; }
if [ -e "$DEST" ] || [ -L "$DEST" ]; then
    echo "DETENIDO: ~/.hermes ya existe. No se sobrescribe. Envia esta salida antes de continuar."
    exit 2
fi
if command -v hermes >/dev/null 2>&1; then
    echo "DETENIDO: ya hay un ejecutable Hermes en PATH. Inspeccionar antes de instalar."
    exit 2
fi
if pgrep -u "$(id -u)" -f '[h]ermes.*(gateway|serve|chat)' >/dev/null 2>&1; then
    echo "DETENIDO: hay procesos Hermes; no se modifica el perfil."
    exit 2
fi
echo "== Preparando memoria y sesiones del respaldo original =="
python3 - "$BACKUP" "$DEST" <<'PY'
import os
import shutil
import sqlite3
import sys
import tarfile
import tempfile
from pathlib import Path

backup, dest = map(Path, sys.argv[1:])
archive = backup / "Ubuntu-Hermes-Full-2026-09-21.tar"
prefix = "home/celestinojbm/.hermes/"
roots = {
    "SOUL.md", "config.yaml", "auth.json", ".env", "IDENTITY.md",
    "USER.md", "AGENTS.md",
}
folders = ("memories/", "skills/", "sessions/", "profiles/")
stage = Path(tempfile.mkdtemp(prefix=".hermes-preparando-", dir=Path.home()))
count = 0
try:
    for name in ("state", "kanban"):
        source = backup / f"database-snapshots/{name}-2026-09-21.db"
        db = sqlite3.connect(f"file:{source.resolve()}?mode=ro&immutable=1", uri=True)
        try:
            result = db.execute("PRAGMA quick_check").fetchone()[0]
        finally:
            db.close()
        if result != "ok":
            raise RuntimeError(f"{name}.db no paso integridad: {result}")
        print(f"{name}.db: OK", flush=True)
    if shutil.disk_usage(Path.home()).free < 2 * 1024**3:
        raise RuntimeError("Menos de 2 GiB libres: revisar almacenamiento primero.")

    with tarfile.open(archive, "r:") as tar:
        for member in tar:
            name = member.name
            while name.startswith("./"):
                name = name[2:]
            if not name.startswith(prefix) or not member.isfile():
                continue
            relative = name[len(prefix):]
            if relative not in roots and not relative.startswith(folders):
                continue
            parts = Path(relative).parts
            if not parts or any(p in ("..", ".", "") for p in parts):
                continue
            source = tar.extractfile(member)
            if source is None:
                continue
            out = stage.joinpath(*parts)
            out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with source, out.open("wb") as target:
                shutil.copyfileobj(source, target)
            out.chmod(0o700 if member.mode & 0o111 else 0o600)
            count += 1
            if count % 1000 == 0:
                print(f"Recuperados {count} archivos...", flush=True)

    for rel in ("SOUL.md", "config.yaml", "memories/MEMORY.md", "memories/USER.md"):
        if not (stage / rel).is_file():
            raise RuntimeError(f"Falta archivo imprescindible: {rel}")

    for name in ("state", "kanban"):
        source = backup / f"database-snapshots/{name}-2026-09-21.db"
        target = stage / f"{name}.db"
        shutil.copyfile(source, target)
        target.chmod(0o600)
    stage.chmod(0o700)
    if dest.exists() or dest.is_symlink():
        raise RuntimeError("Aparecio ~/.hermes durante la preparacion: se cancela.")
    stage.rename(dest)
    print(f"MEMORIA ACTIVA PREPARADA: {count} archivos + 2 bases historicas.", flush=True)
    print("Rutas antiguas de config.yaml pendientes de auditar antes de iniciar gateway.", flush=True)
except Exception:
    if stage.exists():
        shutil.rmtree(stage)
    raise
PY

echo "== Instalando CLI oficial de Hermes (sin setup/gateway/cron) =="
INSTALLER="$(mktemp)"
trap 'rm -f "$INSTALLER"' EXIT
curl -fsSL --retry 3 "https://hermes-agent.nousresearch.com/install.sh" -o "$INSTALLER"
bash "$INSTALLER" --non-interactive --skip-setup --skip-browser --skip-computer-use --no-skills
export PATH="$HOME/.local/bin:$HOME/.hermes/bin:$PATH"
if ! command -v hermes >/dev/null 2>&1; then
    echo "MEMORIA PREPARADA. Instalacion terminada, pero hermes no aparece en PATH."
    exit 3
fi
echo "== Verificacion =="
hermes --version
for rel in state.db kanban.db memories/MEMORY.md memories/USER.md SOUL.md config.yaml; do
    test -s "$DEST/$rel" || { echo "FALTA: $rel"; exit 4; }
    echo "OK: $rel"
done
echo "LISTO: memoria recuperada e instalada la CLI."
echo "Gateway, cron y n8n SIN activar. Auditar rutas antiguas antes de iniciar el agente."
