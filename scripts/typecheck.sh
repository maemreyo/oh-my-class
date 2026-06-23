#!/usr/bin/env bash
# Run basedpyright type checking
# Filters out missing-import errors for third-party libs not installed in dev
set -euo pipefail

echo "🔍 Running basedpyright type check..."

# Run basedpyright and capture output
OUTPUT=$(basedpyright packages/ common/ services/gateway/ 2>&1) || true

# Count errors and warnings
ERRORS=$(echo "$OUTPUT" | grep -c "error:" || true)
WARNINGS=$(echo "$OUTPUT" | grep -c "warning:" || true)

echo "$OUTPUT"
echo ""
echo "📊 Summary: $ERRORS errors, $WARNINGS warnings"

# Fail only on real errors (not missing-import which is expected without full deps)
REAL_ERRORS=$(echo "$OUTPUT" | grep "error:" | grep -v "reportMissingImports" | wc -l || true)
if [ "$REAL_ERRORS" -gt 0 ]; then
    echo "❌ $REAL_ERRORS real type errors found"
    exit 1
fi

echo "✅ No real type errors (missing-import warnings are expected without full deps)"
