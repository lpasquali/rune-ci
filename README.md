# rune-ci

Shared GitHub Actions reusable workflows and composite actions for the [RUNE](https://github.com/lpasquali/rune) platform.

## Purpose

Consolidate ~2,500 lines of duplicated CI/CD YAML across 7 Rune repositories into a single, version-pinned source of truth. A CI change (e.g., bumping a scanner version) requires exactly **one PR** in this repo instead of seven.

## Structure

```
.github/workflows/     # Reusable workflows (called by consumer repos)
actions/               # Composite actions (steps shared across workflows)
  gitleaks-scan/       # Secret scanning
  sbom-scan/           # SBOM generation + CVE scanning (Syft, Grype, Trivy)
  license-check/       # License compliance (pip-licenses, go-licenses)
  docker-setup/        # Docker login + buildx + cache setup
scripts/               # Shared scripts (merge gate, etc.)
```

## Usage

Consumer repos call reusable workflows via `uses:`:

```yaml
jobs:
  security:
    uses: lpasquali/rune-ci/.github/workflows/security-scan.yml@v0.1.0
    secrets: inherit
```

Or use composite actions directly in steps:

```yaml
steps:
  - uses: lpasquali/rune-ci/actions/gitleaks-scan@v0.1.0
```

## Version Pinning

All consumer repos pin to a **tagged release** of `rune-ci` (e.g., `@v0.1.0`). Breaking changes follow semver and are documented in release notes.

## Supported Workflows

| Workflow | Description | Consumers |
|---|---|---|
| `security-scan.yml` | Gitleaks + SBOM/CVE scanning | All repos |
| `pr-compliance.yml` | PR body validation + merge gate + ML4 approval | All repos |
| `python-quality.yml` | pytest + ruff + mypy + bandit + coverage | rune, rune-ui, rune-audit |
| `go-quality.yml` | go test + gofmt + go vet + gosec + coverage | rune-operator |
| `container-build.yml` | Multi-arch Docker build (amd64 + arm64) | rune, rune-operator, rune-ui, rune-docs |
| `release.yml` | Tag guard + container publish + GitHub Release | rune, rune-operator, rune-ui, rune-docs |
| `helm-quality.yml` | helm lint + trivy config scan | rune-charts |
| `docs-quality.yml` | mkdocs build --strict + pymarkdown | rune-docs |
| `shell-quality.yml` | shellcheck + yamllint | rune-airgapped |
| `codeql-callable.yml` | CodeQL via `workflow_call` (`language`: python or go) | Optional thin callers |
| `codeql.yml` | Standalone **Code Scanning (CodeQL)** for this repository (Python; same layout as `rune`) | `rune-ci` only |

Implementation for the split lives in commit `45b2db6` (retro process tracking: **#21**).

## License

Apache-2.0. See [LICENSE](LICENSE).
