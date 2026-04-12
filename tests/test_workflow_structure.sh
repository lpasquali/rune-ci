#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Integration test: validate all workflow YAML files and composite actions.
#
# Checks:
#   1. All workflow YAMLs are valid YAML (python yaml.safe_load)
#   2. All reusable workflows have 'on: workflow_call:' trigger
#   3. All composite actions have 'runs: using: composite'
#   4. All composite actions document their required inputs
#   5. All workflow files reference SHA-pinned actions
#   6. No inline scripts exceed the 200-line safety limit
#   9. SPDX headers on workflows, actions, scripts, docker/*.Dockerfile
#  10. docker/rune-ui-slim.Dockerfile is multi-stage (canonical UI image)
#
# Usage:
#   ./tests/test_workflow_structure.sh
#
# Exit code 0 on success, 1 on any failure.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKFLOWS_DIR="${REPO_ROOT}/.github/workflows"
ACTIONS_DIR="${REPO_ROOT}/actions"

PASS=0
FAIL=0
ERRORS=""

pass() {
  PASS=$((PASS + 1))
  echo "  PASS: $1"
}

fail() {
  FAIL=$((FAIL + 1))
  ERRORS="${ERRORS}\n  FAIL: $1"
  echo "  FAIL: $1"
}

# -----------------------------------------------------------------------
# Test 1: All workflow YAML files are syntactically valid
# -----------------------------------------------------------------------
echo "=== Test 1: YAML syntax validation ==="
for f in "${WORKFLOWS_DIR}"/*.yml; do
  name="$(basename "$f")"
  if python3 -c "
import yaml, sys
with open('$f') as fh:
    yaml.safe_load(fh)
" 2>/dev/null; then
    pass "valid YAML: ${name}"
  else
    fail "invalid YAML: ${name}"
  fi
done

# -----------------------------------------------------------------------
# Test 2: Reusable workflows declare workflow_call trigger
# -----------------------------------------------------------------------
echo ""
echo "=== Test 2: Reusable workflow trigger validation ==="
REUSABLE_WORKFLOWS=(
  "codeql-callable.yml"
  "merge-gate-from-needs.yml"
  "security-scan.yml"
  "pr-compliance.yml"
  "python-quality.yml"
  "go-quality.yml"
  "container-build.yml"
  "shell-quality.yml"
  "docs-quality.yml"
  "helm-quality.yml"
  "helm-release.yml"
  "release.yml"
)
for wf in "${REUSABLE_WORKFLOWS[@]}"; do
  f="${WORKFLOWS_DIR}/${wf}"
  if [ ! -f "$f" ]; then
    fail "missing reusable workflow: ${wf}"
    continue
  fi
  if grep -q "workflow_call" "$f"; then
    pass "has workflow_call: ${wf}"
  else
    fail "missing workflow_call trigger: ${wf}"
  fi
done

# -----------------------------------------------------------------------
# Test 3: Composite actions have correct structure
# -----------------------------------------------------------------------
echo ""
echo "=== Test 3: Composite action structure ==="
for action_dir in "${ACTIONS_DIR}"/*/; do
  action_name="$(basename "$action_dir")"
  action_file="${action_dir}action.yml"
  if [ ! -f "$action_file" ]; then
    fail "missing action.yml in: ${action_name}/"
    continue
  fi
  if grep -q 'using:.*"composite"' "$action_file" || grep -q "using:.*'composite'" "$action_file" || grep -q "using: \"composite\"" "$action_file" || grep -q 'using: composite' "$action_file"; then
    pass "composite action: ${action_name}"
  else
    fail "not a composite action: ${action_name}"
  fi
done

# -----------------------------------------------------------------------
# Test 4: Composite actions document required inputs
# -----------------------------------------------------------------------
echo ""
echo "=== Test 4: Composite action inputs documented ==="
for action_dir in "${ACTIONS_DIR}"/*/; do
  action_name="$(basename "$action_dir")"
  action_file="${action_dir}action.yml"
  [ ! -f "$action_file" ] && continue

  # Count required inputs
  required_count=$(python3 -c "
import yaml, sys
with open('$action_file') as fh:
    data = yaml.safe_load(fh)
inputs = data.get('inputs', {}) or {}
required = [k for k, v in inputs.items() if v.get('required')]
print(len(required))
for r in required:
    desc = inputs[r].get('description', '')
    if not desc.strip():
        print(f'MISSING_DESC:{r}', file=sys.stderr)
        sys.exit(1)
" 2>&1)

  if [ $? -eq 0 ]; then
    pass "inputs documented: ${action_name} (${required_count} required)"
  else
    fail "undocumented required inputs: ${action_name}"
  fi
done

# -----------------------------------------------------------------------
# Test 5: All uses: references are SHA-pinned (SLSA L3 compliance)
# -----------------------------------------------------------------------
echo ""
echo "=== Test 5: Action SHA pinning (SLSA L3) ==="
for f in "${WORKFLOWS_DIR}"/*.yml "${ACTIONS_DIR}"/*/action.yml; do
  [ ! -f "$f" ] && continue
  name="$(basename "$(dirname "$f")")/$(basename "$f")"

  # Extract 'uses:' lines, skip local actions (./), skip workflow_call refs
  unpinned=$(grep -n '^\s*uses:' "$f" \
    | grep -v '^\s*#' \
    | grep -v 'uses: \./' \
    | grep -v 'lpasquali/rune-ci/' \
    | grep -v '@[0-9a-f]\{40\}' \
    | grep -v '@[0-9a-f]\{7\}' \
    || true)

  if [ -z "$unpinned" ]; then
    pass "SHA-pinned: ${name}"
  else
    fail "unpinned actions in ${name}: $(echo "$unpinned" | head -3)"
  fi
