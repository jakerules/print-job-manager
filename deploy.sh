#!/bin/bash
# deploy.sh - Print Job Manager deployment script
# Usage: ./deploy.sh [dev|prod]

set -e

MODE="${1:-dev}"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🖨️  Print Job Manager - Deploy ($MODE)"
echo "========================================"

# --- Backend setup ---
setup_backend() {
    echo ""
    echo "📦 Setting up backend..."
    cd "$ROOT_DIR/backend"

    # Create venv if missing
    if [ ! -d "venv" ]; then
        echo "  Creating Python virtual environment..."
        python3 -m venv venv
    fi

    source venv/bin/activate
    pip install -q -r requirements.txt

    # Initialize database
    echo "  Initializing database..."
    python3 -c "from database.db_config import init_db; init_db()"

    # Run migrations
    echo "  Running migrations..."
    python3 migrations/run_migrations.py

    echo "  ✅ Backend ready"
}

# --- Frontend setup ---
setup_frontend() {
    echo ""
    echo "📦 Setting up frontend..."
    cd "$ROOT_DIR/frontend"

    if ! command -v node &> /dev/null; then
        echo "  ⚠️  Node.js not found. Install Node.js 18+ to build frontend."
        echo "     brew install node   OR   https://nodejs.org/en/download"
        return 1
    fi

    echo "  Node $(node --version), npm $(npm --version)"
    npm ci --silent 2>/dev/null || npm install --silent
    echo "  ✅ Frontend dependencies installed"
}

# --- Run dev ---
run_dev() {
    echo ""
    echo "🚀 Starting development servers..."

    cd "$ROOT_DIR/backend"
    source venv/bin/activate

    # Start backend
    echo "  Starting backend on :5000..."
    python3 api/app.py &
    BACKEND_PID=$!

    # Start frontend if node available
    if command -v node &> /dev/null; then
        cd "$ROOT_DIR/frontend"
        echo "  Starting frontend on :5173..."
        npx vite --host &
        FRONTEND_PID=$!
    fi

    echo ""
    echo "  📍 Backend:  http://localhost:5000"
    echo "  📍 Frontend: http://localhost:5173"
    echo "  📍 API docs: http://localhost:5000/api/health"
    echo ""
    echo "  Press Ctrl+C to stop"

    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
    wait
}

# --- Run prod (Docker) ---
run_prod() {
    echo ""
    if ! command -v docker &> /dev/null; then
        echo "  ❌ Docker not found. Install Docker to run production mode."
        exit 1
    fi

    echo "🐳 Building and starting Docker containers..."
    cd "$ROOT_DIR/docker"
    docker compose up --build -d

    echo ""
    echo "  📍 Application: http://localhost:80"
    echo "  📍 API:         http://localhost:5000"
    echo ""
    echo "  docker compose logs -f    # view logs"
    echo "  docker compose down       # stop"
}

# --- Run tests ---
run_tests() {
    echo ""
    echo "🧪 Running tests..."
    cd "$ROOT_DIR/backend"
    source venv/bin/activate
    python3 -m pytest tests/ -v --tb=short
}

# --- Main ---
case "$MODE" in
    dev)
        setup_backend
        setup_frontend || true
        run_dev
        ;;
    prod)
        run_prod
        ;;
    test)
        setup_backend
        run_tests
        ;;
    setup)
        setup_backend
        setup_frontend || true
        echo ""
        echo "✅ Setup complete! Run './deploy.sh dev' to start."
        ;;
    *)
        echo "Usage: $0 [dev|prod|test|setup]"
        echo ""
        echo "  dev   - Start development servers (default)"
        echo "  prod  - Build and run Docker containers"
        echo "  test  - Run backend test suite"
        echo "  setup - Install dependencies only"
        exit 1
        ;;
esac
