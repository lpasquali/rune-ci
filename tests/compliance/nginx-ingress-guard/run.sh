#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RUNE Contributors
#
# tests/nginx-ingress-guard/run.sh — unit tests for actions/nginx-ingress-guard
#
# Runs the action's script against curated fixtures and asserts PASS/FAIL
# per rule. The action's inline bash (from action.yml) is extracted and
# executed directly; this avoids needing `act` or a full workflow runner.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
readonly REPO_ROOT
ACTION_FILE="${REPO_ROOT}/actions/nginx-ingress-guard/action.yml"
FIX_ROOT="${REPO_ROOT}/actions/nginx-ingress-guard/fixtures"

PASS_COUNT=0
FAIL_COUNT=0

extract_script() {
    # Extract the bash between "run: |" and end-of-step.
    python3 - "$ACTION_FILE" <<'PY'
import sys, yaml
with open(sys.argv[1]) as f:
    d = yaml.safe_load(f)
run = d["runs"]["steps"][0]["run"]
sys.stdout.write(run)
PY
}

run_guard() {
    # $1 = scan-path
    local scan_path="$1"
    local script
    script="$(extract_script)"
    (
        export SCAN_PATH="$scan_path"
        export EXTRA_EXEMPT_PATHS=""
        export EXTRA_EXEMPT_RULE1=""
        bash -c "$script"
    )
}

assert_pass() {
    local name="$1"
    local path="$2"
    if run_guard "$path" >/dev/null 2>&1; then
        echo "  PASS: $name"
        PASS_COUNT=$((PASS_COUNT+1))
    else
        echo "  FAIL: $name (expected PASS, guard FAILED)"
        FAIL_COUNT=$((FAIL_COUNT+1))
        run_guard "$path" 2>&1 | sed 's/^/    /' || true
    fi
}

assert_fail() {
    local name="$1"
    local path="$2"
    local expected_rule="$3"
    local output rc
    output="$(run_guard "$path" 2>&1)" && rc=0 || rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "  FAIL: $name (expected FAIL, guard PASSED)"
        FAIL_COUNT=$((FAIL_COUNT+1))
        return
    fi
    if echo "$output" | grep -q "$expected_rule"; then
        echo "  PASS: $name ($expected_rule triggered)"
        PASS_COUNT=$((PASS_COUNT+1))
    else
        echo "  FAIL: $name (expected $expected_rule, got:)"
        echo "$output" | sed 's/^/    /'
        FAIL_COUNT=$((FAIL_COUNT+1))
    fi
}

echo "=== nginx-ingress-guard unit tests ==="

echo "--- allowed tree passes ---"
assert_pass "allowed fixture tree passes" "${FIX_ROOT}/allowed"

echo "--- forbidden patterns fail with the right rule ---"
assert_fail "FROM nginx without pragma fails rule 1" \
    "${FIX_ROOT}/forbidden-rule1" "Rule 1"
assert_fail "nginx.ingress.kubernetes.io annotation fails rule 2" \
    "${FIX_ROOT}/forbidden-rule2" "Rule 2"
assert_fail "ingress-nginx chart dependency fails rule 3" \
    "${FIX_ROOT}/forbidden-rule3" "Rule 3"
assert_fail "hardcoded kubernetes.io/ingress.class: nginx fails rule 4" \
    "${FIX_ROOT}/forbidden-rule4" "Rule 4"

echo ""
echo "=== Results: ${PASS_COUNT} passed, ${FAIL_COUNT} failed ==="
[ "$FAIL_COUNT" -eq 0 ]
