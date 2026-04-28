# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the license-check composite action's blocklist logic.

The license-check action embeds a Python script that evaluates
pip-licenses JSON output against a configurable blocklist.
This test suite extracts and validates that logic with fixture scenarios:

- Passing build: all licenses allowed
- Blocked license: AGPL dependency detected
- GPL-2.0 variant blocked
- Allowed exceptions bypass blocklist
- Empty license data
- Case-insensitive matching
"""

import json
import os
import textwrap
from pathlib import Path
from typing import Any

import pytest


def _run_license_policy(
    rows: list[dict[str, Any]],
    blocked_licenses: str = "agpl,gplv3,gpl v3,gnu general public license v3,"
    "gnu affero general public license,gplv2,gpl v2,gpl-2.0,"
    "gnu general public license v2",
    allowed_exceptions: str = "",
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    """Replicate the license policy logic from actions/license-check/action.yml.

    Returns (blocked, allowed_hits) tuples.
    """
    disallowed_tokens = tuple(
        t.strip().lower() for t in blocked_licenses.split(",") if t.strip()
    )
    allowed_package_exceptions = {
        p.strip().lower() for p in allowed_exceptions.split(",") if p.strip()
    }

    blocked: list[tuple[str, str, str]] = []
    allowed_hits: list[tuple[str, str, str]] = []

    for row in rows:
        pkg = str(row.get("Name", "unknown"))
        lic = str(row.get("License", "")).lower()
        if any(token in lic for token in disallowed_tokens):
            entry = (pkg, row.get("Version", "unknown"), row.get("License", ""))
            if pkg.lower() in allowed_package_exceptions:
                allowed_hits.append(entry)
            else:
                blocked.append(entry)

    return blocked, allowed_hits


# ---------------------------------------------------------------------------
# Fixture: passing build — all licenses clean
# ---------------------------------------------------------------------------
class TestPassingBuild:
    def test_all_mit(self) -> None:
        rows = [
            {"Name": "requests", "Version": "2.31.0", "License": "Apache Software License"},
            {"Name": "click", "Version": "8.1.7", "License": "BSD License"},
            {"Name": "flask", "Version": "3.0.0", "License": "MIT License"},
        ]
        blocked, allowed = _run_license_policy(rows)
        assert blocked == []
        assert allowed == []

    def test_empty_input(self) -> None:
        blocked, allowed = _run_license_policy([])
        assert blocked == []
        assert allowed == []


# ---------------------------------------------------------------------------
# Fixture: blocked license — AGPL dependency
# ---------------------------------------------------------------------------
class TestBlockedLicense:
    def test_agpl_detected(self) -> None:
        rows = [
            {"Name": "good-pkg", "Version": "1.0", "License": "MIT"},
            {"Name": "bad-pkg", "Version": "2.0", "License": "GNU Affero General Public License v3"},
        ]
        blocked, _ = _run_license_policy(rows)
        assert len(blocked) == 1
        assert blocked[0][0] == "bad-pkg"

    def test_gplv3_detected(self) -> None:
        rows = [
            {"Name": "gpl-pkg", "Version": "1.0", "License": "GPLv3"},
        ]
        blocked, _ = _run_license_policy(rows)
        assert len(blocked) == 1

    def test_gpl_v2_detected(self) -> None:
        rows = [
            {"Name": "old-gpl-pkg", "Version": "1.0", "License": "GPL-2.0"},
        ]
        blocked, _ = _run_license_policy(rows)
        assert len(blocked) == 1

    def test_gnu_gpl_v2_long_name(self) -> None:
        rows = [
            {"Name": "gpl2-pkg", "Version": "1.0", "License": "GNU General Public License v2"},
        ]
        blocked, _ = _run_license_policy(rows)
        assert len(blocked) == 1

    def test_multiple_blocked(self) -> None:
        rows = [
            {"Name": "agpl-pkg", "Version": "1.0", "License": "AGPL-3.0"},
            {"Name": "gpl-pkg", "Version": "2.0", "License": "GPLv3"},
        ]
        blocked, _ = _run_license_policy(rows)
        assert len(blocked) == 2


# ---------------------------------------------------------------------------
# Fixture: allowed exceptions bypass blocklist
# ---------------------------------------------------------------------------
class TestAllowedExceptions:
    def test_exception_bypasses_block(self) -> None:
        rows = [
            {"Name": "special-pkg", "Version": "1.0", "License": "GNU Affero General Public License"},
        ]
        blocked, allowed = _run_license_policy(rows, allowed_exceptions="special-pkg")
        assert blocked == []
        assert len(allowed) == 1
        assert allowed[0][0] == "special-pkg"

    def test_exception_case_insensitive(self) -> None:
        rows = [
            {"Name": "Special-Pkg", "Version": "1.0", "License": "AGPL"},
        ]
        blocked, allowed = _run_license_policy(rows, allowed_exceptions="SPECIAL-PKG")
        assert blocked == []
        assert len(allowed) == 1

    def test_non_matching_exception_does_not_help(self) -> None:
        rows = [
            {"Name": "bad-pkg", "Version": "1.0", "License": "AGPL"},
        ]
        blocked, _ = _run_license_policy(rows, allowed_exceptions="other-pkg")
        assert len(blocked) == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_missing_license_field(self) -> None:
        rows = [{"Name": "no-license", "Version": "1.0"}]
        blocked, _ = _run_license_policy(rows)
        assert blocked == []

    def test_empty_license_string(self) -> None:
        rows = [{"Name": "empty-lic", "Version": "1.0", "License": ""}]
        blocked, _ = _run_license_policy(rows)
        assert blocked == []

    def test_case_insensitive_license_match(self) -> None:
        rows = [{"Name": "mixed-case", "Version": "1.0", "License": "AGPL-3.0-only"}]
        blocked, _ = _run_license_policy(rows)
        assert len(blocked) == 1

    def test_custom_blocklist(self) -> None:
        rows = [{"Name": "pkg", "Version": "1.0", "License": "Proprietary"}]
        blocked, _ = _run_license_policy(rows, blocked_licenses="proprietary")
        assert len(blocked) == 1

    def test_empty_blocklist_allows_everything(self) -> None:
        rows = [{"Name": "agpl-pkg", "Version": "1.0", "License": "AGPL"}]
        blocked, _ = _run_license_policy(rows, blocked_licenses="")
        assert blocked == []
