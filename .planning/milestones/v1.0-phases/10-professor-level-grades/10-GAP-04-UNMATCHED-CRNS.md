# GAP-04: why 1,500 graded CRNs are missing from the whole-term responses (diagnosis)

Date: 2026-10-01. Task: read-only diagnosis requested by the user ("revise-diagnose-missing-crns") after dry run 2 (10-ROLLOUT-EVIDENCE.md, commit 7c68e04). No code was changed, no USF request was made and the backfill CLI was not run. Every hosted database statement ran inside `SET TRANSACTION READ ONLY` (`transaction_read_only` confirmed `on`, always rolled back). This note holds aggregate counts only: no URLs, instructor names, row text or connection strings. Row-level working files stayed in the session scratchpad, outside the repo.

## Verdict

**Most likely cause (not yet proven for the 1,500 individually): the whole-term request is pinned to `campus=T`, and USF lists a large block of Tampa-credited sections under a different schedule campus label (`Off-campus - Tampa`), which that request never returns.** The grade source files the same sections under `0001 - Tampa Campus`, so they are in the grade table and cannot be found in a `campus=T` response. The 2026-09-28 feasibility pull that reported 8,661 of 8,662 grade rows matched used per-subject queries with **no campus filter** (P_CAMPUS blank), so it saw these rows; the dry run's `campus=T` whole-term request does not.

This is a fetch-scope problem (hypothesis H1 below), not a wrong guard and not a parse bug. The guard's definition is sound; the 2% limit was set against an expectation (near-full coverage) that came from the all-campus pull and was never re-tested against the `campus=T` request shape. Do **not** raise the limit. One new USF request would settle it (recommendation below).

## 1. What "unmatched" means and what the fraction is computed over

From `src/easy_a/schedule/backfill.py` (`select_backfill_rows`, `TermSelection`) and `backfill_cli.py`:

- `grade_crns = len(grade_keys)`: the number of **distinct CRNs that have a `grade_distributions` row in that term**, read by `load_grade_keys` with no campus, source or instructor filter.
- `unmatched_grade_crns`: grade CRNs whose CRN is **not among the CRNs of any fetched row**. It is computed against the fetched set before any campus, course or instructor filtering, so a CRN is "unmatched" only if it is wholly absent from the response.
- `unmatched_fraction = unmatched_grade_crns / grade_crns`; the guard trips above 2% (`DEFAULT_MAX_UNMATCHED_FRACTION = 0.02`, `backfill_cli.py` line 92).
- Every other outcome is a separate counter over fetched rows that did match a grade CRN (`non_tampa`, `grade_course_unattributed`, `course_key_mismatch`, `uncataloged`) and was 0 in all five terms (1 `staff_or_blank` in 202501). `non_tampa` is 0 by construction: the request is `campus=T`, so a non-Tampa row never arrives to be counted.

**The denominator is clean; it is not too coarse.** Read-only queries over the five terms:

| Check | Result |
|-------|--------|
| grade rows per term (202408 / 202501 / 202505 / 202508 / 202601) | 179 / 2,096 / 465 / 2,887 / 3,035 = 8,662 |
| distinct CRNs per term | identical to the row counts (one row per CRN, one source) |
| `campus_raw` | `0001 - Tampa Campus` on all 8,662 (no other campus, no NULL) |
| `source` | a single value (`usf_infocenter_grade_distribution_xlsx`) on all 8,662 |
| CRN form | 5 digits on all 8,662 |
| grade rows with no course (`course_id` NULL) | 0 |

So the denominator does not include other campuses, odd CRN shapes, unattributed rows or duplicate sources. Nothing in the definition would make the fraction wrong, other than the request not being able to return a class of rows that the grade table contains.

## 2. Can the unmatched set be rebuilt offline?

- **What-if JSON** (`10-WHATIF-DIFF.json`): per-term counts only. It does not list CRNs for the unmatched set, and the matched CRN sets were discarded after the run (the HTML is never kept; the dry run wrote no `failed-responses` file).
- **Database**: historical terms hold no `sections` rows, so the matched set cannot be read back.
- **Result**: the unmatched set is exactly recoverable for **one term only, 202505 (181 of 1,500)**, because its page survives in `failed-responses/202505.html` (parsed offline with the repo's own `parse_whole_term`: 2,175 of 2,175 rows, matching the dry run's `fetched_rows`; grade CRNs 465, matched 284, unmatched 181, exactly the reported numbers). For 202408, 202501, 202508 and 202601 (1,319 CRNs) the unmatched set cannot be recovered without a new USF request; only grade-side bounds are available (section 4).

