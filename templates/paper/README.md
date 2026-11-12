# Paper Workspace README

## Authoritative Sources

- **Title, authorship, version, and status**: `paper.yaml` only. Git identity does not imply authorship.
- **Body text**: `body/paper.md` is the single authoritative source. Chapter files under `body/` are splits of this source.
- **References**: `references.bib` only. No parallel bibliography files.
- **Figures and tables**: index.yaml under `figures/` and `tables/` are the authoritative inventories.

## Directory Structure

```
<paper-root>/
├── AGENTS.md                    ← 【骨架】Governance pointer → PaperWorkflows/instruction/AGENTS.md
├── paper.yaml                   ← 【骨架】Authoritative metadata
├── README.md                    ← This file
├── authors.yaml                 ← 【骨架】Per-paper author registry (private repo)
├── funding.yaml                 ← 【骨架】Funding information (optional)
├── writing-spec.yaml            ← 【骨架】Writing specification (required, content optional)
├── abstract.md                ← 【骨架】Bilingual abstract (ZH + EN)
├── outline.md                 ← 【骨架】Chapter outline with key points and word estimates
├── research-plan.md           ← 【骨架】Research plan: assumptions, metrics, baseline, budget
├── terms.md                   ← 【骨架】Terminology table
├── verification.yaml          ← 【骨架】Literature 3D verification records
├── references.bib             ← 【骨架】Bibliography
├── body/
│   ├── 01-introduction.md
│   ├── 02-background.md
│   ├── 03-method.md
│   ├── 04-experiment.md
│   ├── 05-results.md
│   ├── 06-discussion.md
│   └── 07-conclusion.md
├── figures/
│   ├── index.yaml             ← Figure inventory
│   └── *.png / *.svg / *.pdf
├── tables/
│   └── index.yaml             ← Table inventory
├── experiments/
│   ├── data/                  ← Raw data (read-only after import)
│   ├── code/                  ← Runnable code
│   ├── logs/                  ← Run logs
│   └── record.yaml            ← Experiment records
├── appendix/                  ← Supplementary materials
├── build-record.md            ← **入库的发布账本**：每次构建的可复现步骤、产物校验与版式决策
└── build/                     ← 产物本体（**不入库**，见 .gitignore）
    └── layout.yaml            ← Paper-level layout overrides
```

> **产物不入库**：docx / PDF / manifest 留在 `build/<version>/` 的本地工作区。
> 入库的凭据是 `build-record.md`（人可读：为什么这么排、改了什么、没改什么）
> 与 `build/<version>/manifest.json`（机器可读：输入快照、profile 与 refdoc 的
> sha256、规则版本、产物 sha256）。见 PF-B5 / PF-B6 / PF-B7。

## Stage Lifecycle

| Stage | Meaning | Unresolved items required |
|---|---|---|
| `intake` | Materials received, being assessed | Yes |
| `proposal` | Outline and research plan drafted | Yes |
| `research` | Experiments running | Yes |
| `writing` | Body text in progress | Yes |
| `review` | Under review | No |
| `revision` | Fixing review issues | Yes |
| `build` | Typesetting and producing docx/PDF | No |
| `released` | Deliverable accepted | No |
| `archived` | Archived after publication | No |

## Version Policy

- `paper_version` in `paper.yaml` follows `major.minor.patch`.
- `0.1.0`: initial draft. `1.0.0`: first accepted release.
- Changelog is expressed through commit messages.

## Temp Policy

- Temporary materials, caches, and temp config go to `temp/P<ID>-<DATE>-<TITLE>-<AUTHOR>/TASK-<NNNN>/`.
- Temp is gitignored and not committed.
- Build intermediates also go to temp.

## Git

- This workspace is an independent git repository with its own GitHub remote under the `PaperWorkflows` org.
- Local git identity: `janssenkm <janssenkm@users.noreply.github.com>`.
- One commit = one logical change. Commit message format: `<type>(<scope>): <description>`.
- Paper commits only include paper workspace content. Governance changes go to the `PaperWorkflows/instruction` repo.
