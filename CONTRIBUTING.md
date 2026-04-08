<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2025-2026 The Rune Authors -->

# Contributing to rune-ci

## Before You Start

Read the RUNE engineering standards in [rune-docs](https://github.com/lpasquali/rune-docs):

1. [SYSTEM_PROMPT.md](https://github.com/lpasquali/rune-docs/blob/main/docs/context/SYSTEM_PROMPT.md) -- Architecture, constraints, SOP
2. [CODING_STANDARDS.md](https://github.com/lpasquali/rune-docs/blob/main/docs/context/CODING_STANDARDS.md) -- Style, coverage floors

## Workflow Changes

Changes to reusable workflows or composite actions affect **all 7 Rune repositories**. Every PR must:

1. Pass `actionlint` and `yamllint` (enforced by CI).
2. Include a risk assessment: which repos are affected and how.
3. Follow the PR template (DoD Level 2 for CI changes).
4. Be tested against at least one consumer repo before merge.

## Composite Actions vs. Reusable Workflows

- **Composite actions** (`actions/*/action.yml`): Self-contained step sequences. Use when the pattern is a group of steps within a job.
- **Reusable workflows** (`.github/workflows/*.yml`): Complete job definitions with `workflow_call` trigger. Use when the pattern is an entire job or set of jobs.

## Third-Party Action Pinning

All third-party GitHub Actions used within rune-ci workflows **must** be pinned to immutable SHA digests, not tags. This is a SLSA L3 compliance requirement.

```yaml
# Correct
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1

# Incorrect
- uses: actions/checkout@v4
```

---

## Version Pinning Strategy

rune-ci follows [Semantic Versioning 2.0.0](https://semver.org/).

### Versioning Policy

| Version Component | When to Bump | Example |
|---|---|---|
| **MAJOR** (vX.0.0) | Breaking changes: removed/renamed inputs, changed defaults, removed jobs/workflows, renamed workflow files | v1.0.0 -> v2.0.0 |
| **MINOR** (v0.X.0) | New features: new workflows, new composite actions, new optional inputs, new outputs | v1.0.0 -> v1.1.0 |
| **PATCH** (v0.0.X) | Bug fixes, documentation updates, internal refactors with no external behavior change | v1.0.0 -> v1.0.1 |

### Consumer Repos Must Pin to Tags

All consumer repositories (rune, rune-operator, rune-ui, rune-charts, rune-docs, rune-audit, rune-airgapped) **must** reference rune-ci using immutable version tags. Pinning to branches (e.g., `@main`) is prohibited.

```yaml
# Correct -- pinned to a release tag
jobs:
  security:
    uses: lpasquali/rune-ci/.github/workflows/security-scan.yml@v1.2.0
    secrets: inherit

steps:
  - uses: lpasquali/rune-ci/actions/gitleaks-scan@v1.2.0

# PROHIBITED -- pinned to a branch
jobs:
  security:
    uses: lpasquali/rune-ci/.github/workflows/security-scan.yml@main
```

### Release Process

Every release of rune-ci follows this process:

1. **Feature branch**: Create a branch for the change (e.g., `feat/add-trivy-action`).
2. **Pull Request**: Open a PR against `main`. The PR must:
   - Pass all CI gates (actionlint, yamllint, quality-gates).
   - Include a risk assessment of affected consumer repos.
   - Declare whether the change is breaking (see [Breaking Change Policy](#breaking-change-policy)).
   - Follow the PR template with the appropriate DoD level.
3. **Review and merge**: PR is reviewed, approved, and merged to `main`.
4. **Tag**: Create a signed, annotated git tag following semver:
   ```bash
   git tag -a v1.2.0 -m "v1.2.0: <brief summary>"
   git push origin v1.2.0
   ```
5. **GitHub Release**: Create a GitHub Release from the tag with:
   - A changelog summarizing all changes since the previous release.
   - A migration guide if the release includes breaking changes.
   - Links to relevant PRs and issues.
6. **Consumer repo updates**: Open PRs in all affected consumer repos to bump their rune-ci version pin.

### Dependabot for Consumer Repos

Consumer repos should configure Dependabot to receive automated PRs when rune-ci releases a new version. A ready-to-use template is provided at [`templates/caller-dependabot.yml`](templates/caller-dependabot.yml).

Add this block to each consumer repo's `.github/dependabot.yml`:

```yaml
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    # Dependabot will detect lpasquali/rune-ci references and propose
    # version bumps when new tags are published.
```

Dependabot natively tracks GitHub Actions references (both `uses:` in workflows and composite actions) and will open PRs when new tags are available.

---

## Breaking Change Policy

### Definitions

#### Breaking Changes

Any change that can cause existing consumer workflows to fail or behave differently without modification. Specifically:

| Change | Why It Breaks |
|---|---|
| Removing a workflow input | Consumer repos referencing the input get a CI error |
| Renaming a workflow input | Same effect as removal -- old name stops working |
| Changing a default value | Consumer repos relying on the old default get unexpected behavior |
| Removing a job from a reusable workflow | Consumer repos depending on that job's outputs or status fail |
| Removing a reusable workflow file | Consumer repos referencing the file get a 404 |
| Renaming a reusable workflow file | Same effect as removal |
| Removing a composite action | Consumer repos referencing it get a 404 |
| Removing or renaming a composite action output | Consumer repos reading the output get empty/error |
| Changing a required input to a different type | Consumer repos passing the old type get a validation error |
| Removing a `secrets: inherit` passthrough | Consumer repos relying on inherited secrets fail silently |

#### Non-Breaking Changes

Changes that are backward-compatible and safe for existing consumers:

| Change | Why It Is Safe |
|---|---|
| Adding a new optional input (with a default) | Existing consumers never pass it, so the default applies |
| Adding a new job to a reusable workflow | Existing consumers are unaffected; new job runs alongside |
| Adding a new output to a workflow or action | Existing consumers do not read it |
| Adding a new reusable workflow file | No consumer references it yet |
| Adding a new composite action | No consumer references it yet |
| Fixing a bug in existing logic | Behavior becomes correct; existing consumers benefit |
| Updating a pinned third-party action SHA | Internal implementation detail |
| Adding or improving documentation | No runtime effect |

### Version Bump Requirements

| Change Type | Required Version Bump | Additional Requirements |
|---|---|---|
| Breaking | **MAJOR** | Migration guide + downstream PRs (see below) |
| New feature | **MINOR** | Release notes describing the new capability |
| Bug fix / internal refactor | **PATCH** | Release notes describing the fix |

### Breaking Change Process

When a breaking change is necessary:

1. **Justify**: Document why the breaking change is required (not just convenient).
2. **Deprecate first**: Add a deprecation notice in the current MINOR release (see [Deprecation Process](#deprecation-process)).
3. **Major version PR**: Open a PR that:
   - Implements the breaking change.
   - Includes a **migration guide** in the PR body and release notes.
   - Updates this CONTRIBUTING.md if the change affects contribution guidelines.
4. **Downstream PRs**: Open PRs in **every affected consumer repo** that update the rune-ci version pin and apply the migration. These PRs must:
   - Reference the rune-ci release.
   - Include the migration steps applied.
   - Pass all CI gates in the consumer repo.
5. **Release**: Tag the major version and create a GitHub Release with the migration guide.

### Deprecation Process

Before removing or renaming any input, output, job, or workflow:

1. **Mark as deprecated**: In the current MINOR release, add a deprecation notice:
   - For workflow/action inputs: add `deprecationMessage` to the input definition.
   - For workflows: add a comment at the top of the file and mention it in release notes.
   - For outputs: document the deprecation in release notes.
2. **Minimum lifetime**: The deprecated item must remain functional for at least **1 MINOR version** after the deprecation notice.
3. **Removal**: Remove the deprecated item in the next MAJOR version.

Example of deprecating a workflow input:

```yaml
inputs:
  old-scanner-version:
    description: "DEPRECATED: Use scanner-version instead. Will be removed in v3.0.0."
    required: false
    default: ""
    deprecationMessage: "Use scanner-version instead. Will be removed in v3.0.0."
  scanner-version:
    description: "Version of the scanner to use"
    required: false
    default: "latest"
```

### PR Checklist for Breaking Changes

Every PR to rune-ci **must** answer the following checklist in the PR body. This is enforced by review, not CI.

```markdown
## Breaking Changes

- [ ] This PR contains **no breaking changes** (skip the rest)
- [ ] This PR contains breaking changes:
  - [ ] MAJOR version bump is planned
  - [ ] Migration guide is included in the PR body
  - [ ] Deprecation notice was added in a prior MINOR release (or this is the initial release)
  - [ ] Downstream PRs are planned for all affected consumer repos
  - [ ] List of affected repos: <!-- e.g., rune, rune-operator, rune-ui -->
```

---

## Contribution Workflow Summary

1. **Fork / branch**: Create a feature branch from `main`.
2. **Implement**: Make your changes, following all guidelines above.
3. **Test**: Validate against at least one consumer repo.
4. **PR**: Open a PR using the template. Check the appropriate DoD level (Level 2 for CI changes).
5. **Review**: Address feedback, ensure CI passes.
6. **Merge**: Maintainer merges to `main`.
7. **Release**: Maintainer tags and creates a GitHub Release.
8. **Propagate**: Update consumer repos to the new version.
