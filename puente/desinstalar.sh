#!/usr/bin/env bash
# Rollback del puente. Por defecto NO borra el estado (evita perder el registro).
#   ./desinstalar.sh            -> quita la programación y deja estado y logs
#   ./desinstalar.sh --completo -> quita también ~/.hermes/bridge (pide confirmación)
set -euo pipefail
PUENTE_HOME="${PUENTE_HOME:-$HOME/.hermes/bridge}"

TMP="$(mktemp)"; crontab -l 2>/dev/null > "$TMP" || true
grep -v "puente/lector.py" "$TMP" > "$TMP.clean" || true
crontab "$TMP.clean"
rm -f "$TMP" "$TMP.clean"
echo "programación eliminada del crontab"

for j in $(hermes cron list 2>/dev/null | grep -B1 "Puente Codex" | grep -oE "^  [0-9a-f]{12}" | tr -d ' '); do
  hermes cron remove "$j" >/dev/null 2>&1 && echo "job de Hermes cron $j eliminado" || true
done

if [ "${1:-}" = "--completo" ]; then
  read -r -p "¿Borrar $PUENTE_HOME con estado y logs? [s/N] " r
  if [ "$r" = "s" ] || [ "$r" = "S" ]; then
    rm -rf "$PUENTE_HOME"
    echo "estado y logs eliminados"
  else
    echo "se conserva el estado"
  fi
fi
