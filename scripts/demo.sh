#!/bin/bash
# MoneySpeaks — Run demo scenarios
# Triggers all 3 demo scenarios in recommended order

set -e

BASE_URL="${1:-http://localhost:8000}"

echo "=== MoneySpeaks Demo ==="
echo "Backend: $BASE_URL"
echo ""

# Health check
echo "Checking backend health..."
curl -s "$BASE_URL/health" | python -m json.tool
echo ""

# Demo 1: Real customer (calibrate — should be green)
echo "--- Demo 1: Real Customer (expect GREEN) ---"
curl -s -X POST "$BASE_URL/demo/real_customer" | python -m json.tool
echo ""
echo "Press Enter to continue..."
read

# Demo 2: Bank impersonation (wav2vec2 flags + urgency)
echo "--- Demo 2: Bank Impersonation (expect RED) ---"
curl -s -X POST "$BASE_URL/demo/bank_impersonation" | python -m json.tool
echo ""
echo "Press Enter to continue..."
read

# Demo 3: Grandparent scam (affective analysis)
echo "--- Demo 3: Grandparent Scam (expect AMBER→RED) ---"
curl -s -X POST "$BASE_URL/demo/grandparent_scam" | python -m json.tool
echo ""

echo "=== Demo Complete ==="
