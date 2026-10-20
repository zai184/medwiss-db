#!/run/current-system/sw/bin/zsh
# Pydantic → contracts/api/openapi.json → ui/src/lib/api-types.d.ts
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
uv run python "$ROOT/scripts/export_openapi.py"
(cd "$ROOT/ui" && bun run gen:api)
echo "OpenAPI → TS types updated"
