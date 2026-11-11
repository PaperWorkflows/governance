# PaperFactory

This project manages independent academic papers from proposal through publication. User instructions take precedence over project files; this file governs all public rules for the main session and all executors.

---

## F1 Scope

- Maintain multiple paper workspaces numbered P1–P999. Each paper occupies one directory under `papers/`.
- Each paper is an independent git repository with its own GitHub remote. Governance files live in a separate governance repo.
- Every paper workspace follows a standard file skeleton covering: metadata, chapter-split body, figures, tables, references, experiments (data + code + logs), build config, and more.

---

## F2 Paper Modes

1. **Proposal mode**: Receive user materials and ideas, organize into the paper素材库, assess feasibility, finalize outline and research plan.
2. **Research mode**: Retrieve and analyze materials (user-provided or web-searched), execute code, data processing, and statistical analysis.
3. **Writing mode**: Generate paper body from outline and research data. Supports投稿requirements (length, content). Natural human language, academic style, citation management.
4. **Build mode**: Layout and produce docx and PDF from source, using default or venue-specific templates.
5. **Review mode**: Automated review流程covering style, wording, and academic standards.
6. **Polish mode**: Controlled refinement of a written body — logic transitions, wording, terminology constraints, and venue writing-standard compliance — without adding new facts. See `governance/polish.md` (PF-PL1–PF-PL13).

---

## F3 Version Management

- Each paper maintains an independent `paper_version` in `paper.yaml` using SemVer 2.0.0 `vMAJOR.MINOR.PATCH` format.
- Initial draft: `v0.1.0`. First accepted release: `v1.0.0`.
  - **MAJOR**: research question, core method, or core conclusion changes substantially.
  - **MINOR**: core framework holds; new methods, evidence, experiments, or qualified conclusions added.
  - **PATCH**: wording, annotations, typesetting, or non-conclusion-affecting corrections.
- Changelog is expressed through commit messages. Higher-order increments reset lower orders.

---

## F4 Author Library

- Each paper manages its own author information in `authors.yaml` (per-paper, private repo).
- Supports first author, second author, corresponding author roles.
- Author names require user confirmation; never derived from Git identity.

---

## F5 Dispatch and Governance

- **Main session**: coordination and governance only. Receives requirements, dispatches subagents, tracks progress, reconciles scope and versions, reports status. Never writes, edits, runs experiments, builds, or signs off on papers.
- **Subagents**: execute all paper production work — proposal, import, novelty search, literature verification, research design, proof, code experiments, writing, figures, review, revision, build, commit, and delivery.
- Governance file changes (public rules, templates, tools, safety) are governance tasks handled by the main session or delegated subagents; never used as cover to modify paper content.

---

## F6 Evidence and References

- All paper tasks are grounded in fact, academic logic, derivation, and actual execution. No fabricated literature, experiments, authorship, or verification results.
- Modify only what is necessary; clean up only task-registered artifacts. Pragmatic, meticulous, restrained. Do not inflate scope or pad content.
- When user claims or topics change, dispatch a subagent for novelty search, compare closest published work, record search date, query, sources, and boundaries.

---

## F7 Safety and Constraints

- Unauthorized permanent deletion, Git history destruction, external transmission, submission, push to unauthorized remotes, or paid API calls are prohibited.
- Preserve the scene on failure; no full-repo rollback.
- Governance capability (prompts + code + Skills + MCP + SubAgent planning) is maintained by the project to maximize agent autonomy, reducing user communication after governance is complete.

---

## F8 Rule Index

Common requirements are defined once in [rule-index.yaml](governance/rule-index.yaml). Writing, review, build, and research rules are referenced as needed. Record conflicts; unresolved research trade-offs go to the user; do not silently lower authenticity requirements.

---

## F9 Governance Change Discipline

- Governance files (this file, CLAUDE.md, project.yaml, everything under `governance/`, `templates/`, `schemas/`, `tools/`, `authors/`) must be changed only after: numbering, baseline and plan version, exact change list, rationale, alternatives, risks, recovery, and verification method are all documented.
- A subagent that did not participate in the change must review and verify the plan before it is written to disk. After writing, an independent subagent must verify actual diffs and check results before commit.
- The main session must never approve its own governance changes.

---

*F1–F9 are PaperFactory's public governance principles. Mode-specific execution rules are in separate governance files.*
