#!/usr/bin/env bash
# Instalación local REVERSIBLE del puente (issue #3).
# No instala servicios de sistema, no abre puertos, no toca credenciales.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LECTOR="$REPO_DIR/puente/lector.py"
PUENTE_HOME="${PUENTE_HOME:-$HOME/.hermes/bridge}"
INTERVALO="${INTERVALO_MINUTOS:-5}"
MODO="${1:-cron}"   # cron | hermes-cron | solo-config

mkdir -p "$PUENTE_HOME/logs"
chmod 700 "$PUENTE_HOME"

if [ ! -f "$PUENTE_HOME/config.json" ]; then
  cp "$REPO_DIR/puente/config.example.json" "$PUENTE_HOME/config.json"
  chmod 600 "$PUENTE_HOME/config.json"
  echo "config creada en $PUENTE_HOME/config.json"
else
  echo "config ya existía; no se sobrescribe"
fi

cmd="PUENTE_HOME=$PUENTE_HOME $(command -v python3) $LECTOR >> $PUENTE_HOME/logs/cron.out 2>&1"

case "$MODO" in
  cron)
    # cron del sistema (cron.service ya está activo en esta instalación).
    TMP="$(mktemp)"; crontab -l 2>/dev/null > "$TMP" || true
    grep -v "puente/lector.py" "$TMP" > "$TMP.clean" || true
    echo "*/$INTERVALO * * * * $cmd" >> "$TMP.clean"
    crontab "$TMP.clean"
    rm -f "$TMP" "$TMP.clean"
    echo "instalado en crontab de usuario cada $INTERVALO min"
    ;;
  hermes-cron)
    # Alternativa oficial: requiere el gateway en marcha para que dispare.
    hermes cron create "every ${INTERVALO}m" \
      --name "Puente Codex -> Hermes (lector)" \
      --script "$REPO_DIR/puente/lector.py" --no-agent
    echo "job de Hermes cron creado (requiere 'hermes gateway' en marcha)"
    ;;
  solo-config)
    echo "solo se creó la configuración; no se programó nada"
    ;;
  *)
    echo "modo desconocido: $MODO (usa cron | hermes-cron | solo-config)" >&2
    exit 2
    ;;
esac

echo
echo "Comprobación manual:"
echo "  PUENTE_HOME=$PUENTE_HOME python3 $LECTOR --verbose"
