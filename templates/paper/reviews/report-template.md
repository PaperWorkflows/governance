# {PERSPECTIVE} Review Report

## Metadata

- **Reviewer**: R-{A|B|C|D}
- **Paper**: {PAPER_ID}
- **Version**: {VERSION}
- **Perspective**: {PERSPECTIVE_DESCRIPTION}
- **Date**: {DATE}
- **Status**: {pending | in-progress | completed | disputed | closed}

---

## 1. Input Snapshot and Rule Version

- **Paper snapshot**: `paper.yaml` version {VERSION}
- **Rule set**: {APPLICABLE_RULES}
- **Commit SHA**: {COMMIT_SHA}

---

## 2. Applicable Rule Coverage

| Rule ID | Rule Title | Applicable | Finding |
|---------|-----------|------------|---------|
| {RULE_ID} | {RULE_TITLE} | yes/no | {FINDING_SUMMARY} |

---

## 3. Check Method

{CHECK_METHOD_DESCRIPTION}

---

## 4. Actual Execution Record

{EXECUTION_RECORD}

---

## 5. Findings

### Finding {N}: {TITLE}

- **Location**: {FILE_PATH}:{LINE_NUMBER}
- **Rule**: {RULE_ID} — {RULE_TITLE}
- **Grade**: P0 | P1 | P2
- **Impact**: {IMPACT_DESCRIPTION}
- **Evidence**: {EVIDENCE}
- **Suggested Fix**: {SUGGESTED_FIX}
- **Status**: pending-fix | fixed-pending-verify | re-verified | rebuttal-valid | not-applicable | unresolved

---

## 6. Overall Status

- **Conclusion**: pass | needs-fix | incomplete
- **P0 Issues**: {COUNT} (all must be closed for delivery)
- **P1 Issues**: {COUNT} (all must be closed or proven non-applicable)
- **P2 Issues**: {COUNT} (may be recorded as not adopted with reason)
- **Limitations**: {LIMITATIONS}
