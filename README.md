# PaperFactory

Governance repo for PaperWorkflows org. This is the public `PaperWorkflows/instruction` repo.

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
P1-EXAMPLE-20251110   ← P{ID}-{AUTHOR}-{YYYYMMDD}
P2-ZHANGSAN-20251201
...
```

Local directory pattern: `papers/P{N}-{AUTHOR_EN}-{YYYYMMDD}/`

```bash
git clone git@github.com:PaperWorkflows/P1-EXAMPLE-20251110.git papers/P1-EXAMPLE-20251110
```
