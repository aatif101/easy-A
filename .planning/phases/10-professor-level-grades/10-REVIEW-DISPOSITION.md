---
phase: 10-professor-level-grades
review: 10-REVIEW.md
reviewed: 2026-10-01
findings: 12
open: 12
note: "All findings default to open; none has been triaged. Phase 10 IDs overlap Phase 9's WR-/IN- numbering (e.g. Phase 9 WR-03 is the cadence-floor race; Phase 10 WR-03 below is the --apply gate). Always cite the phase."
---

# Phase 10 review disposition

Advisory ledger written by the execute-phase orchestrator. Review result: 0 Critical, 5 Warning, 7 Info. Nothing here blocked execution; no finding has been fixed or dismissed yet.

| Finding | Severity | Summary | Disposition |
|---------|----------|---------|-------------|
| P10-WR-01 | Warning | Instructor panel says "No instructor-level grade history is recorded" while also listing "N other instructors" (InstructorBreakdown.tsx isEmpty ignores other_instructor_count); user-visible, live | open |
| P10-WR-02 | Warning | DB error text leaks host/IP/role into stdout and --report-json (scrub only strips scheme://) | open |
| P10-WR-03 | Warning | --apply gate vacuous when --rebuild-term is a nonexistent term (empty stored_before; invariant passes trivially); same for --rollback/--rebuild-only | open |
| P10-WR-04 | Warning | --report-json written unguarded after commit (no path rule, not atomic, OSError gives exit 1 after a committed run) | open |
| P10-WR-05 | Warning | Gating scripts mask errors as "NOT MEASURED"; config errors exit 1 which report_ranking_diff documents as "a difference was found" | open |
| P10-IN-01 | Info | _redact runs on serialized JSON and can corrupt output | open |
| P10-IN-02 | Info | Docstrings overstate pre-normalisation gate and diagnostics guarantees | open |
| P10-IN-03 | Info | Float noise inflates abs_delta buckets; rank from raw floats | open |
| P10-IN-04 | Info | measure_instructor_pairs groups names differently from the scorer | open |
| P10-IN-05 | Info | Unbounded IN (...) lists sized by grade rows (~13% of psycopg3 limit today) | open |
| P10-IN-06 | Info | Anchor repair can move visible note text into the tag; helper scripts duplicate code | open |
| P10-IN-07 | Info | Exit code 2 overloaded; hosted-beta runbook says to retry on it | open |
