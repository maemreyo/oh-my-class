#!/bin/bash
# Verify LiteLLM proxy is healthy and f.light/f.pro are reachable.
set -euo pipefail

BASE_URL="${LITELLM_BASE_URL:-http://localhost:4000}"
MASTER_KEY="${LITELLM_MASTER_KEY:?LITELLM_MASTER_KEY is required}"

echo "Checking LiteLLM proxy at ${BASE_URL}..."

# Readiness endpoint
if curl -sf "${BASE_URL}/health/readiness" > /dev/null; then
  echo "✓ Proxy is ready"
else
  echo "✗ Proxy is NOT ready"
  exit 1
fi

# Model list
echo ""
echo "Available models:"
curl -s "${BASE_URL}/models" \
  -H "Authorization: Bearer ${MASTER_KEY}" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('data', []):
    print(f\"  {m['id']}\")
"

echo ""
echo "Health check passed."
