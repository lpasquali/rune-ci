# Contributing to rune-ci

## Before You Start

Read the RUNE engineering standards in [rune-docs](https://github.com/lpasquali/rune-docs):

1. [SYSTEM_PROMPT.md](https://github.com/lpasquali/rune-docs/blob/main/docs/context/SYSTEM_PROMPT.md) — Architecture, constraints, SOP
2. [CODING_STANDARDS.md](https://github.com/lpasquali/rune-docs/blob/main/docs/context/CODING_STANDARDS.md) — Style, coverage floors

## Workflow Changes

Changes to reusable workflows or composite actions affect **all 7 Rune repositories**. Every PR must:

1. Pass `actionlint` and `yamllint` (enforced by CI).
2. Include a risk assessment: which repos are affected and how.
3. Follow the PR template (DoD Level 2 for CI changes).
4. Be tested against at least one consumer repo before merge.

## Version Pinning

- Consumer repos pin to tagged releases (`@v0.1.0`), not branches.
- Breaking changes require a major version bump.
- All third-party actions must be pinned to immutable SHAs (SLSA L3).

## Composite Actions vs. Reusable Workflows

- **Composite actions** (`actions/*/action.yml`): Self-contained step sequences. Use when the pattern is a group of steps within a job.
- **Reusable workflows** (`.github/workflows/*.yml`): Complete job definitions with `workflow_call` trigger. Use when the pattern is an entire job or set of jobs.