## 3. The 202505 unmatched CRNs against the matched ones (181 vs 284)

All figures from the saved page and the grade table; no USF request.

| Measure | Unmatched (181) | Matched (284) |
|---------|----------------:|--------------:|
| Grade `section_suffix` `O` (schedule type "Other") | **113** | 4 |
| Suffix `C` / `L` / `I` / other | 44 / 22 / 2 / 0 | 157 / 93 / 11 / 23 |
| Section number 0xx / 7xx / 4xx / 1xx-3xx / 9xx | 102 / **47** / 17 / 11 / 4 | 265 / 3 / 0 / 0 / 16 |
| Total grades, quartiles (25% / median / 75% / max) | 24 / 25 / 50 / 399 | 16 / 23 / 39 / 288 |
| Sum of grades | 9,539 | 8,849 |
| Course key also has a matched CRN | 85 (47%) | n/a |
| Course key present on the page (any CRN) | 101 (56%) | n/a |
| Subject absent from the page entirely | 24 CRNs in 11 subjects (SPN, FRE, SOP, PSB and 7 others) | 0 |
| CRN range | 50008 to 55432 | 50004 to 55335 |

Reading:

- The unmatched CRNs fall in the same CRN range and numbering as the matched ones, so there is no term-code or CRN-form mismatch.
- They are dominated by suffix `O` and by 7xx sections; matched suffix-`O` rows (4) correspond one for one with schedule type "Other" (4 of 4), so the `O` suffix is the schedule's "Other" type. In the matched set, each grade suffix maps to exactly one schedule section type (C Class Lecture, L Laboratory, D Discussion, I Internship, Z Directed Individual Study, S Supervised Teaching, R Supervised Research, O Other).
- They cluster by course, not by position in the response: top course keys are ENC 1102 (14), SPC 2608 (11), ENC 3246 (10), PHY 2054L (10), ENC 1101 (6), AMH 2020 (6), ENC 2210 (5), PHY 2053L (5), POS 2041 (5), PHY 2049L (4), REL 3850 (4), SPN 1121 (4). 85 distinct course keys carry the 181 CRNs. In the page, ENC has 9 rows (all Class Lecture, section prefixes 0 and 9) against 42 graded ENC CRNs.
- They are larger on average than the matched sections (mean about 53 against 31 grades).
- They are not a tail truncation: unmatched CRNs sit in subjects that appear early in the page (ENC) as well as late ones, and matched rows come from every part of the response (the page is not ordered by subject).

Direct offline tests on the saved 202505 page (counts only):

| Test | Result |
|------|--------|
| unmatched CRN present as a table-row CRN | 0 of 181 |
| unmatched CRN present anywhere in the raw HTML as a whole token | 1 of 181 (it is a CRN quoted inside a free-text section note of another row, not a row) |
| same (subject, course, section number) present under a different CRN (renumbered or term-shifted) | 0 of 181 |
| campus labels on the page | `Tampa` on all 2,175 rows; the string "Off-campus" does not occur |
| sessions on the page | Summer A, B, C, D, Intersession, Alternative Calendar Term, Extended Alternative Calendar, College of Medicine and Full Term all present (no sub-term is missing) |
| statuses on the page | A, U, H, C, R all present (cancelled and held sections are listed, so status is not filtering) |
| parse | 2,175 of 2,175 data rows parsed; every matched row has the grade row's course key and section number (284 of 284) |

So these CRNs are neither hidden in another shape, term or session on the page nor lost by the parser: they are simply not in a `campus=T` response.

## 4. Grade-side bounds for the other four terms

The grade `O` suffix equals the schedule type "Other". The dry run reports how many "Other" sections it wrote per term, so the `O` grade rows that could not have matched are at least `O` minus matched "Other":

