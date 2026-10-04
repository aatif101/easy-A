---
status: complete
phase: 08-mvp1-p5-end-to-end-mvp-1-verification
source: [08-VERIFICATION.md]
started: 2026-09-24T19:38:37Z
updated: 2026-09-24T20:20:33Z
---

## Current Test

[testing complete]

## Tests

### 1. Evidence wording renders correctly in a real browser (desktop and mobile)
expected: Open the rankings page at desktop width and a mobile viewport; inspect a course row, a course/effective_n=0 (x4900) row, a subject-fallback row and a global-fallback row in both the row/card view and the expanded details. Wording matches the four scopes asserted by RankingEvidence.test.tsx, with no truncation, overlap or layout regression.
result: pass
reported: "pass wording matches describeEvidence()'s four scopes"

## Summary

total: 1
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
