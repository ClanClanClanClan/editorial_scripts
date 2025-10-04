#!/bin/bash
#
# Editorial Command Center - Production Deployment Script
#
# Usage: ./deploy.sh [start|stop|restart|status]
#

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[ECC]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Load credentials
load_credentials() {
    log "Loading credentials from keychain..."
    if [ -f ~/.editorial_scripts/load_all_credentials.sh ]; then
        source ~/.editorial_scripts/load_all_credentials.sh
        success "Credentials loaded"
    else
        warn "Credentials script not found - extractors may fail"
    fi
}

# Start infrastructure
start_infrastructure() {
    log "Starting Docker infrastructure..."

    # Check if Homebrew PostgreSQL is running (causes port conflict)
    if lsof -i :5432 | grep -q postgres && ! docker ps | grep -q ecc_postgres; then
        warn "Stopping Homebrew PostgreSQL to avoid port conflict..."
        brew services stop postgresql@15 2>/dev/null || true
    fi

    docker-compose up -d

    # Wait for services to be healthy
    log "Waiting for services to start..."
    sleep 10

    # Check health
    if docker ps | grep -q ecc_postgres && \
       docker ps | grep -q ecc_redis && \
       docker ps | grep -q ecc_prometheus; then
        success "Infrastructure started"
    else
        error "Some services failed to start"
        docker-compose ps
        exit 1
    fi
}

# Stop infrastructure
stop_infrastructure() {
    log "Stopping Docker infrastructure..."
    docker-compose down
    success "Infrastructure stopped"
}

# Start API server
start_api() {
    log "Starting FastAPI backend..."

    export DATABASE_URL="postgresql+asyncpg://ecc_user:ecc_password@localhost:5432/ecc_db"
    export REDIS_URL="redis://localhost:6380"

    # Check if already running
    if pgrep -f "uvicorn src.ecc.main:app" > /dev/null; then
        warn "API server already running (PID: $(pgrep -f 'uvicorn src.ecc.main:app'))"
        return
    fi

    # Start in background
    nohup poetry run uvicorn src.ecc.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        > logs/api.log 2>&1 &

    API_PID=$!
    echo $API_PID > logs/api.pid

    sleep 3

    # Check if started
    if curl -s http://localhost:8000/health > /dev/null; then
        success "API server started (PID: $API_PID)"
        log "Health endpoint: http://localhost:8000/health"
        log "API docs: http://localhost:8000/docs"
    else
        error "API server failed to start"
        tail -20 logs/api.log
        exit 1
    fi
}

# Stop API server
stop_api() {
    log "Stopping API server..."

    if [ -f logs/api.pid ]; then
        kill $(cat logs/api.pid) 2>/dev/null || true
        rm logs/api.pid
        success "API server stopped"
    else
        # Fallback: find and kill by process name
        pkill -f "uvicorn src.ecc.main:app" || true
        success "API processes killed"
    fi
}

# Show status
show_status() {
    log "===== INFRASTRUCTURE STATUS ====="
    docker-compose ps

    log "\n===== API SERVER STATUS ====="
    if pgrep -f "uvicorn src.ecc.main:app" > /dev/null; then
        success "API server running (PID: $(pgrep -f 'uvicorn src.ecc.main:app'))"
        log "Health check:"
        curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || \
            error "Health check failed"
    else
        warn "API server not running"
    fi

    log "\n===== SERVICES ====="
    log "PostgreSQL:  http://localhost:5432"
    log "Redis:       http://localhost:6380"
    log "Prometheus:  http://localhost:9092"
    log "Grafana:     http://localhost:3002 (admin/admin)"
    log "pgAdmin:     http://localhost:5050 (admin/admin)"
    log "API:         http://localhost:8000"
    log "API Docs:    http://localhost:8000/docs"
}

# Create necessary directories
setup_directories() {
    mkdir -p logs
    mkdir -p downloads/{MF,MOR,FS,JOTA,MAFE,SICON,SIFIN,NACO}
}

# Main command handler
main() {
    setup_directories

    case "${1:-start}" in
        start)
            log "Starting Editorial Command Center..."
            load_credentials
            start_infrastructure
            start_api
            success "\n🚀 ECC is running!"
            show_status
            ;;

        stop)
            log "Stopping Editorial Command Center..."
            stop_api
            stop_infrastructure
            success "ECC stopped"
            ;;

        restart)
            log "Restarting Editorial Command Center..."
            $0 stop
            sleep 2
            $0 start
            ;;

        status)
            show_status
            ;;

        logs)
            log "Showing recent logs..."
            log "\n===== API Logs ====="
            tail -50 logs/api.log 2>/dev/null || warn "No API logs found"

            log "\n===== Docker Logs ====="
            docker-compose logs --tail=50
            ;;

        *)
            echo "Usage: $0 {start|stop|restart|status|logs}"
            echo ""
            echo "Commands:"
            echo "  start    - Start all services"
            echo "  stop     - Stop all services"
            echo "  restart  - Restart all services"
            echo "  status   - Show service status"
            echo "  logs     - Show recent logs"
            exit 1
            ;;
    esac
}

main "$@"
