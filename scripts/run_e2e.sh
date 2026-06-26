#!/usr/bin/env bash
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/.scratch/api-test-output"
GATEWAY_LOG="$OUTPUT_DIR/gateway.log"
FLOW_LOG="$OUTPUT_DIR/e2e.log"
GATEWAY_PORT=8001
TIMEOUT=900
PROGRESS_INTERVAL=20

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} $*"; }
ok()   { echo -e "${GREEN}[$(date +%H:%M:%S)] ✓${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date +%H:%M:%S)] ⚠${NC} $*"; }
fail() { echo -e "${RED}[$(date +%H:%M:%S)] ✗${NC} $*"; }

# ── Step 1: Kill old processes ────────────────────────────────────────────────
log "Killing old gateway and flow processes..."
lsof -ti:$GATEWAY_PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
pkill -f "run_live_flow.py" 2>/dev/null || true
sleep 1
ok "Old processes killed"

# ── Step 2: Clean old logs ────────────────────────────────────────────────────
mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR"/*.log "$OUTPUT_DIR"/*.json "$OUTPUT_DIR"/*.html "$OUTPUT_DIR"/*.pid
ok "Old logs cleaned"

# ── Step 3: Load env and start gateway ────────────────────────────────────────
log "Starting gateway on port $GATEWAY_PORT..."
cd "$PROJECT_ROOT"
set -a
source .env
set +a

nohup .venv/bin/python -m uvicorn services.gateway.main:app \
    --host 127.0.0.1 \
    --port $GATEWAY_PORT \
    --reload \
    > "$GATEWAY_LOG" 2>&1 &
GATEWAY_PID=$!
echo $GATEWAY_PID > "$OUTPUT_DIR/gateway.pid"

# Wait for health
log "Waiting for gateway to be ready..."
for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:$GATEWAY_PORT/health" > /dev/null 2>&1; then
        ok "Gateway ready (pid=$GATEWAY_PID)"
        break
    fi
    if [ $i -eq 30 ]; then
        fail "Gateway failed to start after 30s"
        cat "$GATEWAY_LOG" | tail -20
        exit 1
    fi
    sleep 1
done

# ── Step 4: Run E2E flow ─────────────────────────────────────────────────────
log "Running E2E flow (timeout=${TIMEOUT}s)..."
cd "$PROJECT_ROOT"
.venv/bin/python3 .scratch/api-test-output/run_live_flow.py \
    --timeout $TIMEOUT \
    --progress-interval $PROGRESS_INTERVAL \
    2>&1 | tee "$OUTPUT_DIR/e2e-stdout.log"
FLOW_EXIT=${PIPESTATUS[0]}

# ── Step 5: Collect results ──────────────────────────────────────────────────
echo ""
log "═══════════════════════════════════════════════════════════"
if [ $FLOW_EXIT -eq 0 ]; then
    ok "E2E flow completed successfully"
else
    fail "E2E flow failed (exit=$FLOW_EXIT)"
fi

# Show summary if it exists
if [ -f "$OUTPUT_DIR/summary.json" ]; then
    echo ""
    log "Summary:"
    cat "$OUTPUT_DIR/summary.json"
fi

# Show gateway LLM calls
echo ""
log "Gateway LLM calls:"
grep -E "llm\.call\.(start|success|failure)" "$GATEWAY_LOG" 2>/dev/null | \
    python3 -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        msg = d.get('message', '')
        ts = d.get('timestamp', '')
        level = d.get('level', '')
        marker = '✓' if 'success' in msg else ('✗' if 'failure' in msg else '→')
        print(f'  {ts} {marker} {msg}')
    except: pass
" 2>/dev/null || warn "Could not parse gateway log"

# Show errors if any
ERRORS=$(grep -c '"level": "ERROR"' "$GATEWAY_LOG" 2>/dev/null || echo "0")
WARNINGS=$(grep -c '"level": "WARNING"' "$GATEWAY_LOG" 2>/dev/null || echo "0")
if [ "$ERRORS" != "0" ] || [ "$WARNINGS" != "0" ]; then
    echo ""
    log "Errors ($ERRORS) and Warnings ($WARNINGS):"
    grep -E '"level": "(ERROR|WARNING)"' "$GATEWAY_LOG" 2>/dev/null | \
        python3 -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        ts = d.get('timestamp', '')
        level = d.get('level', '')
        msg = d.get('message', '')[:200]
        print(f'  {ts} [{level}] {msg}')
    except: pass
" 2>/dev/null || true
fi

echo ""
log "Output files:"
ls -la "$OUTPUT_DIR"/*.json "$OUTPUT_DIR"/*.html "$OUTPUT_DIR"/*.log 2>/dev/null | \
    awk '{print "  " $NF " (" $5 " bytes)"}'

echo ""
log "═══════════════════════════════════════════════════════════"

# ── Step 6: Cleanup ──────────────────────────────────────────────────────────
log "Stopping gateway..."
kill $GATEWAY_PID 2>/dev/null || true
wait $GATEWAY_PID 2>/dev/null || true
ok "Gateway stopped"

exit $FLOW_EXIT
