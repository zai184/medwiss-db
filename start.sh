#!/run/current-system/sw/bin/zsh

# Medizinische Wissensdatenbank - Start Script
# This script starts all required services for the Medical Knowledge Database

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

# Project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
UI_DIR="$PROJECT_ROOT/ui"

# Function to print colored output
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

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for PostgreSQL
wait_for_postgres() {
    print_info "Waiting for PostgreSQL to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if sudo docker-compose exec -T db pg_isready -U medwiss -d medwiss >/dev/null 2>&1; then
            print_success "PostgreSQL is ready!"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    print_error "PostgreSQL failed to start within $max_attempts seconds"
    return 1
}

# Function to cleanup on exit
cleanup() {
    print_warning "Shutting down services..."
    sudo docker-compose down 2>/dev/null || true
    # Kill Llamaserver if we started it
    pkill -f "llama-server.*qwen35-9b" 2>/dev/null || true
    # Kill background processes
    jobs -p | xargs -r kill 2>/dev/null || true
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

print_info "Starting Medizinische Wissensdatenbank..."
print_info "Project root: $PROJECT_ROOT"

# Check prerequisites
print_info "Checking prerequisites..."

if ! command_exists docker; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command_exists docker-compose; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

if ! command_exists python3; then
    print_error "Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

if ! command_exists bun; then
    print_error "bun is not installed. Please install bun first."
    print_info "Install with: curl -fsSL https://bun.sh/install | bash"
    exit 1
fi

if ! command_exists uv; then
    print_error "uv is not installed. Please install uv first."
    print_info "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

print_success "All prerequisites found!"

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    if [ -f "$PROJECT_ROOT/../.env.example" ]; then
        print_warning ".env file not found. Copying from .env.example..."
        cp "$PROJECT_ROOT/../.env.example" "$PROJECT_ROOT/.env"
    elif [ -f "$PROJECT_ROOT/.env.example" ]; then
        print_warning ".env file not found. Copying from .env.example..."
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    else
        print_warning ".env file not found. Using default configuration."
    fi
fi

# Start PostgreSQL
print_info "Starting PostgreSQL with Docker..."
cd "$PROJECT_ROOT"
sudo docker-compose up -d

# Wait for PostgreSQL
wait_for_postgres

# Start embedding sidecar (CPU-only, Qwen3-Embedding-8B for Leitlinien search)
SIDECAR_COMPOSE="/srv/docker/llamaserver/docker-compose.sidecar.yml"
LLAMA_BASE="/srv/docker/llamaserver/docker-compose.yml"
QWEN_OVERRIDE="/srv/docker/llamaserver/models/qwen35-9b.yml"

# Wait for a service health endpoint with timeout (seconds)
wait_for_health() {
    local url="$1"
    local name="$2"
    local max_wait="${3:-60}"
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            print_success "$name started on $url"
            return 0
        fi
        sleep 2
        waited=$((waited + 2))
    done
    print_warning "$name not ready after ${max_wait}s (may still be loading)"
    return 1
}

if [ "$START_QWEN" = true ] && [ -f "$SIDECAR_COMPOSE" ] && [ -f "$LLAMA_BASE" ] && [ -f "$QWEN_OVERRIDE" ]; then
    # Start sidecar + main Llamaserver together so --remove-orphans doesn't kill the sidecar
    # NOTE: no --wait here — it blocks until BOTH containers are healthy and can hang
    # for minutes while the 9B model loads. Start detached, then poll health separately.
    print_info "Starting embedding sidecar + Llamaserver (qwen35-9b)..."
    sudo docker compose -f "$SIDECAR_COMPOSE" -f "$LLAMA_BASE" -f "$QWEN_OVERRIDE" up -d 2>/dev/null
    wait_for_health "http://localhost:8080/health" "Llamaserver" 120
    wait_for_health "http://localhost:8081/health" "Embedding sidecar" 60
elif [ -f "$SIDECAR_COMPOSE" ]; then
    print_info "Starting embedding sidecar on :8081 (CPU-only)..."
    sudo docker compose -f "$SIDECAR_COMPOSE" up -d 2>/dev/null
    wait_for_health "http://localhost:8081/health" "Embedding sidecar" 60
else
    print_warning "Sidecar compose not found at $SIDECAR_COMPOSE — Leitlinien search will be unavailable"
fi

# Initialize database if needed
print_info "Checking database initialization..."
if ! sudo docker-compose exec -T db psql -U medwiss -d medwiss -c "SELECT 1 FROM knowledge_entries LIMIT 1" >/dev/null 2>&1; then
    print_info "Initializing database schema..."
    if [ -f "$PROJECT_ROOT/database/seeds.sql" ]; then
        sudo docker-compose exec -T db psql -U medwiss -d medwiss < "$PROJECT_ROOT/database/seeds.sql"
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

# Start Backend API in background
print_info "Starting FastAPI backend..."
cd "$PROJECT_ROOT"
# Pre-flight: ensure port 8000 is free (orphaned uvicorn from a prior run)
if lsof -ti:8000 >/dev/null 2>&1; then
    print_warning "Port 8000 still in use — killing stale process"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi
uv run python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
sleep 3

# Check if backend actually bound to the port (not just process alive)
if ! curl -s http://localhost:8000/health >/dev/null 2>&1; then
    print_error "Backend failed to start!"
    kill -9 $BACKEND_PID 2>/dev/null || true
    exit 1
fi

print_success "Backend started on http://localhost:8000"

# Install frontend dependencies
print_info "Installing frontend dependencies with bun..."
cd "$UI_DIR"
if [ ! -d "node_modules" ]; then
    bun install
    print_success "Frontend dependencies installed!"
else
    print_success "Frontend dependencies already installed!"
fi

# Start Frontend in background
print_info "Starting SvelteKit frontend..."
if lsof -ti:5175 >/dev/null 2>&1; then
    print_warning "Port 5175 still in use — killing stale process"
    lsof -ti:5175 | xargs kill -9 2>/dev/null || true
    sleep 1
fi
bun run dev --host &
FRONTEND_PID=$!
sleep 4

# Check if frontend actually responds (not just process alive)
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:5175 2>/dev/null | grep -q "200"; then
    print_error "Frontend failed to start!"
    kill -9 $FRONTEND_PID 2>/dev/null || true
    exit 1
fi

print_success "Frontend started on http://localhost:5175"

# Open the site in the default browser
print_info "Opening http://localhost:5175 in the browser..."
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:5175" >/dev/null 2>&1 || print_warning "Could not auto-open browser"
elif command -v open >/dev/null 2>&1; then
    open "http://localhost:5175" >/dev/null 2>&1 || print_warning "Could not auto-open browser"
elif command -v powershell >/dev/null 2>&1; then
    powershell -Command "Start-Process 'http://localhost:5175'" >/dev/null 2>&1 || print_warning "Could not auto-open browser"
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
echo -e "${BLUE}Embed Sidecar:${NC} http://localhost:8081 (CPU, Leitlinien search)"
echo ""
echo -e "${YELLOW}Default Credentials:${NC}"
echo "  Username: admin"
echo "  Password: test123"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for user interrupt
wait
