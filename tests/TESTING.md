# Integration Test Suite for rune-ci

This directory contains the integration test suite that validates rune-ci's
reusable workflows, composite actions, and merge gate logic.

## Running Tests

### Python unit tests (merge gate, license check, CVE policy, PR compliance)

```bash
cd ~/Devel/rune-ci
pip install pytest pyyaml
pytest tests/ -v
```

### Workflow structure validation (YAML parsing, SHA pinning, permissions)

```bash
cd ~/Devel/rune-ci
pip install pyyaml
./tests/test_workflow_structure.sh
```

### All tests together

```bash
cd ~/Devel/rune-ci
pip install pytest pyyaml
pytest tests/ -v && ./tests/test_workflow_structure.sh
```

## CI Integration

Tests run automatically on every PR to `rune-ci` via the `integration-tests`
job in `.github/workflows/quality-gates.yml`. Results feed into the merge gate
and block merge on failure.

## Test Coverage Map

| Test file | What it validates |
|---|---|
| `test_merge_gate.py` | `scripts/merge_gate.py` — all pass/fail/skip/cancel combos |
| `test_license_check.py` | License blocklist logic from `actions/license-check/action.yml` |
| `test_cve_policy.py` | CVE threshold/VEX suppression from `actions/sbom-scan/action.yml` |
| `test_pr_compliance.py` | PR body regex validation from `pr-compliance.yml` |
| `test_workflow_structure.sh` | YAML validity, `workflow_call` triggers, SHA pinning, permissions, SPDX headers |

## Fixture Scenarios

Each test file covers these standard scenarios:

1. **Passing build** — all inputs are clean, validation passes
2. **Failing coverage** — a required job reports failure
3. **Blocked license** — AGPL/GPL dependency detected in license scan
4. **CVSS threshold breach** — fixable CVE above the 7.0 threshold
5. **Malformed PR body** — missing issue reference, DoD level, or required sections

## Adding New Test Scenarios

### Adding a new fixture to an existing test file

1. Open the relevant `test_*.py` file.
2. Add a new test class or method following the existing pattern:
   ```python
   class TestNewScenario:
       def test_specific_case(self) -> None:
           # Arrange: set up inputs
           # Act: call the function under test
           # Assert: verify expected outcome
           ...
   ```
3. Run `pytest tests/ -v` to verify.

### Adding tests for a new reusable workflow

1. Create `tests/test_<workflow_name>.py`.
2. Extract the testable logic (Python script blocks, regex patterns, or
   threshold calculations) from the workflow YAML into a helper function
   in the test file.
3. Write tests covering the standard fixture scenarios listed above.
4. If the workflow introduces a new composite action, add structure
   validation to `test_workflow_structure.sh` (it auto-discovers new
   actions in `actions/`).

### Adding a new composite action

The `test_workflow_structure.sh` script automatically validates:
- The action has an `action.yml` with `using: composite`
- All required inputs have descriptions
- All `uses:` references are SHA-pinned
- SPDX license headers are present

No manual test updates are needed for structural checks. If the action
contains embedded Python logic, extract and test it as described above.

### Adding a new structural check

1. Open `tests/test_workflow_structure.sh`.
2. Add a new numbered test section following the existing pattern:
   ```bash
   echo ""
   echo "=== Test N: Description ==="
   # ... validation logic ...
   if [ condition ]; then
     pass "description"
   else
     fail "description"
   fi
   ```
3. Run `./tests/test_workflow_structure.sh` to verify.
