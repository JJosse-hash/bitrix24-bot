#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd "$PROJECT_DIR/.." && pwd)"
API_SRC="$PROJECT_DIR/apps/api"
API_MIRROR="$REPO_DIR/apps/api"
BRANCH="${GIT_BRANCH:-main}"
MESSAGE="${1:-}"

cd "$REPO_DIR"

if [[ ! -d "$API_SRC" ]]; then
  echo "No existe $API_SRC"
  exit 1
fi

echo "Sincronizando API canonica hacia espejo de Render..."
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache/' \
    "$API_SRC/" "$API_MIRROR/"
else
  find "$API_MIRROR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
  tar -C "$API_SRC" \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    -cf - . | tar -C "$API_MIRROR" -xf -
fi

if [[ -x ".venv/bin/python" ]]; then
  echo "Corriendo pruebas del bot..."
  .venv/bin/python -m pytest apps/api/tests/test_bitrix_automation.py -k 'not endpoint'
else
  echo "No existe .venv; salto pruebas locales."
fi

git add -A

if git diff --cached --quiet; then
  echo "No hay cambios para subir."
else
  if [[ -z "$MESSAGE" ]]; then
    MESSAGE="Actualiza AgentVentas BOT $(date '+%Y-%m-%d %H:%M')"
  fi
  git commit -m "$MESSAGE"
fi

if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  ASKPASS_FILE="$(mktemp)"
  chmod 700 "$ASKPASS_FILE"
  cat > "$ASKPASS_FILE" <<'EOF'
#!/usr/bin/env bash
case "$1" in
  *Username*) echo "x-access-token" ;;
  *) echo "$GITHUB_TOKEN" ;;
esac
EOF
  trap 'rm -f "$ASKPASS_FILE"' EXIT
  GIT_TERMINAL_PROMPT=0 GIT_ASKPASS="$ASKPASS_FILE" git push origin "HEAD:$BRANCH"
else
  git push origin "HEAD:$BRANCH"
fi

echo "Listo. GitHub recibio el cambio y Render debe iniciar autodeploy."