done

# -----------------------------------------------------------------------
# Test 6: No excessively long inline scripts
# -----------------------------------------------------------------------
echo ""
echo "=== Test 6: Inline script length check (<200 lines) ==="
for f in "${WORKFLOWS_DIR}"/*.yml; do
  name="$(basename "$f")"

  # Use python to extract run: blocks and check their line counts
  long_scripts=$(python3 -c "
import yaml
with open('$f') as fh:
    data = yaml.safe_load(fh)
jobs = data.get('jobs', {}) or {}
for jname, jdata in jobs.items():
    for step in (jdata.get('steps') or []):
        run_block = step.get('run', '')
        lines = run_block.count('\n') + 1
        if lines > 200:
            print(f'{jname}/{step.get(\"name\", \"unnamed\")}: {lines} lines')
" 2>/dev/null || true)

  if [ -z "$long_scripts" ]; then
    pass "no long scripts: ${name}"
  else
    fail "long inline scripts in ${name}: ${long_scripts}"
  fi
done

# -----------------------------------------------------------------------
# Test 7: quality-gates.yml has a merge-gate job
# -----------------------------------------------------------------------
echo ""
echo "=== Test 7: Merge gate job exists ==="
QG="${WORKFLOWS_DIR}/quality-gates.yml"
if python3 -c "
import yaml
with open('$QG') as fh:
    data = yaml.safe_load(fh)
jobs = data.get('jobs', {})
assert 'merge-gate' in jobs, 'merge-gate job missing'
" 2>/dev/null; then
  pass "merge-gate job in quality-gates.yml"
else
  fail "merge-gate job missing in quality-gates.yml"
fi

# -----------------------------------------------------------------------
# Test 8: All reusable workflows have permissions declared
# -----------------------------------------------------------------------
echo ""
echo "=== Test 8: Permissions declared ==="
for wf in "${REUSABLE_WORKFLOWS[@]}"; do
  f="${WORKFLOWS_DIR}/${wf}"
  [ ! -f "$f" ] && continue
  if grep -q "^permissions:" "$f"; then
    pass "permissions declared: ${wf}"
  else
    fail "missing permissions block: ${wf}"
  fi
done

# -----------------------------------------------------------------------
# Test 9: SPDX license headers present
# -----------------------------------------------------------------------
echo ""
echo "=== Test 9: SPDX license headers ==="
for f in "${WORKFLOWS_DIR}"/*.yml "${ACTIONS_DIR}"/*/action.yml "${REPO_ROOT}"/scripts/*.py "${REPO_ROOT}"/docker/*.Dockerfile; do
  [ ! -f "$f" ] && continue
  name="$(basename "$f")"
  if head -2 "$f" | grep -q "SPDX-License-Identifier"; then
    pass "SPDX header: ${name}"
  else
    fail "missing SPDX header: ${name}"
  fi
done

# -----------------------------------------------------------------------
# Test 10: Canonical docker/rune-ui-slim.Dockerfile is multi-stage
# -----------------------------------------------------------------------
echo ""
echo "=== Test 10: rune-ui canonical Dockerfile (multi-stage) ==="
REF="${REPO_ROOT}/docker/rune-ui-slim.Dockerfile"
if [ ! -f "$REF" ]; then
  fail "missing ${REF}"
elif python3 -c "
import pathlib, re
p = pathlib.Path('$REF')
t = p.read_text()
from_count = len(re.findall(r'^FROM ', t, re.MULTILINE))
assert from_count >= 2, f'expected >=2 FROM stages, got {from_count}'
" 2>/dev/null; then
  pass "docker/rune-ui-slim.Dockerfile has builder + final stages"
else
  fail "docker/rune-ui-slim.Dockerfile must be multi-stage (>=2 FROM lines)"
fi

# -----------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------
echo ""
echo "========================================"
echo "  PASSED: ${PASS}"
echo "  FAILED: ${FAIL}"
if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "  Failures:"
  echo -e "$ERRORS"
  echo ""
  exit 1
fi
echo "========================================"
echo "All tests passed."
exit 0
