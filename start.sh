#!/run/current-system/sw/bin/zsh

# Medizinische Wissensdatenbank - Start Script
# Starts PostgreSQL, embedding sidecar, FastAPI backend, SvelteKit frontend.

set -e

# Parse flags
START_QWEN=false
for arg in "$@"; do
    case "$arg" in
        --qwen) START_QWEN=true ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directories — ${0:A:h} is the script dir (BASH_SOURCE is empty in zsh)
PROJECT_ROOT="${0:A:h}"
UI_DIR="$PROJECT_ROOT/ui"

# One compose invocation for the whole script (compose v2 plugin, sudo for the shared daemon)
dc() { sudo docker compose "$@"; }

# `up -d` on a stopped container whose network was deleted fails with
# "network ... not found" (compose reuses the container instead of rewiring it).
# Retry once via down+up, which recreates network and container. A healthy,
# already-running sidecar succeeds on the first `up -d` and never reaches this.
sidecar_up() {
    if ! dc "$@" up -d; then
        print_warning "compose up failed — recreating stale container/network"
        dc "$@" down 2>/dev/null || true
        dc "$@" up -d || true
    fi
}

print_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

# Poll an endpoint until it answers or the timeout (seconds) runs out
wait_for_health() {
    local url="$1" name="$2" max_wait="${3:-60}" waited=0
    while [ $waited -lt "$max_wait" ]; do
        if curl -sf "$url" >/dev/null 2>&1; then
            print_success "$name ready ($url)"
            return 0
        fi
        sleep 2
        waited=$((waited + 2))
    done
    print_error "$name not ready after ${max_wait}s ($url)"
    return 1
}

# Kill an orphaned process still holding a dev port
free_port() {
    if lsof -ti:"$1" >/dev/null 2>&1; then
        print_warning "Port $1 still in use — killing stale process"
        lsof -ti:"$1" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

wait_for_postgres() {
    print_info "Waiting for PostgreSQL to be ready..."
    local attempt=1
    while [ $attempt -le 30 ]; do
        if dc exec -T db pg_isready -U medwiss -d medwiss >/dev/null 2>&1; then
            print_success "PostgreSQL is ready!"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    print_error "PostgreSQL failed to start within 30 seconds"
    return 1
}

# Runs on SIGINT/SIGTERM and then again on EXIT (the `exit` inside fires the
# EXIT trap) — the guard makes it run once, so no double compose-down or second
# sudo prompt while Ctrl+C is still unwinding.
CLEANED=0
cleanup() {
    local st=$? # capture before any command below clobbers it
    if [ "$CLEANED" = 1 ]; then
        return 0
    fi
    CLEANED=1
    print_warning "Shutting down services..."
    dc down || true # stderr visible: a swallowed down error leaves containers running silently
    # Kill Llamaserver if we started it
    pkill -f "llama-server.*qwen35-9b" 2>/dev/null || true
    # Kill background processes
    jobs -p | xargs -r kill 2>/dev/null || true
    # >128 = interrupted by a signal (clean Ctrl+C/SIGTERM); anything else is a real failure
    exit $(( st > 128 ? 0 : st ))
}
trap cleanup SIGINT SIGTERM EXIT

print_info "Starting Medizinische Wissensdatenbank..."
print_info "Project root: $PROJECT_ROOT"

# Check prerequisites
print_info "Checking prerequisites..."
for cmd in docker python3 bun uv; do
    if ! command_exists "$cmd"; then
        print_error "$cmd is not installed."
        case "$cmd" in
            bun) print_info "Install with: curl -fsSL https://bun.sh/install | bash" ;;
            uv)  print_info "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh" ;;
        esac
        exit 1
    fi
done
if ! docker compose version >/dev/null 2>&1; then
    print_error "docker compose plugin is not available."
    exit 1
fi
print_success "All prerequisites found!"

# Start PostgreSQL
print_info "Starting PostgreSQL with Docker..."
cd "$PROJECT_ROOT"
dc up -d
wait_for_postgres

# Embedding sidecar (CPU, Qwen3-Embedding-8B) + optional main Llamaserver live outside the repo
SIDECAR_COMPOSE="/srv/docker/llamaserver/docker-compose.sidecar.yml"
LLAMA_BASE="/srv/docker/llamaserver/docker-compose.yml"
QWEN_OVERRIDE="/srv/docker/llamaserver/models/qwen35-9b.yml"

