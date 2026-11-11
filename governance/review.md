# Review Mode Rules

## Scope

This file defines the review mode execution rules. Review mode covers: four-perspective independent review, issue grading, dispute resolution, and fix closure.

## Rules

### PF-RV1 生效规则与审核边界

- Main session assigns: paper identity, perspective, fixed input, applicable rule set, evidence scope, and unique report path for each review task.
- Reviewer is read-only. Can only write the assigned report. Cannot modify body, config, code, data, figures, or public rules.
- Each finding cites specific rule ID, location, evidence, and impact. New requirements not in existing rules can only be proposed as governance revisions, not used to silently reject papers.
- Each applicable rule must have a review finding. Each "not applicable" must have a research-type or style basis.
- Checks not actually executed are marked unverified, not passed. Tool missing, source unobtainable = limit noted, impact on conclusion explained.

### PF-RV2 四视角独立初审

- R-A (venue/editor perspective): verifies W1-W4, W9-W10, and applicable P rules for problem value, contribution, related work, logic, independence, and submission fit.
- R-B (technical/reproducibility perspective): verifies W4-W8, W10, and applicable T/P/S rules for proof, algorithm, system, data, experiment, statistics, source support, and reproduction conditions.
- R-C (editor/reader perspective): verifies W1-W3, W6-W10, and applicable T/P rules for bilingual consistency, terminology, citations, authorship, structure, self-sufficiency, and pragmatic wording.
- R-D (layout/output perspective): verifies W2, W8, and applicable T rules for docx, PDF, captions, formulas, figures, tables, and layout.
- Four perspectives conduct independent initial review on the same input, forming judgment before viewing other opinions. One task = one paper × one perspective.
- Same version must not be uniquely accepted by the writer (R3).

### PF-RV3 写审分离

- Executor cannot be the sole acceptor of the same version. Review and fix are dispatched separately.
- Prefer cross-dispatch between general-glm and general-minimax. Record actual executor and degradation reason.
- Subagent unavailability is recorded as gap; main session does not substitute.
- Image issues require second executor or source confirmation before modification.

### PF-RV4 问题分级

- P0 (blocking): invalidates core authenticity, correctness, independence, or delivery safety. Examples: fabricated results, key proof error, snapshot mixing. Unresolved = not a deliverable.
- P1 (important): affects evidence sufficiency, interpretation, reproduction, or style compliance. Must be fixed and re-verified, or proven non-applicable with evidence. Cannot be simply recorded and passed.
- P2 (improvement): expression or presentation improvement that does not affect current requirement satisfaction. May be recorded as not adopted with reason.
- Report must include: input snapshot and rule version, applicable rule coverage, check method, actual execution record, issue location, rule basis, grade, suggested fix conditions, and limitations.
- Overall status: pass, needs-fix, or incomplete. Warning count does not substitute for complete conclusion.

### PF-RV5 争议与复核

- Main session compiles disputes, both sides' evidence, and pending questions; dispatches independent subagent for arbitration.
- Arbitration checks original text, proof, code, data, or rendering per specific rules. Reports verifiable evidence, support, and counterexamples.
- Majority agreement is only a clue, not a substitute for actual verification.
- Two rounds of集中review still unresolved: record分歧 and evidence gaps, move to补证, claim narrowing, research adjustment, or user report.

### PF-RV6 修复闭环

- Record per issue: pending-fix, fixed-pending-verify, re-verified, rebuttal-valid, not-applicable, or unresolved. Attach evidence.
- Original report preserved. Fix task only modifies authorized scope.
- After body, literature, data, code, figures, authorship, config, toolchain, or layout changes, subagent checks impact and复审 affected items. Cannot reuse expired reports.
- Final report binds to current complete snapshot and re-verification relationships.
- Delivery requires: applicable rules verified, P0/P1 all closed, P2 disposition recorded, and both T-rule artifacts with visual verification complete.

### PF-RV7 目标刊格式合规复核

- Reviewers verify the paper against the venue constraints recorded in `writing-spec.yaml` (PF-W11), and against the layout profile selected in `paper.yaml.layout_profile` (PF-B11/PF-B12).
- Mechanical checks (title length and punctuation, abstract length and forbidden subject forms, keyword count and separator, presence of the English abstract and keyword blocks, funding note ordering, corresponding-author marking, author biography fields) are executed and recorded with actual values, not asserted.
- Advisory constraints are reported against their tolerance band; exceeding an advisory constraint is P2 unless the venue's own text makes it binding.
- The layout side is verified against the built artifacts: page geometry, body font and size, heading hierarchy, table rule style, caption placement, page numbering, and the absence of residual default styling. Deviations that the build did not already flag are P1.
- Findings cite the venue clause or the profile key they rest on. Where a value originates from a fallback rather than the venue, the report must say so (PF-B14).
