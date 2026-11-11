# Review Reports

Four-perspective independent review reports (PF-RV2).

## Directory Structure

```
reviews/
├── README.md                          ← This file
├── R-A-{paper_id}-v{version}.md       ← Venue/editor perspective
├── R-B-{paper_id}-v{version}.md       ← Technical/reproducibility perspective
├── R-C-{paper_id}-v{version}.md       ← Editor/reader perspective
├── R-D-{paper_id}-v{version}.md       ← Layout/output perspective
├── issues.yaml                        ← Consolidated issue tracking
├── polish-r0-extract.md               ← Polish step 0a terminology extraction (PF-PL2)
├── polish-r1-logic.md                 ← Polish diagnosis / track decision (PF-PL3)
├── polish-r3-diff.md                  ← Semantic diff verification (PF-PL7)
├── polish-r4-transition.md            ← Paragraph transition diff (PF-PL8)
├── polish-rewrite-plan.md             ← Rewrite track plan, user-approved (PF-PL5)
├── polish-issues.yaml                 ← Polish-period issue ledger (merged into issues.yaml at next review)
├── polish-version-record.md           ← Version bump record (PF-PL11 / PF-V3)
└── venue-refactor-note.md             ← Config-level refactor registry (rules_version switch, PF-RV6 invalidation)
```

## Perspective Responsibilities (PF-RV2)

- **R-A** (venue/editor): W1-W4, W9-W10, P rules → problem value, contribution, related work, logic, independence, submission fit
- **R-B** (technical/reproducibility): W4-W8, W10, T/P/S rules → proof, algorithm, system, data, experiment, statistics, source support, reproduction
- **R-C** (editor/reader): W1-W3, W6-W10, T/P rules → bilingual consistency, terminology, citations, authorship, structure, self-sufficiency
- **R-D** (layout/output): W2, W8, T rules → docx, PDF, captions, formulas, figures, tables, layout

## Venue Compliance (PF-RV7)

When `paper.yaml.target_venue` is set and `writing-spec.yaml` carries venue constraints,
R-A/R-C verify compliance item by item (checklist = PF-PL13); R-D verifies built artifacts
against the merged layout profile. Mechanically decidable hard constraints are at least P1.

## Issue Grades (PF-RV4)

- **P0** (blocking): invalidates core authenticity, correctness, independence, or delivery safety. Unresolved = not a deliverable.
- **P1** (important): affects evidence sufficiency, interpretation, reproduction, or style compliance. Must be fixed or proven non-applicable.
- **P2** (improvement): expression or presentation improvement. May be recorded as not adopted with reason.

## Report Structure

Each review report must include:
1. Input snapshot and rule version
2. Applicable rule coverage
3. Check method
4. Actual execution record
5. Issue location, rule basis, grade, suggested fix
6. Limitations

## Status Values

- `pending` — review not started
- `in-progress` — review in progress
- `completed` — review complete, issues recorded
- `disputed` — dispute arbitration in progress
- `closed` — all issues resolved
