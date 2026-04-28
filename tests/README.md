# RUNE-CI Test Suite

Tests for shared GitHub Actions, reusable workflows, and CI/CD logic.

## Directory Structure

- **`compliance/`**: Validates repository standards: PR body checks, license compliance, CVE policy enforcement, and ingress guards.
- **`logic/`**: Tests for internal CI logic: merge gate heuristics and workflow structure validation.

## Running Tests

Python tests use `pytest`, shell tests are run directly:

```bash
# Run compliance Python tests
python -m pytest tests/compliance/

# Run logic tests
python -m pytest tests/logic/
bash tests/logic/test_workflow_structure.sh
```
