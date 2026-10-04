# Phase 05 — API Coverage Decision

No external API integration: the USF InfoCenter grade-distribution export is a Codex-owned,
out-of-band, authenticated, file-based data source. This phase loads an already-produced XLSX
into hosted Supabase through existing local CLI tooling (`scripts/refresh_data.py`,
`scripts/ingest_grades.py`) and builds no API/SDK/service client. Sourcing the export is external
to this codebase (D-08/D-09 — bounded, narrow, approved USF access; never scraped). There is no
capability matrix to fill because there is no client library or API surface introduced.
