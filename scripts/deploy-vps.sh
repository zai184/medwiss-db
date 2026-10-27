#!/usr/bin/env bash
# deploy-vps.sh — full medwiss-db deploy to the VPS (playbook slices 2/3/5).
# Usage: scripts/deploy-vps.sh [--dry-run]
# Backend + frontend as a whole; writes /srv/medwiss/.git-revision so the
# fleet dashboard shows the deployed git sha.
set -euo pipefail

cd "$(dirname "$0")/.."
APP="$PWD"
# Host and port stay out of git. This checkout keeps them in .private/deploy.env.
PRIVATE_ENV="$APP/.private/deploy.env"
if [ -f "$PRIVATE_ENV" ]; then
  set -a
  . "$PRIVATE_ENV"
  set +a
fi
: "${MEDWISS_DEPLOY_HOST:?Set MEDWISS_DEPLOY_HOST in .private/deploy.env}"
: "${MEDWISS_DEPLOY_PORT:?Set MEDWISS_DEPLOY_PORT in .private/deploy.env}"
RSH="ssh -p ${MEDWISS_DEPLOY_PORT}"
HOST="$MEDWISS_DEPLOY_HOST"
DEST="$HOST:/srv/medwiss/app/"
RP='sudo -u medwiss rsync'
DRY=""

[ "${1:-}" = "--dry-run" ] && DRY="--dry-run"

SHA="$(git rev-parse HEAD)"
echo "=== medwiss deploy $(date +%Y%m%d_%H%M%S) sha=$SHA ==="

# Slice 2 — app tree (never .env; never pip)
rsync -a $DRY -e "$RSH" --rsync-path="$RP" \
  --exclude '.venv' --exclude '__pycache__' --exclude '.env' \
  "$APP/api/" "$DEST/api/"
rsync -a $DRY -e "$RSH" --rsync-path="$RP" --exclude '__pycache__' "$APP/search/"   "$DEST/search/"
rsync -a $DRY -e "$RSH" --rsync-path="$RP" --exclude '__pycache__' "$APP/pipeline/" "$DEST/pipeline/"
rsync -a $DRY -e "$RSH" --rsync-path="$RP" --exclude '__pycache__' "$APP/config/"   "$DEST/config/"
rsync -a $DRY -e "$RSH" --rsync-path="$RP" --exclude '__pycache__' "$APP/database/" "$DEST/database/"
rsync -a $DRY -e "$RSH" --rsync-path="$RP" "$APP/data/" "$DEST/data/"
rsync -a $DRY -e "$RSH" --rsync-path="$RP" "$APP/pyproject.toml" "$APP/uv.lock" "$DEST"

# New or removed Python deps: frozen sync against the lock we just copied.
# Side effects after the rsynces stay dry-run-gated: --dry-run must not write
# the revision file or restart services on old code.
if [ -z "$DRY" ]; then
  ssh -p "$MEDWISS_DEPLOY_PORT" "$HOST" 'sudo -u medwiss bash -lc "cd /srv/medwiss/app && UV_PYTHON_PREFERENCE=system uv sync --frozen"'
fi

# Slice 3 — SPA build on tux, rsync static
( cd ui && bun run build )
rsync -a $DRY --delete -e "$RSH" --rsync-path="$RP" "$APP/ui/build/" "$HOST:/srv/medwiss/build/"

if [ -z "$DRY" ]; then
  # Deployed git sha for the fleet dashboard (medwiss-serve /healthz git field)
  echo -n "$SHA" | $RSH "$HOST" 'sudo tee /srv/medwiss/.git-revision >/dev/null'

  # Slice 5 — restart + active check (no UI checks; boss verifies the app)
  $RSH "$HOST" 'sudo systemctl restart medwiss-api medwiss-web && systemctl is-active medwiss-api medwiss-web postgresql'
fi
echo "=== done (sha=$SHA) ==="
