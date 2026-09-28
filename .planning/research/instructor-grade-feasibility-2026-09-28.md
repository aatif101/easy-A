# Instructor-level grade feasibility — investigation (2026-09-28)

Exploratory data analysis, not implementation. The user's brief made MVP-1 constraints negotiable
**for this investigation only**; the 595-query historical schedule pull below ran under that
brief. Ongoing request policy is D-22 in `PROJECT.md`.

**Method.** Hosted Supabase queried read-only (`BEGIN TRANSACTION READ ONLY … ROLLBACK`); nothing
written; no production file changed. Past-term instructors pulled from the public USF
StaffScheduleSearch with the repo's own `StaffScheduleClient`/`parse_schedule_html` (595
subject×term queries, ~1 req/s, 0 failures). `effective_n = min(A–F count, total_grades)` as in
`analytics/grades.py` (recency off). A% = A / (A–F).

## Headline

`instructor_course` can never activate in production today, at **any** threshold: the join
`_fetch_instructor_course_grade_observations` needs a `Section` row for the grade row's term+CRN,
and none exist for grade terms.

| Terms | grade rows | `sections` | `section_instructors` |
|---|---|---|---|
| 202408, 202501, 202505, 202508, 202601 | 8,662 | 0 | 0 |
| 202701 | 0 | 3,783 | 4,226 |

Live `section_rankings`: 3,422 `course` / 311 `subject` / 50 `global` / **0 `instructor_course`**.

The data is recoverable: 27,273 historical sections pulled from USF; **8,661 / 8,662** grade rows
matched a named instructor by term+CRN (1 was "Staff"); 0 course mismatches.

## 1. Pair histogram (after historical instructor join)

3,216 (instructor, course) pairs · 1,796 instructors · 1,117 courses.

| effective_n ≥ | 60 | 30 | 15 | 5 | 1 |
|---|---|---|---|---|---|
| pairs | 1,329 | 2,178 | 2,829 | 3,208 | 3,216 |

1,439 pairs span ≥ 2 terms; 1,308 have n ≥ 30 and ≥ 2 terms. Term span: 1 term 1,777 · 2 965 ·
3 359 · 4 110 · 5 5.

## 2. Instructor identity quality

- Spring 2027 (observed 2026-09-20..22): 1,491 named (39%), 2,292 "Staff" (61%), 0 blank,
  0 multi-name; 685 distinct names. Whole subjects 100% Staff at that time: CIS, CNT, CHM, PHY,
  MAC, EEL, SPC, IDH, MVO, ART.
- Historical terms: effectively 100% named on graded sections.
- Live re-check 2026-09-28 (6 days later): 48 Staff→named, 23 named→other name, 13 named→Staff,
  92 stored sections no longer in the live schedule, 7 new CRNs in tracked courses.

## 3. Case studies (A%, n, shrunk toward course mean with k = 30)

| Course (course A%) | Instructors |
|---|---|
| CNT 4419 Secure Coding (30.5) | X. Ou 175, 40.0 (38.6) · J. Ligatti 203, 25.1 (25.8) · Y. Liu 109, 28.4 · A. Ami 44, 22.7 |
| PSY 2012 (64.8) | J. Gillespie 351, 77.5 · M. Wilkerson 216, 82.4 · E. Sykes 342, 60.5 · A. Kah 172, 42.4 |
| ENC 1101 (70.6), 62 instructors | P. Fields 171, 83.0 · C. Doubler 164, 53.7 · most 65–77 |
| MAC 1105 (47.9) | V. Grupchev 1,378, 48.5 · L. Avazpour 1,359, 45.0 · I. Rothstein 389, 58.6 |
| COP 4530 (55.2) | V. Korzhova 295, 37.6 · F. Kaleemunnisa 88, 84.1 · D. Tahmoush 88, 76.1 |
| CIS 4622 (55.8) | M. Alam 161, 73.9 · M. Pazos Revilla 133, 49.6 · S. Fang 41, 12.2 |

Single-instructor (no added value): COT 3100 (J. Theado 603/603), COP 3514 (J. Wang 518/632).

Across 562 courses with ≥ 2 instructors: median true between-instructor SD of A% = **8.9 pp**
(rms 13.0). Of 2,373 instructor-vs-rest-of-course tests (n ≥ 15 each side), 44% have |z| > 2 and
54% differ by ≥ 10 pp.

## 4. Spring 2027 reach after backfill

| Rule | sections |
|---|---|
| today | 0 |
| n ≥ 60 (current setting) | 582 |
| **n ≥ 30 (recommended)** | **751** (433 pairs, 321 courses) |
| n ≥ 30 and ≥ 2 terms | 629 |
| n ≥ 15 | 859 |

Threshold reasoning: at n = 30 the binomial SE of an A-rate (~9 pp) ≈ the true 8.9 pp spread, so
signal ≈ noise; empirical-Bayes implies a prior strength k ≈ 15–30. The current setting is doubly
conservative (prior strength 60 plus a gate at 60). Binding constraint is Staff, not sample size:
386 more named sections are instructors new to that course in the window.

## 5. Landmines

1. Co-teaching is invisible — the source lists one instructor per CRN.
2. Names are initial + surname: 242 of 3,019 historical names span > 1 college; 261 surnames shared
   by different initials; e.g. "X. Liu" in EAS/EML and HSC. Low risk within one course; a
   cross-course professor view needs name + college.
3. Labs: 131 of the 751 qualifying sections are Laboratory, often rotating TAs.
4. Modality/size confounds (e.g. one 216-student PSY 2012 section).
5. Cross-listing: 0 course mismatches by CRN.
6. Thin history: Fall 2024 covers 8 subjects only; 55% of pairs are single-term.

## Operational finding (drives Phase 9 live sync)

A StaffScheduleSearch POST with empty subject and `campus=T` for 202701 returned all **6,663 Tampa
rows / 231 subjects in 9.2 s (7.1 MB)** — a full refresh is one request.
