# SPDX-License-Identifier: Apache-2.0
"""Unit tests for PR body compliance validation logic.

The pr-compliance reusable workflow (and quality-gates.yml) use JavaScript
regex patterns to validate PR body structure. This test suite validates those
same patterns in Python to ensure correctness of the validation rules.

Fixture scenarios:
- Valid PR body: passes all checks
- Malformed PR body: missing issue ref, DoD level, sections
- Edge cases: empty body, partial matches
"""

import re
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Replicate the PR body compliance regex checks from pr-compliance.yml
# ---------------------------------------------------------------------------
ISSUE_REF_PATTERN = re.compile(r"[Cc]loses?\s+#\d+|[Ff]ixes?\s+#\d+|[Rr]esolves?\s+#\d+")
DOD_LEVEL_PATTERN = re.compile(r"\[x\]\s+\*\*Level\s+[123]")
ACCEPTANCE_SECTION = re.compile(r"## Acceptance Criteria Evidence")
AUDIT_SECTION = re.compile(r"## Audit Checks")
AUDIT_RESULTS = re.compile(r"PASS|FAIL|No triggers fired")
AUDIT_FAIL = re.compile(r"\|\s*FAIL\s*\|")
BREAKING_SECTION = re.compile(r"## Breaking Changes")


def validate_pr_body(body: str) -> list[str]:
    """Replicate PR body validation logic. Returns list of error strings."""
    errors: list[str] = []
    if not ISSUE_REF_PATTERN.search(body):
        errors.append("PR must reference an issue (Closes #NNN, Fixes #NNN, or Resolves #NNN)")
    if not DOD_LEVEL_PATTERN.search(body):
        errors.append("PR must check exactly one DoD level")
    if not ACCEPTANCE_SECTION.search(body):
        errors.append('PR must include "## Acceptance Criteria Evidence" section')
    if not AUDIT_SECTION.search(body):
        errors.append('PR must include "## Audit Checks" section')
    if AUDIT_SECTION.search(body) and not AUDIT_RESULTS.search(body):
        errors.append('Audit Checks section must report PASS/FAIL results or state "No triggers fired"')
    if AUDIT_FAIL.search(body):
        errors.append("PR has FAIL audit check results -- resolve before merging")
    if not BREAKING_SECTION.search(body):
        errors.append('PR must include "## Breaking Changes" section')
    return errors


# A valid PR body that passes all checks
VALID_PR_BODY = """## Summary
- Added integration tests for rune-ci workflows

Closes #157

## DoD Level
- [ ] **Level 1** -- Full Validation
- [x] **Level 2** -- Test Infrastructure
- [ ] **Level 3** -- Documentation Validation

## Acceptance Criteria Evidence
- [x] Test workflow calling each reusable workflow with test inputs
- [x] Fixture scenarios cover all required cases

## Audit Checks
No triggers fired.

## Breaking Changes
None.

## Test plan
- [x] All tests pass locally
"""


# ---------------------------------------------------------------------------
# Fixture: valid PR body
# ---------------------------------------------------------------------------
class TestValidPRBody:
    def test_fully_valid(self) -> None:
        errors = validate_pr_body(VALID_PR_BODY)
        assert errors == []

    def test_closes_variant(self) -> None:
        body = VALID_PR_BODY.replace("Closes #157", "Close #42")
        errors = validate_pr_body(body)
        assert errors == []

    def test_fixes_variant(self) -> None:
        body = VALID_PR_BODY.replace("Closes #157", "Fixes #42")
        errors = validate_pr_body(body)
        assert errors == []

    def test_resolves_variant(self) -> None:
        body = VALID_PR_BODY.replace("Closes #157", "Resolves #42")
        errors = validate_pr_body(body)
        assert errors == []

    def test_level_1(self) -> None:
        body = VALID_PR_BODY.replace(
            "- [x] **Level 2**", "- [ ] **Level 2**"
        ).replace("- [ ] **Level 1**", "- [x] **Level 1**")
        errors = validate_pr_body(body)
        assert errors == []

    def test_level_3(self) -> None:
        body = VALID_PR_BODY.replace(
            "- [x] **Level 2**", "- [ ] **Level 2**"
        ).replace("- [ ] **Level 3**", "- [x] **Level 3**")
        errors = validate_pr_body(body)
        assert errors == []

    def test_audit_with_pass_result(self) -> None:
        body = VALID_PR_BODY.replace(
            "No triggers fired.",
            "| Check | Result |\n| `cyber check:supply-chain` | PASS |",
        )
        errors = validate_pr_body(body)
        assert errors == []


# ---------------------------------------------------------------------------
# Fixture: malformed PR body
# ---------------------------------------------------------------------------
class TestMalformedPRBody:
    def test_empty_body(self) -> None:
        errors = validate_pr_body("")
        assert len(errors) >= 5  # All sections missing

    def test_missing_issue_ref(self) -> None:
        body = VALID_PR_BODY.replace("Closes #157", "Related to issue 157")
        errors = validate_pr_body(body)
        assert any("reference an issue" in e for e in errors)

    def test_missing_dod_level(self) -> None:
        body = VALID_PR_BODY.replace("[x] **Level 2**", "[ ] **Level 2**")
        errors = validate_pr_body(body)
        assert any("DoD level" in e for e in errors)

    def test_missing_acceptance_criteria(self) -> None:
        body = VALID_PR_BODY.replace("## Acceptance Criteria Evidence", "## Evidence")
        errors = validate_pr_body(body)
        assert any("Acceptance Criteria" in e for e in errors)

    def test_missing_audit_checks(self) -> None:
        body = VALID_PR_BODY.replace("## Audit Checks", "## Audits")
        errors = validate_pr_body(body)
        assert any("Audit Checks" in e for e in errors)

    def test_missing_breaking_changes(self) -> None:
        body = VALID_PR_BODY.replace("## Breaking Changes", "## Changes")
        errors = validate_pr_body(body)
        assert any("Breaking Changes" in e for e in errors)

    def test_fail_audit_result_blocks(self) -> None:
        body = VALID_PR_BODY.replace(
            "No triggers fired.",
            "| Check | Result |\n| `cyber check:supply-chain` | FAIL |",
        )
        errors = validate_pr_body(body)
        assert any("FAIL audit" in e for e in errors)

    def test_audit_section_present_but_no_results(self) -> None:
        body = VALID_PR_BODY.replace("No triggers fired.", "TBD")
        errors = validate_pr_body(body)
        assert any("report PASS/FAIL" in e for e in errors)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_multiple_issue_refs(self) -> None:
        body = VALID_PR_BODY.replace("Closes #157", "Closes #157\nFixes #42")
        errors = validate_pr_body(body)
        assert errors == []

    def test_cross_repo_issue_ref_needs_local_ref(self) -> None:
        """Cross-repo refs like 'Closes lpasquali/rune-docs#157' do NOT match
        the regex (it expects whitespace before #NNN). A local issue ref is
        also needed for compliance."""
        body = VALID_PR_BODY.replace("Closes #157", "Closes lpasquali/rune-docs#157")
        errors = validate_pr_body(body)
        assert any("reference an issue" in e for e in errors)

    def test_cross_repo_with_local_ref(self) -> None:
        """Cross-repo ref paired with a local ref passes."""
        body = VALID_PR_BODY.replace(
            "Closes #157", "Closes lpasquali/rune-docs#157\nCloses #157"
        )
        errors = validate_pr_body(body)
        assert errors == []

    def test_case_sensitivity_closes(self) -> None:
        body = VALID_PR_BODY.replace("Closes #157", "closes #157")
        errors = validate_pr_body(body)
        assert errors == []
