---
status: testing
phase: 08-mvp1-p5-end-to-end-mvp-1-verification
source: [08-VERIFICATION.md]
started: 2026-09-24T19:38:37Z
updated: 2026-09-24T19:38:37Z
---

## Current Test

number: 1
name: Evidence wording renders correctly in a real browser (desktop and mobile)
expected: |
  Wording matches describeEvidence()'s four scopes (course history; "No letter-grade history (pass/fail or independent study) — score is a prior"; subject fallback; no course evidence) in the table row / mobile card and the expanded details panel, with no truncation, overlap or layout regression.
awaiting: user response

## Tests

### 1. Evidence wording renders correctly in a real browser (desktop and mobile)
expected: Open the rankings page at desktop width and a mobile viewport; inspect a course row, a course/effective_n=0 (x4900) row, a subject-fallback row and a global-fallback row in both the row/card view and the expanded details. Wording matches the four scopes asserted by RankingEvidence.test.tsx, with no truncation, overlap or layout regression.
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
