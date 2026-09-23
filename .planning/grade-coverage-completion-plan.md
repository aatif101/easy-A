# Grade coverage completion plan — Spring 2025 cutoff

Goal: give every Spring 2027 Tampa section with an available, approved InfoCenter grade history
an exact-course match in hosted Supabase. Query only Spring 2025, Summer 2025, Fall 2025,
Spring 2026, and Summer 2026. Summer 2026 has so far returned no rows. The 179 older pilot rows
stay in place, but no more pre-Spring-2025 data will be gathered.

Baseline (2026-09-23): 3,783 current sections / 1,401 courses; 2,571 sections / 793 courses have
an own-course history match; 1,212 sections / 608 courses do not. Muma, Engineering, and Arts and
Sciences have been processed. The exact remaining college membership is not stored in `sections`.

## Execution

1. Inventory the remaining InfoCenter college choices for Tampa and run one Spring 2026
   all-department report per college. Record `NO ROWS RETURNED`, complete, or capped. For complete
   reports, download the XLSX and verify its displayed term, campus, college, row count, unique
   CRNs, grade totals, and parsed grade-bucket sums. Keep raw files outside Git.
2. Split capped college reports using disjoint department selections, or the two distance-learning
   restriction values when each is uncapped. Reject a capped partition. Reconcile partition CRNs
   and grade values against the capped college preview and check for duplicates.
3. Import exact course keys represented in Spring 2027 Tampa sections with
   `scripts/ingest_college_grades.py`. Each source XLSX retains its own SHA-256 and term/CRN/source
   deduplication. Record per-report and per-import counts. Verify the live database after each term.
4. Repeat for Fall 2025, Spring 2025, and Summer 2025, focusing first on colleges and course keys
   still without an own-course match. Query Summer 2026 only to confirm whether it remains empty.
5. For residual unmatched course keys, use bounded exact course queries in InfoCenter across the
   allowed terms. Mark a course unavailable if every allowed query returns no rows or only
   suppressed/invalid data. Do not infer a distribution from a subject or global fallback.
6. Rebuild the Spring 2027 rankings cache once final imports finish. Verify raw DB matches,
   evidence-backed scores, data-quality findings, and `git` hygiene. Update `STATE.md` and an
   aggregate provenance ledger. Report any source-limited remainder explicitly.

## Stop conditions

- No export containing a cap warning is imported as complete.
- No row with a blank/suppressed grade bucket or mismatched `Total Grades` is coerced to zero.
- No pre-Spring-2025 term is newly imported.
- 100% coverage is claimed only if every current section's exact course key has sourced history.
  Otherwise completion means the allowed source range has been exhausted, with each remaining
  exact course key accounted for as unavailable, invalid, or unresolved.
