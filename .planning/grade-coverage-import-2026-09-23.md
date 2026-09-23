# Tampa grade coverage import — 2026-09-23

USF InfoCenter Grade Distribution (SGDIS), Tampa Campus, approved use. XLSX source files were
downloaded outside Git and parsed with fail-closed grade-count validation. Each imported row has
`source=usf_infocenter_grade_distribution_xlsx`, the original workbook SHA-256, and a historical
term/CRN/source uniqueness key. Only courses represented by Spring 2027 Tampa sections were
imported. Source files and CRN-level rows are not stored in this repository.

The user set **Spring 2025 as the oldest term for new coverage work**. Summer 2026 was queried
for all three colleges and returned `NO ROWS RETURNED`. The 179 pre-existing Fall 2024 pilot rows
remain in the database; no new pre-Spring-2025 rows were imported.

| Historical term | Muma report rows / imported | Engineering report rows / imported | Arts and Sciences report rows / imported | New rows |
|---|---:|---:|---:|---:|
| Spring 2026 (`202601`) | 416 / 235 | 317 / 238 | 2,031 / 1,647 | 2,120 |
| Fall 2025 (`202508`) | 418 / 216 | 352 / 197 | 2,125 / 1,614 | 2,027 |
| Summer 2025 (`202505`) | 94 / 31 | 77 / 58 | 497 / 376 | 465 |
| Spring 2025 (`202501`) | 396 / 205 | 443 / 304 | 2,054 / 1,587 | 2,096 |
| **Total** | **1,324 / 687** | **1,189 / 797** | **6,707 / 5,224** | **6,708** |

Muma and Engineering used complete uncapped college exports. Arts and Sciences used 23 nonempty
department exports for each spring/fall term; its Summer 2025 report was partitioned by
`All EXCEPT Distance Learning` and `ONLY Distance Learning`. Every partition was below the cap,
had unique CRNs, and the capped college preview's rows and counts were all present and identical
in the partition union. `CAS JOURNALISM AND DIGITAL COMMUNICATION` returned no rows in all three
spring/fall terms. Report run IDs and database run IDs:

| Term | Muma InfoCenter / DB run | Engineering InfoCenter / DB run | Arts and Sciences InfoCenter / DB runs |
|---|---|---|---|
| Spring 2026 | 863966 / 13 | 863967 / 14 | 863969–863993 / 15–37 (863979 no rows; 863972 was an unused broad report) |
| Fall 2025 | 863998 / 38 | 863999 / 39 | 864001–864024 / 40–62 (864010 no rows) |
| Summer 2025 | 864028 / 63 | 864029 / 64 | 864031–864032 / 65–66 |
| Spring 2025 | 864034 / 67 | 864035 / 68 | 864037–864060 / 69–91 (864046 no rows) |

The Spring 2026 Arts and Sciences report-ID range includes an unused broad query generated while
the InfoCenter form reset its filters; it was not downloaded or imported. The actual workbook
department labels, terms, campus, row totals, and source hashes were checked before import.

## Departments with source rows in the requested colleges

**Muma (9):** DBA Program; Deans Office; Graduate Advising; Kate Tiedemann School of Business
and Finance; Lynn Pippenger School of Accountancy; Marketing – Sport and Entertainment Management;
Marketing Center for Entrepreneurship; School of Information Systems and Management; School of
Marketing and Innovation. The college-wide exports cover all departments that returned rows.

**Engineering (8):** Chemical, Biological, and Materials Engineering; Civil and Environmental
Engineering; Computer Science and Engineering; Deans Office; Electrical Engineering; Industrial
and Management Systems; Mechanical Engineering; Medical Engineering. The college-wide exports
cover all departments that returned rows.

**Arts and Sciences (23 with rows):** Anthropology; Chemistry; Communication; Deans Office;
Economics; English; History; Humanities and Cultural Studies; Integrative Biology; Mathematics and
Statistics; Molecular Biosciences; Philosophy; Physics; Psychology; Religious Studies; School of
Geosciences; School of Information; School of Interdisciplinary Global Studies; School of Public
Affairs; Sociology and Interdisciplinary Social Sciences; Women's, Gender, and Sexuality Studies;
World Languages; Zimmerman School of Advertising and Mass Communications.

`CAS JOURNALISM AND DIGITAL COMMUNICATION` was checked and had no source rows. A department having
source rows does not mean every current course in that department has history; InfoCenter omits
courses with fewer than five enrolled students, and we imported only exact course-code matches.

## Live result after final Spring 2027 cache refresh

- 3,783 searchable Tampa sections / 1,401 represented courses.
- 2,571 sections / 793 courses have an own-course historical grade-row match. **1,212 sections /
  608 courses remain without one.**
- 2,362 sections / 767 courses have own-course scoring evidence with `effective_n > 0`.
- 402 sections use a subject fallback; 810 use a global fallback. These are not own-course grade
  distributions. Data quality: 0 errors; 1,566 low-confidence warnings; 810 no-history info items.
- Hosted Supabase holds 6,887 total grade rows: 6,708 new plus 179 earlier pilot rows.

The database's current `sections` table does not carry college or department. It therefore cannot
reliably assign the 1,212 unmatched sections to a remaining department. Colleges outside Muma,
Engineering, and Arts and Sciences have not been processed in this import run.
