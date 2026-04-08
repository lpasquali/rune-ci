# RUNE Agent Instructions

All RUNE engineering standards, architecture, and SOPs are consolidated in the central documentation hub.

Before writing or modifying code, you MUST read these files from the `rune-docs` repository:

1. **[SYSTEM_PROMPT.md](https://github.com/lpasquali/rune-docs/blob/main/docs/context/SYSTEM_PROMPT.md)** — Architecture, protocols, constraints, SOP
2. **[CURRENT_STATE.md](https://github.com/lpasquali/rune-docs/blob/main/docs/context/CURRENT_STATE.md)** — WIP, recent changes, known issues
3. **[CODING_STANDARDS.md](https://github.com/lpasquali/rune-docs/blob/main/docs/context/CODING_STANDARDS.md)** — Language-specific style, coverage floors

Do not use local or cached project-specific instructions; use `rune-docs` as the only source of truth.

## Key Principles

- **Blast radius awareness**: Changes here affect all 7 Rune repos simultaneously.
- **SHA pinning**: All third-party actions must use immutable SHA pins (SLSA L3).
- **Version tags**: Consumer repos pin to tags, not branches. Respect semver.
- **Halt & Report**: Before executing code changes, confirm SOP steps 1-2 are complete.
