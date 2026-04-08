# SPDX-License-Identifier: Apache-2.0
"""Unit tests for scripts/merge_gate.py.

Validates merge gate logic with all fixture scenarios:
- All jobs pass
- Single job failure
- Multiple job failures
- Mix of success and skipped
- Unknown/cancelled statuses
- Empty results
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

# Load merge_gate module from scripts/ (not on sys.path by default)
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
_MERGE_GATE = _SCRIPTS_DIR / "merge_gate.py"

spec = importlib.util.spec_from_file_location("merge_gate", _MERGE_GATE)
assert spec is not None and spec.loader is not None
merge_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merge_gate)

evaluate = merge_gate.evaluate


# ---------------------------------------------------------------------------
# Fixture: passing build — all jobs succeed
# ---------------------------------------------------------------------------
class TestAllPass:
    def test_all_success(self) -> None:
        results = {
            "lint-workflows": "success",
            "lint-yaml": "success",
            "security-secrets": "success",
            "pr-body-check": "success",
        }
        assert evaluate(results) is True

    def test_all_skipped(self) -> None:
        results = {
            "lint-workflows": "skipped",
            "lint-yaml": "skipped",
        }
        assert evaluate(results) is True

    def test_mixed_success_and_skipped(self) -> None:
        results = {
            "lint-workflows": "success",
            "lint-yaml": "skipped",
            "security-secrets": "success",
            "pr-body-check": "skipped",
        }
        assert evaluate(results) is True


# ---------------------------------------------------------------------------
# Fixture: failing coverage — a coverage job fails
# ---------------------------------------------------------------------------
class TestFailingCoverage:
    def test_single_failure(self) -> None:
        results = {
            "coverage": "failure",
            "lint-workflows": "success",
            "security-secrets": "success",
        }
        assert evaluate(results) is False

    def test_coverage_failure_blocks_merge(self, capsys: pytest.CaptureFixture[str]) -> None:
        results = {
            "coverage": "failure",
            "linting": "success",
        }
        result = evaluate(results)
        captured = capsys.readouterr()
        assert result is False
        assert "FAIL" in captured.out
        assert "coverage" in captured.out


# ---------------------------------------------------------------------------
# Fixture: blocked license — license check fails
# ---------------------------------------------------------------------------
class TestBlockedLicense:
    def test_license_failure(self) -> None:
        results = {
            "license-check": "failure",
            "coverage": "success",
            "linting": "success",
        }
        assert evaluate(results) is False


# ---------------------------------------------------------------------------
# Fixture: CVSS threshold breach — security scan fails
# ---------------------------------------------------------------------------
class TestCVSSThresholdBreach:
    def test_security_scan_failure(self) -> None:
        results = {
            "security-sbom": "failure",
            "security-secrets": "success",
            "coverage": "success",
        }
        assert evaluate(results) is False


# ---------------------------------------------------------------------------
# Fixture: malformed PR body — pr-body-check fails
# ---------------------------------------------------------------------------
class TestMalformedPRBody:
    def test_pr_body_check_failure(self) -> None:
        results = {
            "pr-body-check": "failure",
            "lint-workflows": "success",
            "lint-yaml": "success",
        }
        assert evaluate(results) is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_empty_results(self) -> None:
        assert evaluate({}) is True

    def test_cancelled_job(self) -> None:
        results = {"coverage": "cancelled"}
        assert evaluate(results) is False

    def test_unknown_status(self) -> None:
        results = {"coverage": "unknown"}
        assert evaluate(results) is False

    def test_multiple_failures(self) -> None:
        results = {
            "coverage": "failure",
            "linting": "failure",
            "security-secrets": "failure",
        }
        assert evaluate(results) is False

    def test_output_format(self, capsys: pytest.CaptureFixture[str]) -> None:
        results = {
            "job-a": "success",
            "job-b": "failure",
        }
        evaluate(results)
        captured = capsys.readouterr()
        assert "OK:   job-a = success" in captured.out
        assert "FAIL: job-b = failure" in captured.out


# ---------------------------------------------------------------------------
# CLI integration tests — run merge_gate.py as a subprocess
# ---------------------------------------------------------------------------
class TestCLI:
    def test_cli_success(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_MERGE_GATE), '{"a": "success", "b": "skipped"}'],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_cli_failure(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_MERGE_GATE), '{"a": "success", "b": "failure"}'],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1

    def test_cli_bad_usage(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_MERGE_GATE)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2

    def test_cli_invalid_json(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_MERGE_GATE), "not-json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
