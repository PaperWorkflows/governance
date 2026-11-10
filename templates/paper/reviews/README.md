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
└── issues.yaml                        ← Consolidated issue tracking
```

## Perspective Responsibilities (PF-RV2)

- **R-A** (venue/editor): W1-W4, W9-W10, P rules → problem value, contribution, related work, logic, independence, submission fit
- **R-B** (technical/reproducibility): W4-W8, W10, T/P/S rules → proof, algorithm, system, data, experiment, statistics, source support, reproduction
- **R-C** (editor/reader): W1-W3, W6-W10, T/P rules → bilingual consistency, terminology, citations, authorship, structure, self-sufficiency
- **R-D** (layout/output): W2, W8, T rules → docx, PDF, captions, formulas, figures, tables, layout

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
