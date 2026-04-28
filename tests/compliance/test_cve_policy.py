# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the SBOM scan composite action's CVE policy logic.

The sbom-scan action embeds a Python script that evaluates Grype and Trivy
JSON output against a configurable CVSS threshold and VEX suppression file.
This test suite validates that logic with fixture scenarios:

- Passing scan: no findings
- CVSS threshold breach: fixable vuln above threshold blocked
- Unfixable vulns: warned but not blocked
- VEX suppression: known-accepted CVEs excluded from block
- Mixed scanner output (Grype + Trivy formats)
"""

import json
from pathlib import Path
from typing import Any

import pytest


def _safe_float(v: Any) -> float:
    """Replicate safe_float from sbom-scan action."""
    try:
        return float(v or 0)
    except (ValueError, TypeError):
        return 0.0


def _evaluate_cve_policy(
    scan_files: dict[str, dict[str, Any]],
    cvss_threshold: float = 7.0,
    vex_statements: list[dict[str, Any]] | None = None,
) -> tuple[list[tuple[str, float, str, bool]], list[tuple[str, float, str, bool]]]:
    """Replicate the CVE policy logic from actions/sbom-scan/action.yml.

    Args:
        scan_files: dict of filename -> parsed JSON content
        cvss_threshold: CVSS score threshold for blocking
        vex_statements: list of VEX statement dicts for suppression

    Returns:
        (blocked, warned) tuples of (cve_id, score, source_file, fixable)
    """
    vendor_constrained: set[str] = set()
    if vex_statements:
        for stmt in vex_statements:
            vuln_name = (stmt.get("vulnerability") or {}).get("name", "")
            if vuln_name and stmt.get("status") in {"affected", "not_affected"}:
                vendor_constrained.add(vuln_name)

    findings: list[tuple[str, float, str, bool]] = []

    for filename, data in scan_files.items():
        # Grype format
        if "matches" in data:
            for m in data.get("matches", []):
                vuln = m.get("vulnerability", {})
                fix_state = (vuln.get("fix") or {}).get("state", "unknown")
                fixable = fix_state == "fixed"
                scores: list[float] = []
                for c in vuln.get("cvss", []) or []:
                    metrics = c.get("metrics", {})
                    for k in ("baseScore", "base_score"):
                        scores.append(_safe_float(metrics.get(k)))
                findings.append(
                    (vuln.get("id", "UNKNOWN"), max(scores) if scores else 0.0, filename, fixable)
                )
        # Trivy format
        elif "Results" in data:
            for r in data.get("Results", []) or []:
                for v in r.get("Vulnerabilities", []) or []:
                    score = 0.0
                    for vendor in ("nvd", "redhat", "ghsa"):
                        score = max(
                            score,
                            _safe_float((v.get("CVSS") or {}).get(vendor, {}).get("V3Score")),
                        )
                    fixable = bool((v.get("FixedVersion") or "").strip())
                    findings.append(
                        (v.get("VulnerabilityID", "UNKNOWN"), score, filename, fixable)
                    )

    blocked = [
        x
        for x in findings
        if x[1] >= cvss_threshold and x[3] and x[0] not in vendor_constrained
    ]
    warned = [
        x
        for x in findings
        if x[1] >= cvss_threshold and (not x[3] or x[0] in vendor_constrained)
    ]

    return blocked, warned


# ---------------------------------------------------------------------------
# Fixture: passing scan — no vulnerabilities
# ---------------------------------------------------------------------------
class TestPassingScan:
    def test_no_findings(self) -> None:
        grype_data = {"matches": []}
        blocked, warned = _evaluate_cve_policy({"grype.json": grype_data})
        assert blocked == []
        assert warned == []

    def test_empty_trivy(self) -> None:
        trivy_data = {"Results": []}
        blocked, warned = _evaluate_cve_policy({"trivy.json": trivy_data})
        assert blocked == []
        assert warned == []

    def test_low_severity_not_blocked(self) -> None:
        grype_data = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-2024-0001",
                        "fix": {"state": "fixed"},
                        "cvss": [{"metrics": {"baseScore": 3.5}}],
                    }
                }
            ]
        }
        blocked, warned = _evaluate_cve_policy({"grype.json": grype_data})
        assert blocked == []
        assert warned == []


# ---------------------------------------------------------------------------
# Fixture: CVSS threshold breach — fixable vuln above threshold
# ---------------------------------------------------------------------------
class TestCVSSThresholdBreach:
    def test_high_cvss_fixable_blocked(self) -> None:
        grype_data = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-2024-9999",
                        "fix": {"state": "fixed"},
                        "cvss": [{"metrics": {"baseScore": 9.8}}],
                    }
                }
            ]
        }
        blocked, _ = _evaluate_cve_policy({"grype.json": grype_data})
        assert len(blocked) == 1
        assert blocked[0][0] == "CVE-2024-9999"
        assert blocked[0][1] == 9.8

    def test_exactly_at_threshold_blocked(self) -> None:
        grype_data = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-2024-7000",
                        "fix": {"state": "fixed"},
                        "cvss": [{"metrics": {"baseScore": 7.0}}],
                    }
                }
            ]
        }
        blocked, _ = _evaluate_cve_policy({"grype.json": grype_data})
        assert len(blocked) == 1

    def test_trivy_high_cvss_blocked(self) -> None:
        trivy_data = {
            "Results": [
                {
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-8888",
                            "CVSS": {"nvd": {"V3Score": 8.5}},
                            "FixedVersion": "2.0.0",
                        }
                    ]
                }
            ]
        }
        blocked, _ = _evaluate_cve_policy({"trivy.json": trivy_data})
        assert len(blocked) == 1
        assert blocked[0][0] == "CVE-2024-8888"

    def test_custom_threshold(self) -> None:
        grype_data = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-2024-5555",
                        "fix": {"state": "fixed"},
                        "cvss": [{"metrics": {"baseScore": 5.5}}],
                    }
                }
            ]
        }
        # With lower threshold, this gets blocked
        blocked, _ = _evaluate_cve_policy({"grype.json": grype_data}, cvss_threshold=5.0)
        assert len(blocked) == 1

        # With default threshold, this passes
        blocked, _ = _evaluate_cve_policy({"grype.json": grype_data}, cvss_threshold=7.0)
        assert blocked == []


# ---------------------------------------------------------------------------
# Fixture: unfixable vulns — warned but not blocked
# ---------------------------------------------------------------------------
class TestUnfixableVulns:
    def test_high_cvss_unfixable_warned(self) -> None:
        grype_data = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-2024-0002",
                        "fix": {"state": "not-fixed"},
                        "cvss": [{"metrics": {"baseScore": 9.0}}],
                    }
                }
            ]
        }
        blocked, warned = _evaluate_cve_policy({"grype.json": grype_data})
        assert blocked == []
        assert len(warned) == 1

    def test_trivy_no_fixed_version_warned(self) -> None:
        trivy_data = {
            "Results": [
                {
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-0003",
                            "CVSS": {"nvd": {"V3Score": 8.0}},
                            "FixedVersion": "",
                        }
                    ]
                }
            ]
        }
        blocked, warned = _evaluate_cve_policy({"trivy.json": trivy_data})
        assert blocked == []
        assert len(warned) == 1


# ---------------------------------------------------------------------------
# Fixture: VEX suppression
# ---------------------------------------------------------------------------
class TestVEXSuppression:
    def test_vex_not_affected_suppresses_block(self) -> None:
        grype_data = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-2024-1111",
                        "fix": {"state": "fixed"},
                        "cvss": [{"metrics": {"baseScore": 9.8}}],
                    }
                }
            ]
        }
        vex = [
            {
                "vulnerability": {"name": "CVE-2024-1111"},
                "status": "not_affected",
            }
        ]
        blocked, warned = _evaluate_cve_policy(
            {"grype.json": grype_data}, vex_statements=vex
        )
        assert blocked == []
        assert len(warned) == 1  # Still warned even if VEX-suppressed

    def test_vex_affected_also_suppresses(self) -> None:
        """VEX 'affected' status also moves from blocked to warned."""
        grype_data = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-2024-2222",
                        "fix": {"state": "fixed"},
                        "cvss": [{"metrics": {"baseScore": 8.0}}],
                    }
                }
            ]
        }
        vex = [
            {
                "vulnerability": {"name": "CVE-2024-2222"},
                "status": "affected",
            }
        ]
        blocked, warned = _evaluate_cve_policy(
            {"grype.json": grype_data}, vex_statements=vex
        )
        assert blocked == []
        assert len(warned) == 1

    def test_unrelated_vex_does_not_suppress(self) -> None:
        grype_data = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-2024-3333",
                        "fix": {"state": "fixed"},
                        "cvss": [{"metrics": {"baseScore": 9.0}}],
                    }
                }
            ]
        }
        vex = [
            {
                "vulnerability": {"name": "CVE-2024-OTHER"},
                "status": "not_affected",
            }
        ]
        blocked, _ = _evaluate_cve_policy(
            {"grype.json": grype_data}, vex_statements=vex
        )
        assert len(blocked) == 1


# ---------------------------------------------------------------------------
# Mixed scanner output
# ---------------------------------------------------------------------------
class TestMixedScanners:
    def test_grype_and_trivy_combined(self) -> None:
        grype_data = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-2024-GRYPE",
                        "fix": {"state": "fixed"},
                        "cvss": [{"metrics": {"baseScore": 8.0}}],
                    }
                }
            ]
        }
        trivy_data = {
            "Results": [
                {
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-TRIVY",
                            "CVSS": {"nvd": {"V3Score": 9.0}},
                            "FixedVersion": "3.0.0",
                        }
                    ]
                }
            ]
        }
        blocked, _ = _evaluate_cve_policy(
            {"grype.json": grype_data, "trivy.json": trivy_data}
        )
        assert len(blocked) == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
class TestCVEEdgeCases:
    def test_missing_cvss_scores(self) -> None:
        grype_data = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-2024-NOCVSS",
                        "fix": {"state": "fixed"},
                        "cvss": [],
                    }
                }
            ]
        }
        blocked, _ = _evaluate_cve_policy({"grype.json": grype_data})
        assert blocked == []

    def test_null_cvss_field(self) -> None:
        grype_data = {
            "matches": [
                {
                    "vulnerability": {
                        "id": "CVE-2024-NULL",
                        "fix": {"state": "fixed"},
                        "cvss": None,
                    }
                }
            ]
        }
        blocked, _ = _evaluate_cve_policy({"grype.json": grype_data})
        assert blocked == []

    def test_safe_float_edge_cases(self) -> None:
        assert _safe_float(None) == 0.0
        assert _safe_float("") == 0.0
        assert _safe_float("not-a-number") == 0.0
        assert _safe_float(7.5) == 7.5
        assert _safe_float("9.8") == 9.8