SIDECAR_OK=false
if [ "$START_QWEN" = true ] && [ -f "$SIDECAR_COMPOSE" ] && [ -f "$LLAMA_BASE" ] && [ -f "$QWEN_OVERRIDE" ]; then
    # Start sidecar + main Llamaserver together so --remove-orphans doesn't kill the sidecar.
    # No --wait: it blocks until BOTH are healthy and can hang for minutes while the 9B
    # model loads. Start detached, poll health separately, tolerate slow loads.
    # Keep compose stderr visible: a swallowed `up -d` failure otherwise only shows
    # up as a health timeout with no cause.
    print_info "Starting embedding sidecar + Llamaserver (qwen35-9b)..."
    sidecar_up -f "$SIDECAR_COMPOSE" -f "$LLAMA_BASE" -f "$QWEN_OVERRIDE"
    wait_for_health "http://localhost:8080/health" "Llamaserver" 120 || true
    # 8B Q6 on CPU takes minutes to load — give it a realistic timeout
    wait_for_health "http://localhost:8081/health" "Embedding sidecar" 300 && SIDECAR_OK=true
elif [ -f "$SIDECAR_COMPOSE" ]; then
    print_info "Starting embedding sidecar on :8081 (CPU-only)..."
    sidecar_up -f "$SIDECAR_COMPOSE"
    wait_for_health "http://localhost:8081/health" "Embedding sidecar" 300 && SIDECAR_OK=true
else
    print_warning "Sidecar compose not found at $SIDECAR_COMPOSE — Leitlinien search will be unavailable"
fi

# Initialize database if needed
print_info "Checking database initialization..."
if ! dc exec -T db psql -U medwiss -d medwiss -c "SELECT 1 FROM knowledge_entries LIMIT 1" >/dev/null 2>&1; then
    print_info "Initializing database schema..."
    if [ -f "$PROJECT_ROOT/database/seeds.sql" ]; then
        dc exec -T db psql -U medwiss -d medwiss < "$PROJECT_ROOT/database/seeds.sql"
        print_success "Database initialized!"
    else
        print_warning "No seeds.sql found. Database may need manual initialization."
    fi
else
    print_success "Database already initialized!"
fi

# Install Python dependencies with uv
print_info "Installing Python dependencies with uv..."
cd "$PROJECT_ROOT"
uv sync
print_success "Python dependencies installed!"

# Start backend — poll instead of a fixed sleep (cold uvicorn import can beat sleep 3)
print_info "Starting FastAPI backend..."
free_port 8000
uv run python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 &
wait_for_health "http://localhost:8000/health" "Backend API" 60 || exit 1

# Install frontend deps (no-op when the lockfile is already applied)
print_info "Installing frontend dependencies with bun..."
cd "$UI_DIR"
bun install

# Start frontend
print_info "Starting SvelteKit frontend..."
free_port 5175
bun run dev --host &
wait_for_health "http://localhost:5175" "Frontend" 60 || exit 1

# Open the site in the default browser
print_info "Opening http://localhost:5175 in the browser..."
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:5175" >/dev/null 2>&1 || print_warning "Could not auto-open browser"
fi

echo ""
echo "========================================"
echo -e "${GREEN}✓ All services are running!${NC}"
echo "========================================"
echo ""
echo -e "${BLUE}Frontend:${NC}     http://localhost:5175"
echo -e "${BLUE}API:${NC}          http://localhost:8000"
echo -e "${BLUE}API Docs:${NC}     http://localhost:8000/docs"
if [ "$START_QWEN" = true ]; then
    echo -e "${BLUE}Llamaserver:${NC}  http://localhost:8080 (qwen35-9b)"
else
    echo -e "${BLUE}Llamaserver:${NC}  http://localhost:8080 (not started — use --qwen)"
fi
if [ "$SIDECAR_OK" = true ]; then
    echo -e "${BLUE}Embed Sidecar:${NC} http://localhost:8081 (CPU, Leitlinien search)"
else
    echo -e "${YELLOW}Embed Sidecar:${NC} NOT READY — Leitlinien embed search unavailable (see compose output above)"
fi
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for user interrupt
wait
