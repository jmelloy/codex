#!/bin/bash

# Codex Development Startup Script

echo "🚀 Starting Codex Development Environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.14+"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 20+"
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p data

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
uv pip install -e ".[dev]"

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo "✅ Setup complete!"
echo ""
echo "To start the development servers:"
echo ""
echo "Backend (Terminal 1):"
echo "  uvicorn backend.api.main:app --reload --port 8000"
echo ""
echo "Frontend (Terminal 2):"
echo "  cd frontend && npm run dev"
echo ""
echo "Or use Docker:"
echo "  docker-compose up -d"
echo ""
echo "Access:"
echo "  - Frontend: http://localhost:5173"
echo "  - Backend API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
