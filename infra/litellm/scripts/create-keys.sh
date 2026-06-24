#!/bin/bash
# Create virtual keys per agent type for cost attribution.
# Run after LiteLLM proxy is up. Output keys go into .env.production.
set -euo pipefail

BASE_URL="${LITELLM_BASE_URL:-http://localhost:4000}"
MASTER_KEY="${LITELLM_MASTER_KEY:?LITELLM_MASTER_KEY is required}"

create_key() {
  local alias="$1"
  local models="$2"
  local budget="$3"

  curl -s -X POST "${BASE_URL}/key/generate" \
    -H "Authorization: Bearer ${MASTER_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"key_alias\": \"${alias}\",
      \"models\": ${models},
      \"max_budget\": ${budget},
      \"budget_duration\": \"1mo\",
      \"rpm_limit\": 100
    }" | python3 -c "import sys, json; print(json.load(sys.stdin)['key'])"
}

echo "Creating virtual keys for oh-my-class agents..."
echo "content-creator: $(create_key 'content-creator' '["f.pro"]' 50)"
echo "llm-judge:       $(create_key 'llm-judge'       '["f.pro"]' 30)"
echo "fact-checker:    $(create_key 'fact-checker'     '["f.pro"]' 20)"
echo "planner:         $(create_key 'planner'          '["f.light","f.pro"]' 10)"
echo "summarizer:      $(create_key 'summarizer'       '["f.light"]' 10)"
echo ""
echo "Done. Add the above keys to .env.production as LLM_CLIENT_API_KEY."