| Term | grade CRNs | unmatched (reported) | grade `O` rows | matched "Other" (histogram) | `O` unmatched at least |
|------|-----------:|---------------------:|---------------:|----------------------------:|-----------------------:|
| 202408 | 179 | 18 | 11 | 0 | 11 |
| 202501 | 2,096 | 252 | 233 | 45 | 188 |
| 202505 | 465 | 181 | 117 | 4 | 113 (exact) |
| 202508 | 2,887 | 526 | 319 | 50 | 269 |
| 202601 | 3,035 | 523 | 345 | 59 | 286 |
| Total | 8,662 | 1,500 | 1,025 | 158 | **867 (58% of 1,500)** |

(The total of 1,025 `O` rows agrees with the 2026-09-28 session's own read of the grade table.) The remaining 633 unmatched are other suffixes (C, L, I): in 202505 these are 68 of 181, including 22 lab sections. That residue is not explained by "Other" type alone; it is consistent with the same label split only if off-campus Tampa also holds classroom and lab sections, which cannot be checked offline.

## 5. Evidence from the 2026-09-28 pull and the code

- `.planning/research/instructor-grade-feasibility-2026-09-28.md` (and the plan that followed) say "27,273 historical sections pulled" by "595 subject x term queries" and "8,661 / 8,662 grade rows matched". The session transcript that produced those numbers (a local Claude session log, not in the repo) shows the pull ran `ScheduleSearchQuery(term=term, subject=subj)` with **no campus**, so P_CAMPUS was blank, and its join matched by (term, CRN) only, with campus recorded but never used to filter.
- The same session printed a campus count for one 8-subject, one-term sample (202408, 1,728 rows): `Tampa` 1,236; **`Off-campus - Tampa` 178**; `St. Petersburg` 167; `Off-campus - Sarasota-Manatee` 68; `Sarasota-Manatee` 50; `Off-campus - St. Petersburg` 29. One sample row of the off-campus Tampa block was type "Other", delivery AD (all online), session Full Term. 178 of 1,728 rows is 10.3%; the dry run's 202408 unmatched fraction is 10.06% (18 of 179). The two figures are of different populations (all rows against graded CRNs) and are circumstantial, not a proof.
- The whole-term request is `campus=T` by code (`client.py` `search_term(term, campus="T")`, `build_whole_term_form_data`, called with the default from `fetch.py` `fetch_whole_term`) and by policy (PROJECT.md D-22(a): "one whole-term Tampa ... request, empty subject, `campus=T`"). D-22(e) (the five-term backfill) does not itself restate the campus.
- The selection step has a second, independent campus gate: `same_campus(row.campus, "Tampa")` is an exact case-folded comparison (`common/campus.py`), so even if an all-campus response were fetched, rows labelled `Off-campus - Tampa` would be counted as `non_tampa` and skipped. The plan text (10-02-PLAN: "whose campus is Tampa") and the Sprint 5 cleanup (PROJECT.md, Tampa-only correction: any nonblank campus other than Tampa was deleted) both treat the label as exact.
- The whole-term request for the **live** term is also `campus=T`. The live term in the database is therefore all `Tampa` (3,815 of 3,815 sections), and it contains 78 "Other" sections out of about 3,700 (2%), against a grade table where suffix `O` is 12% of rows (1,025 of 8,662). The same blind spot probably exists for Spring 2027 (see "Side effect").

## 6. What the project documents expected (item 4)

- D-06: write only sections whose term+CRN has a grade row, "(~8.7k rows rather than the ~27k pulled)". D-07: "post-run re-measure must match the 2026-09-28 report numbers". The runbook states unmatched CRNs are "graded CRNs USF no longer lists" and says not to raise the limit without understanding why. Plan 10-02 introduced the 2% limit as a defensive sanity bound.
- Nowhere do the planning documents say that only a subset of grade CRNs was expected to match, nor derive 2% from another population. The expectation was near-complete coverage, taken from the all-campus pull (0.01%: 1 in 8,662, the one "Staff" row). The 2% therefore protects against "USF returned a broken or partial page"; it did what it was designed to do, and it surfaced a coverage assumption that had not been tested for the `campus=T` request shape.

## 7. Ranked hypotheses

| # | Hypothesis | Evidence for | Evidence against / still open | Verdict |
|---|------------|--------------|-------------------------------|---------|
| H1 | The `campus=T` request excludes Tampa-credited sections labelled `Off-campus - Tampa` (and the code's exact campus gate would skip them anyway). | The 09-28 pull had no campus filter and matched all but 0 to 1 of the same CRNs; that pull saw a 10.3% `Off-campus - Tampa` block in one sample (10.06% unmatched in the same term); the saved 202505 page has zero such rows; unmatched CRNs are dominated by type "Other" (113 of 181, 867 of 1,500 as a lower bound), 7xx and larger (online-type) sections; no unmatched CRN is on the page in any shape; grade table files all of them under Tampa. | The off-campus label of the 1,500 themselves was never observed (no saved all-campus response; the 09-28 file was not kept); 633 non-Other CRNs (C/L/I, including labs) are not explained by type and need the label check; 10.3% was one 8-subject term. | **Most likely; confirm with one request** |
| H2 | USF truncates or caps the whole-term response (every page ends in a USF error tail), so later rows are missing. | The error tail is present on the saved 202505 page; the page ends mid-structure. | Matched and unmatched are interleaved across the page order; the unmatched are attribute-clustered (type, course, section range), not position-clustered; the live term's whole-term response covered all but about 3% of the stored sections on 09-28; 202505's page size (2.3 MB for 2,175 rows) is consistent with the other terms' bytes per row (about 1.05 to 1.07 KB). | Unlikely as the main cause; cannot be fully excluded for 202408/501/508/601 without their pages |
| H3 | Sections dissolved, merged or purged from the public schedule after the term. | Normal for removed sections (live term lost about 90 in six days). | The same CRNs were found by the unfiltered per-subject pull three days earlier (8,661 of 8,662); graded sections cannot be unenrolled. | Rejected |
| H4 | The guard's denominator/numerator is wrong or too coarse (other campuses, blank/staff, study abroad, CRN form, term code, summer sub-terms). | none | All 8,662 grade rows are `0001 - Tampa Campus`, 5-digit CRNs, one source, all attributed; the 202505 page includes every summer session; the counters for skipped rows are 0. | Rejected |
| H5 | A parse or CRN-matching bug. | none | 2,175 of 2,175 rows parsed; 284 of 284 matched rows agree on course key and section number; no unmatched CRN occurs as a row CRN or under another CRN. | Rejected (for 202505; the same code path ran for all five terms) |

## 8. Recommendation

The closest of the four options is **(c), a fixable fetch/scope problem, confirmed first through (d) a single, minimal USF request.** It is not (a) (the guard's definition is correct) and not (b) (the rows are not genuinely absent from USF, so a raised limit would hide a coverage hole and also leave 10 to 39% of graded sections without an instructor, i.e. a worse product and the failed re-measure).

**Step 1, the single request that settles it** (needs the user's go-ahead; it is a narrow request under D-09, not a whole-term one): one POST for term **202505**, subject **ENC**, **campus blank** (all campuses), parsed offline into counts only: (i) how many of the 42 graded ENC CRNs of 202505 appear, (ii) what campus label each carries, (iii) how many rows carry `Off-campus - Tampa`. Interpretation:
  - the 37 unmatched `O` ENC CRNs appear and carry `Off-campus - Tampa`: H1 confirmed (a campus label gap);
  - they appear but carry `Tampa`: the whole-term `campus=T` response is capped or incomplete (H2), and the next step is a response-completeness check, not a campus change;
  - they do not appear: the rows are no longer served, and the 09-28 match would have to be re-examined.

**Step 2, if H1 is confirmed** (not implemented here, a user decision on policy is required because it changes D-22 and the Tampa-only rule):
1. Backfill-only change: let the one-off backfill request the five terms with a blank campus (the live sync stays on `campus=T`, since D-22(a) pins it), and widen the selection campus gate from exactly "Tampa" to an explicit allow-list of the two labels the grade source files under Tampa (`Tampa` and `Off-campus - Tampa`), so `St. Petersburg`, `Sarasota-Manatee` and their off-campus variants still count as `non_tampa` and are not written.
2. Keep the 2% limit unchanged. Under the corrected request the expected unmatched count is about 0 of 8,662 (the 09-28 reference: all 8,662 found), so the correct fraction would be 0.0% to 0.01%, far under 2%.
3. Five fresh whole-term requests are needed (the five dry-run responses were not kept), under D-22(e), and a new dry run must reach `guard_failures: []` and `pairs_match_reference` PASS before `--apply`.

If the user prefers not to touch the request policy, the only no-request option is to proceed with the 7,162 matched sections and accept a smaller join (2,788 pairs against 3,216); that needs an explicit, evidence-based written decision and is not recommended because the missing 1,500 are concentrated in online "Other" sections of large courses (ENC 1101/1102, SPC 2608).

## Side effect for the live product (separate decision, flag only)

If H1 holds, the live sync (`campus=T`) and the Sprint 5 Tampa-only cleanup also exclude the `Off-campus - Tampa` block for Spring 2027, about 10% of rows in the one sample. That is a coverage statement about the shipped product ("every number ... real", D-06/D-07: absent evidence must be reported as absent), not a Phase 10 backfill problem; it should be queued as its own question after the single request above answers whether those sections really are Tampa-credited.

## Method record

- Code read: `src/easy_a/schedule/backfill.py`, `backfill_cli.py` (`_run`, `_guard_failures`), `src/easy_a/sync/fetch.py`, `src/easy_a/schedule/client.py`, `src/easy_a/common/campus.py`, `src/easy_a/grades/parser.py`, `src/easy_a/models/core.py`.
- Documents read: AGENTS.md, PROJECT.md (D-06 to D-09, D-22, the Tampa-only correction), the phase 10 CONTEXT, PLAN 10-02, 10-06, 10-07, ROLLOUT-EVIDENCE, WHATIF-DIFF, the runbook and both 2026-09-28 research files; the earlier session log for the 09-28 pull's query shape and the campus count sample.
- Hosted queries (all READ ONLY): grade rows by term, campus, source, CRN length; the grade rows of the five terms (CRN, course key, section number, suffix, totals); 202701 section campus and type distributions. Nothing was written.
- Offline: `parse_whole_term` over the git-ignored saved 202505 page (never quoted or committed).
- Not done, by instruction: any USF request, any backfill CLI run, any code change.

## Confirmation probe (2026-10-01)

One USF request, authorized by the user ("confirm-with-one-request"): term 202505, subject ENC, campus blank, made with the project's `StaffScheduleClient.search(ScheduleSearchQuery(...))` and `parse_schedule_html` (default user agent, single request, no retry, no backfill CLI). The grade side was read in a `SET TRANSACTION READ ONLY` transaction. The response was kept only in the session scratchpad (outside the repo). Counts only; no URLs, names or row text.

| Measure | Result |
|---------|-------:|
| Rows in the response | 77 |
| Campus label `Off-campus - Tampa` | 46 |
| Campus label `Tampa` | 9 |
| Campus label `Off-campus - Sarasota-Manatee` | 14 |
| Campus label `Off-campus - St. Petersburg` | 4 |
| Campus label `St. Petersburg` | 4 |
| Graded ENC CRNs of 202505 present in the response | 42 of 42 |
| ...labelled `Tampa` | 5 |
| ...labelled `Off-campus - Tampa` | 37 |
| Graded ENC CRNs present in the saved whole-term `campus=T` page | 5 of 42 |
| Whole-term-unmatched ENC grade CRNs | 37 |
| ...present in this response, labelled `Off-campus - Tampa` | 37 |
| ...present, labelled `Tampa` | 0 |
| ...absent | 0 |

The suffix-`O` question: all 37 unmatched ENC CRNs have grade suffix `O` and all 37 are labelled `Off-campus - Tampa`; every `Off-campus - Tampa` row in the response (46 of 46) has schedule type "Other"; the 5 matched graded CRNs are the `Tampa`-labelled class lectures.

**Verdict: H1 confirmed for ENC in 202505.** Every unmatched graded ENC CRN appears under the label `Off-campus - Tampa` in an all-campus response, none under `Tampa` (so no sign of the `campus=T` response being incomplete, H2) and none is absent. The 5 CRNs that matched the whole-term page are exactly the `Tampa`-labelled ones.

Limits of this probe: one subject in one term, and every unmatched ENC CRN is suffix `O`, so the non-`O` residue noted in section 4 (C/L/I, including labs; 68 of 181 in 202505) is still not checked by this evidence. The 14 `Off-campus - Sarasota-Manatee` rows and the St. Petersburg rows are not graded Tampa CRNs and would remain `non_tampa` under the Step 2 allow-list.
