#!/usr/bin/env bash
# oh-my-class dev environment bootstrap
set -euo pipefail

echo "🚀 Setting up oh-my-class development environment..."

# ── Validate .env exists ──
if [ ! -f .env ]; then
  echo "❌ .env file not found. Copying from .env.example..."
  cp .env.example .env
  echo "⚠️  Please edit .env with real values before continuing."
  echo "   At minimum, set: NINEROUTER_API_KEY, POSTGRES_PASSWORD, JWT_SECRET"
  exit 1
fi

# ── Check required vars ──
required_vars=("NINEROUTER_API_KEY" "POSTGRES_PASSWORD" "JWT_SECRET")
missing=()
for var in "${required_vars[@]}"; do
  if [ -z "${!var:-}" ]; then
    missing+=("$var")
  fi
done

if [ ${#missing[@]} -gt 0 ]; then
  echo "❌ Missing required env vars: ${missing[*]}"
  echo "   Edit .env and set these values."
  exit 1
fi

# ── Python workspace ──
echo "📦 Setting up Python workspace with uv..."
if command -v uv &>/dev/null; then
  uv sync
else
  echo "⚠️  uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "   Falling back to pip..."
  pip install -e packages/agents
  pip install -e packages/quality
  pip install -e common/contracts
  pip install -e services/gateway
fi

# ── TypeScript dependencies ──
echo "📦 Installing TypeScript dependencies..."
if command -v pnpm &>/dev/null; then
  pnpm install
else
  echo "⚠️  pnpm not found. Install: npm install -g pnpm"
  exit 1
fi

# ── Theme generation ──
echo "🎨 Generating theme CSS files..."
python scripts/generate_theme.py

# ── Start services ──
echo "🐳 Starting Docker services..."
docker compose -f infra/compose/docker-compose.yml up -d

echo ""
echo "✅ Development environment ready!"
echo "   Gateway:    http://localhost:8001"
echo "   Dashboard:  http://localhost:3000"
echo "   LiteLLM:    http://localhost:4000"
echo "   9Router:    http://localhost:20128"
echo ""
echo "⚠️  Remember: ALL LLM traffic routes through 9Router (port 20128)"
echo "   If 9Router is down, system fails safely — no paid fallbacks."
