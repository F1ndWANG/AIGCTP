#!/bin/bash
# AI Life Recommender - Startup Script
# Usage: bash start.sh        (start all services)
#        bash start.sh --seed  (start all services + seed demo data)

echo "🚀 Starting AI Life Recommender..."

# Check .env
if [ ! -f .env ]; then
  echo "📝 Creating .env from .env.example..."
  cp .env.example .env
  echo "⚠️  Please edit .env with your API keys!"
  exit 1
fi

# Start infrastructure (PostgreSQL & Redis if available via Docker)
if command -v docker &> /dev/null && [ -f docker-compose.yml ]; then
  echo "🐳 Starting PostgreSQL & Redis..."
  docker compose up -d
  echo "⏳ Waiting for services to be ready..."
  sleep 3
else
  echo "ℹ️  Docker not found, assuming external PostgreSQL/Redis or SQLite mode"
fi

# Install backend deps
echo "📦 Installing backend dependencies..."
pip install -q -r backend/requirements.txt 2>/dev/null

# Seed demo data if --seed flag is set
if [ "$1" = "--seed" ]; then
  echo "🌱 Seeding demo data..."
  cd backend && python seed_data.py && cd ..
fi

# Run backend
echo "🌐 Starting backend on http://localhost:8000..."
cd backend && python run.py &
BACKEND_PID=$!
cd ..

# Wait for backend health check
echo "⏳ Waiting for backend..."
for i in $(seq 1 15); do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend ready!"
    break
  fi
  sleep 1
done

# Install & run frontend
echo "📦 Installing frontend dependencies..."
cd frontend
if [ ! -d node_modules ]; then
  npm install --silent
fi
echo "🌐 Starting frontend on http://localhost:3000..."
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ All services started!"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "   Demo account (after --seed):  demo / demo123"
echo ""
echo "Press Ctrl+C to stop all services"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
