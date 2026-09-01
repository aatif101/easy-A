# Narrow Live Source Drift Check — 2026-09-01

Scope: Spring 2027 (`202701`), Tampa (`T`), `MAC 1105` and `ENC 1101` only.
This check made two narrow public Staff Schedule searches and two course searches
in the public Simple Syllabus library. It did not ingest, crawl, or retain source
HTML, and it does not change signal scoring.

## Schedule observations

- `MAC 1105`: five Tampa sections are currently listed. All instructors remain
  `Staff`. Against the checked-in `schedule_current.html` baseline, CRN `13173`
  remains capacity/enrollment/seats `135/0/135`; CRN `19410` changed from
  `190/207/-17` to `135/0/135`. The live note for CRN `19410` now explicitly says
  video lectures are on Canvas, weekly SMART Lab time is required, and quizzes and
  exams are in person in the SMART Lab.
- `ENC 1101`: 41 Tampa sections are currently listed, all with instructor `Staff`
  and capacity/enrollment/seats `19/0/19`. The repository has no checked-in Spring
  2027 ENC schedule baseline, so instructor and seat *change* cannot be determined;
  these values are current observations only.

## Syllabus observations

- No Spring 2027 `MAC 1105` syllabus appeared in the public Simple Syllabus library.
- No Spring 2027 `ENC 1101` syllabus appeared in the public Simple Syllabus library.
- Matching public library results for both courses were Fall 2026 documents only.

Result: instructor assignments did not change for the comparable MAC rows; a seat
snapshot changed for CRN `19410`; and no new current-term syllabus was found for
either requested course. ENC change status remains unknown because no prior ENC
baseline exists in the repository.
