# Proposal Mode Rules

## Scope

This file defines the proposal mode execution rules. Proposal mode covers: receiving user materials, organizing into the paper素材库, assessing feasibility, finalizing outline, and designing the research plan.

## Rules

### PF-P1 原始材料登记

- Record all source materials with origin, acquisition date, authorization, and checksum. Original materials are read-only after import.
- Do not overwrite, clean, or modify original materials in place. Extraction, cleaning, and rewriting go to new files.

### PF-P2 联网查新

- For every new paper claim, topic, or modification request, dispatch a subagent to perform novelty search.
- Search scope must be proportional: new topics cover related problems and main methods; local modifications focus on affected claims.
- Record: user request, search date, channel, query terms, scope, sources visited, closest published work, impact on current request, uncovered scope, access limits, and uncertainty.
- Existing sources may be reused after verifying current applicability. No results or access failure does not imply novelty.

### PF-P3 选题与独立性评估

- Subagent reports closest published work and its impact on the topic, claim, modification, or writing requirement.
- Clearly indicate similar work; distinguish between: substantial duplication, verifiable but unconfirmed increment, or insufficient evidence/resources.
- Recommend only after evidence is obtained and independently verified. Complex decisions require independent cross-validation.
- When unable to form a conclusion, explicitly state no recommendation, explain information gaps, and ask neutral questions. Do not set default recommendations.

### PF-P4 题目拆分边界

- Large topics may be split. Before splitting, compare each sub-topic's problem, method, data, results, and conclusion.
- Register source overlap. Do not repackage the same core results under different titles.
- Internal cross-paper citation requires the cited paper to be formally published with verifiable records. Preprints follow venue policy.

### PF-P5 论文配置草案

- Upon topic selection, instantiate `paper.yaml` from template with: confirmed title, confirmed authors (or empty if unconfirmed), paper_type, stage, applicable_rules, budget, and unresolved items list.
- `paper.yaml` is the single authoritative source for title, authors, version, and status.
- Draft instances go to `temp/`; formal instantiation goes to the paper workspace root.

### PF-P6 大纲设计

- Design outline after evidence is available. Each chapter must have: chapter number, title, key points, estimated word count, and evidence sources.
- Outline structure follows the paper type: theory (definitions, propositions, proofs), algorithm experiment (method, comparison), system (design, implementation, load validation), empirical (object, method, results, interpretation).
- Do not force IMRAD or a fixed chapter count. Add experiments only when they serve a claim.

### PF-P7 研究方案

- Before formal research, document: claims, assumptions, evidence gaps, verification path, comparison baseline, success and failure criteria.
- Configure time, compute, storage, and external service budgets with explicit limits, units, authorization scope, and stop conditions.
- Record execution environment tier (E0/E1/E2/E3) and authorization. Isolation requirements follow the isolation profile.

### PF-P8 开题交付

- Deliverables: topic proposal document, paper.yaml draft, outline document, research plan document.
- All unresolved items must be listed with owners and target resolution dates.
- Formal instantiation of the paper workspace (creating `papers/P<ID>-<DATE>-<TITLE>-<AUTHOR>/`) requires user confirmation of topic and authors.
