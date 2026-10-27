#!/run/current-system/sw/bin/zsh

# Medizinische Wissensdatenbank - Stop Script
# This script stops all services for the Medical Knowledge Database
#
# Kill order matters: leaf processes first, then parents.
# Multiprocessing workers survive parent death and keep spawning tesseract,
# so we must kill bottom-up: tesseract → workers → uvicorn → docker.

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directory — ${0:A:h} is the script dir (BASH_SOURCE is empty in zsh).
# find_project_pids scopes every kill by this prefix, so it must not be the
# caller's cwd — running stop.sh from elsewhere would match nothing.
PROJECT_ROOT="${0:A:h}"

# One compose invocation (compose v2 plugin, sudo for the shared daemon)
dc() { sudo docker compose "$@"; }

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Find PIDs matching a pattern, excluding self.
# pgrep uses ERE (verified: BRE-style `a\|b` alternation never matches), so
# patterns below must be written as `a|b` / `(a|b)`.
find_pids() {
    pgrep -f "$1" 2>/dev/null | while read -r pid; do
        # Skip our own process
        [ "$pid" = "$$" ] && continue
        echo "$pid"
    done
}

# Find PIDs matching a pattern whose working directory is inside this
# project. Generic names (uvicorn, vite, whisper) must never match other
# apps — e.g. the fleet dashboard's own uvicorn was killed by Phase 3 on
# 2026-08-29 because find_pids matched every uvicorn on the host.
find_project_pids() {
    local pid cwd
    for pid in $(find_pids "$1" 2>/dev/null); do
        cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null) || continue
        case "$cwd" in
            "$PROJECT_ROOT"|"$PROJECT_ROOT"/*) echo "$pid" ;;
        esac
    done
}

# Kill every PID in the list with a signal (missing PIDs are ignored).
# Callers pass one multi-line PID string as a single argument — zsh does not
# word-split unquoted scalars, so read the list line by line here. Unsplit,
# `kill -9 "1\n2"` fails and the old `2>/dev/null || true` hid it: multi-PID
# kills were silently doing nothing.
kill_pids() {
    local signal="$1" list
    shift
    list="$*"
    printf '%s\n' "$list" | while IFS= read -r pid; do
        [ -n "$pid" ] || continue
        kill "$signal" "$pid" 2>/dev/null || true
    done
}

# Kill whatever is listening on a TCP port (most reliable method)
kill_port() {
    local port="$1"
    local pids
    pids=$(lsof -ti:"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        print_info "  Port $port: killing PIDs $pids"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 0.5
    fi
}

print_info "Stopping Medizinische Wissensdatenbank services..."

# === Phase 1: Kill leaf processes (tesseract, whisper) ===
# These are the CPU hogs — spawned by batch workers for OCR
print_info "Phase 1: Stopping KI pipeline subprocesses (tesseract, whisper)..."
TESSERACT_PIDS=$(find_project_pids "tesseract.*(ocr|psm|oem)" || true)
WHISPER_PIDS=$(find_project_pids "whisper" || true)
if [ -n "$TESSERACT_PIDS" ]; then
    print_info "  Killing tesseract: $TESSERACT_PIDS"
    kill_pids -9 "$TESSERACT_PIDS"
fi
if [ -n "$WHISPER_PIDS" ]; then
    print_info "  Killing whisper: $WHISPER_PIDS"
    kill_pids -9 "$WHISPER_PIDS"
fi

# === Phase 2: Kill multiprocessing workers ===
# These are children of uvicorn that survive parent SIGTERM.
# They keep processing files and spawning tesseract.
print_info "Phase 2: Stopping batch/pipeline workers..."
WORKER_PIDS=$(find_project_pids "multiprocessing\.(spawn|resource_tracker)" || true)
if [ -n "$WORKER_PIDS" ]; then
    print_info "  Killing multiprocessing workers: $WORKER_PIDS"
    kill_pids -9 "$WORKER_PIDS"
fi

# === Phase 3: Kill uvicorn/FastAPI backend ===
print_info "Phase 3: Stopping FastAPI backend..."
UVICORN_PIDS=$(find_project_pids "uvicorn" || true)
if [ -n "$UVICORN_PIDS" ]; then
    print_info "  Killing uvicorn: $UVICORN_PIDS"
    kill_pids -TERM "$UVICORN_PIDS"
    sleep 1
    kill_pids -9 "$UVICORN_PIDS"
fi

# Also kill `uv run` wrapper if still around
UV_PIDS=$(find_project_pids "uv run.*uvicorn" || true)
if [ -n "$UV_PIDS" ]; then
    kill_pids -9 "$UV_PIDS"
fi

# === Phase 4: Kill SvelteKit/Vite frontend ===
print_info "Phase 4: Stopping SvelteKit frontend..."
VITE_PIDS=$(find_project_pids "vite.*dev|bun.*dev|node.*vite" || true)
if [ -n "$VITE_PIDS" ]; then
    print_info "  Killing vite/bun: $VITE_PIDS"
    kill_pids -9 "$VITE_PIDS"
fi

# === Phase 5: Kill any other project-related processes ===
print_info "Phase 5: Cleanup remaining project processes..."
for pattern in "pipeline/orchestrator" "pipeline/monitor" "services/source_watcher" "batch_import" "run_pipeline" "generate_embeddings"; do
    PIDS=$(find_project_pids "$pattern" || true)
    if [ -n "$PIDS" ]; then
        print_info "  Killing $pattern: $PIDS"
        kill_pids -9 "$PIDS"
    fi
done

# === Phase 6: Kill by port (nuclear option — catches survivors) ===
# This is the most reliable way to free ports. After all named kills above,
# some processes may still linger (e.g. zombie uvicorn, orphaned node).
# Killing by port guarantees the ports are free for the next start.
print_info "Phase 6: Freeing ports..."
kill_port 8000   # FastAPI backend
kill_port 5175   # Vite dev server
kill_port 8080   # Llamaserver (if running locally)
kill_port 8081   # Embedding sidecar

# === Phase 7: Stop Docker containers (postgres + sidecar) ===
print_info "Phase 7: Stopping Docker containers..."
cd "$PROJECT_ROOT" || exit 1 # never compose-down an unrelated project in the caller's cwd
dc down || true # stderr visible: a swallowed down error leaves containers running silently
SIDECAR_COMPOSE="/srv/docker/llamaserver/docker-compose.sidecar.yml"
if [ -f "$SIDECAR_COMPOSE" ]; then
    print_info "Stopping embedding sidecar..."
    dc -f "$SIDECAR_COMPOSE" down || true
fi

# === Phase 8: Final sweep ===
jobs -p 2>/dev/null | xargs -r kill -9 2>/dev/null || true

sleep 0.5

# === Verification ===
# `codegraph` excluded: the codegraph MCP daemon keeps the repo db path in its
# argv, so it matches the pattern while being dev tooling, not a service.
# Second stage keeps only PID-headed lines: a multi-line argv (node -e ...) would
# otherwise leak continuation lines past every -v exclusion.
LEFTOVERS=$(pgrep -af "medwiss|$PROJECT_ROOT" 2>/dev/null | grep -v "grep\|stop.sh\|codegraph\|$$" | grep "^[0-9]" || true)
if [ -n "$LEFTOVERS" ]; then
    echo ""
    print_warning "Some processes may still be running:"
    echo "$LEFTOVERS"
    echo ""
else
    print_success "All services stopped!"
fi

echo ""
echo -e "${GREEN}✓ All services have been stopped${NC}"
echo ""
