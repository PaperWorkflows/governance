# Version and Commit Rules

## Scope

This file defines version numbering, repository structure, commit scoping, and related verification discipline for PaperFactory.

## Rules

### PF-V1 规则追溯

- Any task reads root AGENTS.md first, then traces rule-index and relevant rules per task needs. Not required to read all governance files every time.
- Record actually applicable rule versions, entries, and necessary exception bases. Cannot use on-demand reading to bypass applicability requirements.

### PF-V2 独立版本号

- `paper.yaml.paper_version` is per-paper independent scientific version using SemVer 2.0.0 format `vMAJOR.MINOR.PATCH`.
- Initial draft: `v0.1.0`. First accepted release: `v1.0.0`.
- **MAJOR**: research question, core method, or core conclusion changes substantially (old version's core argument cannot be directly carried forward).
- **MINOR**: core framework holds; new methods, evidence, experiments, or qualified conclusions added.
- **PATCH**: wording, annotations, typesetting, or non-conclusion-affecting corrections.
- Evidence changes sufficient to overturn or change core conclusions cannot be patch.
- After higher-order increment, lower orders reset to zero. Not based on word count, line count, or task count.

### PF-V3 版本号变更记录

- Each scientific version change records: issue, method, evidence, conclusion impact, and rationale. Must be re-verified per R6.
- Version number does not substitute for quality judgment. Pure scheduling logs, maintenance records, or non-paper-affecting process records do not change paper_version.
- Toolchain migrations without scientific impact do not auto-bump paper_version, but actual dependencies and acceptance relationships must be updated.

### PF-V4 多仓库结构

- Governance repo (`PaperWorkflows/instruction`, public): holds AGENTS.md, CLAUDE.md, project.yaml, governance/, schemas/, templates/, tools/, authors/.
- Paper repos (`PaperWorkflows/P{N}-{AUTHOR_EN}-{YYYYMMDD}`, private): each holds one paper workspace. Independent git repo, independent GitHub remote.
- `papers/` directory in governance repo is gitignored. Paper repos are cloned into `papers/` by user or tooling.

### PF-V5 提交分区

- Each commit is scoped to one of: pure governance, or exactly one paper repo's content.
- Mixing governance and paper content in one commit is forbidden. Cross-paper commits are forbidden.
- Governance commit includes: governance files, schemas, templates, tools, authors registry.
- Paper commit includes: everything within that paper's workspace.

### PF-V6 Changelog

- Changelog is expressed through commit messages. Each commit message must clearly describe the change.
- Conventional commits recommended: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- Version bumps must include the version change reason in the commit body.

### PF-V7 临时目录

- Paper temp materials, build intermediates, caches, and temp config are in the paper repo's `temp/P<ID>-<DATE>-<TITLE>-<AUTHOR>/TASK-<NNNN>/`.
- Governance test namespace uses `temp/P9999/` (reserved, not a real paper).
- Temp directories are gitignored. Not committed.

### PF-V8 前置检查

- Pre-build: validate paper.yaml against schema, check body files exist, check references.bib exists.
- Pre-commit: verify commit scope matches intended target (governance repo vs specific paper repo).
- Pre-release: verify both docx and PDF exist, manifest is valid, review status is complete.

### PF-V9 骨架成员

- 每篇论文工作区必须包含以下骨架成员（Skeleton Members），缺一不可：
  1. `paper.yaml` — 论文元数据（唯一权威源）
  2. `authors.yaml` — 作者信息（私有仓库，可放敏感信息）
  3. `funding.yaml` — 基金项目信息（可选，可空）
  4. `writing-spec.yaml` — 编写规范（必选文件，内容可选）
  5. `abstract.md` — 中英双语摘要
  6. `outline.md` — 大纲
  7. `research-plan.md` — 研究方案
  8. `terms.md` — 术语表
  9. `verification.yaml` — 文献三维核验记录
  10. `references.bib` — 参考文献
  11. `body/` — 正文目录（按一级章节拆分）
  12. `figures/` — 图目录（含 index.yaml）
  13. `tables/` — 表目录（含 index.yaml）
  14. `experiments/` — 实验目录（含 data/, code/, logs/, record.yaml）
  15. `appendix/` — 附录目录
  16. `build/` — 构建配置目录（含 layout.yaml）
  17. `AGENTS.md` — 治理指针（指向 PaperWorkflows/instruction/AGENTS.md）
  18. `materials.yaml` — 素材注册表（文献、数据集、代码、工具）
- `check` 工具验证骨架成员完整性；缺失则检查失败。

### PF-V10 论文仓库独立性

- 论文仓库为私有，所有作者信息、基金信息、编写规范均存放于该仓库内。
- 治理仓库（instruction）不存储任何论文的作者或基金信息。
- Git 提交身份统一使用 `janssenkm <janssenkm@users.noreply.github.com>`，与论文作者身份无关。
