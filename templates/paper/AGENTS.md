# Paper Workspace Governance Pointer

This paper workspace is governed by the canonical rules in:
`PaperWorkflows/instruction/AGENTS.md`

## Local Skeleton Members (PF-V9)

This paper repo contains the following required governance files:
- `paper.yaml` — paper metadata (title, authors ref, version, stage, applicable rules)
- `authors.yaml` — author information (private repo: full details allowed)
- `funding.yaml` — funding information (optional, may be empty)
- `writing-spec.yaml` — venue-specific writing requirements (required file, content optional)

## How to Read Rules

1. Read the canonical `AGENTS.md` in `PaperWorkflows/instruction/` for all governance principles (F1–F9).
2. Read mode-specific rules in `PaperWorkflows/instruction/governance/` as needed:
   - `proposal.md` — PF-P1 to PF-P8
   - `research.md` — PF-R1 to PF-R8
   - `writing.md` — PF-W1 to PF-W10
   - `build.md` — PF-B1 to PF-B10
   - `review.md` — PF-RV1 to PF-RV6
   - `versions.md` — PF-V1 to PF-V10
3. Read `schemas/` for paper.yaml and authors.yaml structures.
4. Read `templates/` for file skeletons and examples.

## Git Identity

All commits in this repository use:
`janssenkm <janssenkm@users.noreply.github.com>`

Git identity does not imply paper authorship. Authorship is declared in `authors.yaml`.

## Quick Reference

- Paper ID: see `paper.yaml` → `id`
- Paper version: see `paper.yaml` → `paper_version`
- Stage: see `paper.yaml` → `stage`
- Authors: see `authors.yaml`
- Writing requirements: see `writing-spec.yaml`
- Funding: see `funding.yaml`
