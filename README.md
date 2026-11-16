# PaperFactory

Governance repo for PaperWorkflows org. This is the public `PaperWorkflows/governance` repo.

## Structure

- `AGENTS.md` — Public governance principles (F1–F9)
- `CLAUDE.md` — Entry pointer
- `project.yaml` — Project configuration and capability status
- `governance/` — Mode-specific rules (proposal, research, writing, build, review, versions)
- `governance/rule-index.yaml` — Single source of truth for all rule IDs
- `schemas/` — JSON schemas for paper.yaml and authors.yaml
- `templates/` — Paper workspace template skeleton
- `tools/` — CLI tools (scaffold, check, version-bump)
- `authors/` — Author registry

## Paper Repos

Each paper is a separate private repo under `PaperWorkflows/`:

```
P1-Example_Paper_Title-Author_A   ← P{N}-{TITLE_EN}-{FIRST_AUTHOR_EN}  (≤100 chars, see GC-2026-1116-07)
...
```

Local directory pattern: `papers/P{N}-{AUTHOR_EN}-{YYYYMMDD}/`

```bash
'git clone git@github.com:PaperWorkflows/P1-Example_Paper_Title-Author_A.git papers/P1-EXAMPLE-20251110'
```
