#!/bin/bash
# One-click demo script for CPS Growth Copilot

set -e

echo "🚀 Starting CPS Growth Copilot Demo..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check dependencies
echo "📋 Checking dependencies..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install Node.js 18+ first."
    exit 1
fi

echo "✅ Dependencies check passed"
echo ""

# Step 1: Start PostgreSQL
echo "🐘 Starting PostgreSQL container..."
cd app/infra
docker-compose up -d postgres
cd ../..

echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 10

# Step 2: Initialize database
echo "📊 Initializing database..."
if command -v psql &> /dev/null; then
    export PGPASSWORD=${POSTGRES_PASSWORD:-cps_password}
    psql -h localhost -p 5432 -U cps_user -d cps_growth -f app/infra/postgres/init.sql || echo "⚠️  Schema may already exist"
else
    echo "⚠️  psql not found, skipping schema init (should be auto-init by docker-compose)"
fi

# Step 3: Load sample data
echo "📦 Loading sample data..."
cd scripts
python3 load_sample_data.py
cd ..

# Step 4: Setup backend
echo "🔧 Setting up backend..."
cd app/backend
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate 2>/dev/null || . venv/bin/activate
pip install -q -e . || pip install -q fastapi uvicorn sqlalchemy asyncpg pydantic python-dotenv

echo "🚀 Starting backend server..."
uvicorn src.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ../..

# Step 5: Setup frontend
echo "🎨 Setting up frontend..."
cd app/frontend
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

echo "🚀 Starting frontend server..."
npm run dev &
FRONTEND_PID=$!
cd ../..

# Wait a bit for servers to start
sleep 5

echo ""
echo "${GREEN}✅ Demo is running!${NC}"
echo ""
echo "📍 Access points:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "🧪 Example API calls:"
echo ""
echo "   # Health check"
echo "   curl http://localhost:8000/health"
echo ""
echo "   # Get taoke metrics"
echo "   curl http://localhost:8000/metrics/taoke/1?window=7d"
echo ""
echo "   # Get taoke diagnosis"
echo "   curl http://localhost:8000/diagnosis/taoke/1?window=14d"
echo ""
echo "   # Get merchant metrics"
echo "   curl http://localhost:8000/metrics/merchant/1?window=7d"
echo ""
echo "   # Get opportunities"
echo "   curl http://localhost:8000/opportunities/taoke/1?window=14d"
echo ""
echo "   # Run alerts"
echo "   curl -X POST http://localhost:8000/alerts/run"
echo ""
echo "${YELLOW}⚠️  Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for user interrupt
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker-compose -f app/infra/docker-compose.yml down; exit" INT

wait

