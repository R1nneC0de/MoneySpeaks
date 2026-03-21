#!/bin/bash
# MoneySpeaks — Full project setup
set -e

echo "=== MoneySpeaks Setup ==="

# Backend
echo ""
echo "--- Backend ---"
cd "$(dirname "$0")/../backend"

if [ ! -f .env ]; then
    cp ../.env.example .env
    echo "Created backend/.env from template"
fi

echo "Installing Python dependencies..."
pip install -r requirements.txt

# Frontend
echo ""
echo "--- Frontend ---"
cd ../frontend

echo "Installing Node dependencies..."
npm install

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To start:"
echo "  Backend:  cd backend && uvicorn backend.main:app --reload --port 8000"
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "The app runs in mock mode by default (no API keys needed)."
echo "Add keys to backend/.env to enable real integrations."
