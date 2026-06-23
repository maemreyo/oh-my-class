#!/usr/bin/env bash
# Run Alembic migrations
set -euo pipefail

cd services/gateway
alembic upgrade head
echo "✅ Migrations applied"
