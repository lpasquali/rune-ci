# `nginx-ingress-guard` composite action

Regression lint for [rune-docs ADR 0008](https://github.com/lpasquali/rune-docs/blob/main/docs/architecture/adrs/0008-single-container-http-tool-and-ingress-agnosticism.md) / epic [rune-docs#295](https://github.com/lpasquali/rune-docs/issues/295). Fails the job if a pull request reintroduces one of four forbidden patterns:

| # | Pattern | Scope | Exemption |
|---|---|---|---|
| 1 | `FROM nginx[:@]…` in any `Dockerfile` / `*.Dockerfile` | all files | inline comment `# allow-nginx: <reason>` within the 3 lines above the `FROM`, **or** path `rune/tests/test_k8sgpt_driver.py` (simulated-broken-pod fixture), **or** paths added via `extra-exempt-from-rule1` |
| 2 | `nginx.ingress.kubernetes.io/` annotation literal | all files | files under `docs/`, `.vex/`, any `*.md`, plus paths added via `extra-exempt-paths` |
| 3 | Helm chart `Chart.yaml` declaring `ingress-nginx` as a dependency | `Chart.yaml` / `Chart.yml` | none |
| 4 | Hardcoded `kubernetes.io/ingress.class: nginx` annotation value | all files | same as rule 2 |

## Usage

```yaml
- uses: lpasquali/rune-ci/actions/nginx-ingress-guard@<sha>
  with:
    scan-path: "."             # optional; defaults to the repo root
```

Optional inputs:

- `extra-exempt-paths` — newline-separated path prefixes added to the rule 2/4 exemption list (in addition to the built-in `docs/`, `.vex/`, `*.md`, `fixtures/`).
- `extra-exempt-from-rule1` — newline-separated file paths whose `FROM nginx` lines are exempt from rule 1 without an inline pragma. Used for test fixtures.

## Reasoning

The RUNE ecosystem standardises on Caddy (`caddy:2-alpine`) as the only container-level HTTP tool and leaves the Kubernetes Ingress controller choice to the platform operator. Annotations, hardcoded IngressClass values, and chart dependencies that privilege one controller (nginx-ingress) defeat the agnosticism goal and force downstream operators to edit values or fork the chart.

Documentation files are allowed to describe nginx-ingress (for comparison, migration notes, or historical context); the lint only blocks it in files that shape runtime / build / deployment behavior.

## Tests

Run the action's own test harness with `bash tests/nginx-ingress-guard/run.sh`. Fixtures under `actions/nginx-ingress-guard/fixtures/` contain both allowed and forbidden examples; the harness asserts that the allowed tree passes and each forbidden tree fails for the expected rule.
