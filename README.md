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

All consumer repos pin to a **tagged release** of `rune-ci` (e.g., `@v0.1.0`). Breaking changes follow [Semantic Versioning 2.0.0](https://semver.org/) and are documented in release notes.

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
| `nginx-ingress-guard.yml` | Regression lint for [ADR 0008](https://github.com/lpasquali/rune-docs/blob/main/docs/architecture/adrs/0008-single-container-http-tool-and-ingress-agnosticism.md): blocks `FROM nginx`, `nginx.ingress.kubernetes.io/*` annotations, `ingress-nginx` chart deps, and hardcoded `kubernetes.io/ingress.class: nginx`. See [`actions/nginx-ingress-guard/README.md`](actions/nginx-ingress-guard/README.md). | All repos (follow-up wiring) |

Implementation for the split lives in commit `45b2db6` (retro process tracking: **#21**).

## Tools & standards referenced

Official documentation for the tools and standards invoked by the workflows above. Same URLs as the rune-docs [External Links Catalog](https://github.com/lpasquali/rune-docs/blob/main/docs/reference/EXTERNAL_LINKS.md).

**Security & compliance**

- [gitleaks](https://github.com/gitleaks/gitleaks) — secret scanning
- [Syft](https://github.com/anchore/syft) — SBOM generation
- [Grype](https://github.com/anchore/grype) — CVE scan
- [Trivy](https://trivy.dev/) — container + config scan
- [Bandit](https://bandit.readthedocs.io/) — Python SAST
- [gosec](https://github.com/securego/gosec) — Go SAST
- [CodeQL](https://codeql.github.com/docs/) — static analysis
- [pip-licenses](https://pypi.org/project/pip-licenses/) — Python license check
- [go-licenses](https://github.com/google/go-licenses) — Go license check

**Language tooling**

- [ruff](https://docs.astral.sh/ruff/) — Python linter
- [mypy](https://mypy.readthedocs.io/) — Python type checker
- [pytest](https://docs.pytest.org/) — Python test runner
- [gofmt](https://pkg.go.dev/cmd/gofmt) — Go formatter
- [go vet](https://pkg.go.dev/cmd/vet) — Go correctness checks

**Docs / config / shell**

- [MkDocs](https://www.mkdocs.org/) — docs site builder
- [PyMarkdown](https://github.com/jackdewinter/pymarkdown) — markdown linter
- [actionlint](https://github.com/rhysd/actionlint) — GitHub Actions YAML linter
- [yamllint](https://yamllint.readthedocs.io/) — YAML linter
- [shellcheck](https://www.shellcheck.net/) — shell linter
- [Helm](https://helm.sh/docs/) — K8s package manager

**Compliance standards**

- [IEC 62443-4-1](https://webstore.iec.ch/publication/33615) / [ISA overview](https://www.isa.org/standards-and-publications/isa-standards/isa-iec-62443-series-of-standards) — secure product development lifecycle
- [SLSA v1.0](https://slsa.dev/spec/v1.0/) — Supply-chain Levels for Software Artifacts
- [Semantic Versioning 2.0.0](https://semver.org/) — release versioning

## License

Apache-2.0. See [LICENSE](LICENSE).
