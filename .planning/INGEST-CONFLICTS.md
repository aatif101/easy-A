## Conflict Detection Report

Operation: ingest. Mode: new. Precedence: ADR > SPEC > PRD > DOC, with explicit
per-doc ranks 0/1/2/3 supplied by docs/gsd-mvp-manifest.yaml.

Docs consumed: 4 (1 ADR locked, 1 SPEC, 1 PRD, 1 DOC). No UNKNOWN classifications.
No low-confidence classifications. Only one locked document exists, so no
LOCKED-vs-LOCKED contradiction is possible in this set. Mode is `new`, so there is no
existing CONTEXT.md decision block to contradict.

### BLOCKERS (0)

None.

### WARNINGS (3)

Resolution update (2026-09-08): OQ-01 is resolved by explicit user confirmation: implementation
stays in worktrees off `origin/main`, with Phase 1 planning on the onboarding branch in the same
PR. Leave local `main` and untracked files alone until developer 1 merges. Fresh fetch and ancestry
checks confirmed the baseline; see PROJECT.md. The original ingest findings below are retained
as history. The first warning no longer blocks planning; its protection of local work still applies.

[WARNING] Stale local main with untracked work is still live, contrary to the ingest premise
  Found: docs/final-mvp-plan.md section 2 states the user's local `main` was `d880d3c2bd31158c2392725e5c203ac92b2088fa` with an untracked `web/` directory, and instructs "Do not treat that older local checkout as the current product, overwrite local work, or copy its built frontend over source on current main." docs/gsd-core-mvp-prompt.md repeats this as locked decision ADR-13. Repository inspection during synthesis found `refs/heads/main` is still `d880d3c2bd31158c2392725e5c203ac92b2088fa`, the worktree `C:/Users/smati/VS Code Projects/easy-A` is checked out on `main` at that commit, `git status` there reports `?? web/`, and `web/` is untracked at `d880d3c` but tracked at `06634490de5c765bdc7b55e4f439476b0e4fa0f7`.
  Impact: The ingest task described this as known staleness that was already resolved, and suggested INFO severity. That premise does not hold. Local `main` has not advanced and the untracked `web/` still exists. Any later phase that assumes the condition is resolved, or that checks out or merges onto local `main`, can destroy untracked user work. The plan section 2 warning is current guidance, not a historical note.
  → Do not downgrade this to INFO. Before Phase 1 implementation, either fast-forward local `main` to `origin/main` after preserving the untracked `web/` directory and the untracked handoff docs, or explicitly confirm that all implementation stays in a worktree descended from `06634490` (this ingest ran in `.claude/worktrees/gsd-onboard-774626` at `894da473`, which is such a descendant). Record the chosen baseline in PROJECT.md.

[WARNING] Live evidence shows no named instructors in the sampled launch scope
  Found: docs/live-source-drift-2026-09-01.md reports that all five observed Spring 2027 Tampa `MAC 1105` sections and all 41 observed `ENC 1101` sections have instructor `Staff`. docs/final-mvp-plan.md requires REQ-RMP-01 to display a verified RMP link "for the applicable instructor", requires Phase 3 to "Curate actual unambiguous launch examples", and sets a 60 A-F outcome threshold before same-professor evidence may be preferred. Its Phase 3 exit criterion is that "a verified profile opens the correct professor/university". docs/gsd-core-mvp-prompt.md carries the same requirement as locked scope item 6.
  Impact: If the declared launch scope resembles the sampled scope, verified RMP links and professor-specific grade evidence could have near-zero real coverage at launch, and Phase 3's exit criterion may be unprovable with real data. The DOC is lowest precedence and cannot override the PRD or ADR requirement, so the requirement stands - but the coverage risk is a Phase 1 scope decision, not a Phase 3 discovery. The drift check sampled only two courses and does not establish a campus-wide pattern.
  → During Phase 1 launch-coverage manifest work (REQ-LAUNCH-01), inventory how many sections in the intended launch scope have named instructors. Then either choose launch subjects that include named instructors, or explicitly accept course-only evidence plus "Verified RMP link unavailable" as the launch-normal state and restate the Phase 3 exit criterion accordingly. Do not silently narrow scope to whichever courses happen to have RMP matches.

[WARNING] No current-term syllabus found for either sampled course
  Found: docs/live-source-drift-2026-09-01.md reports no Spring 2027 syllabus in the public Simple Syllabus library for `MAC 1105` or `ENC 1101`, with matching public results being Fall 2026 documents only. docs/final-mvp-plan.md REQ-POLICY-01 requires chips to keep source term and scope and requires the "current syllabus to supported schedule note to historical same instructor/course to historical same course" precedence chain. docs/final-mvp-ui-spec.md section 6 specifies the "No current syllabus" state as "Clearly dated historical source if supported, otherwise no policy information."
  Impact: In the sampled scope the current-syllabus branch of the precedence chain yields nothing, so the historical-source path and the "avoid implying historical policy is current" labeling become the primary rendered path rather than a fallback. Building and testing the current-syllabus path first would leave the actual launch behavior least exercised.
  → Confirm during Phase 1 whether current-term syllabus availability is generally this thin for the declared launch term. If so, treat the historical-source labeling path and the "syllabus link exists but no chip extracted" state as primary acceptance cases for Phase 3, not edge cases.

### INFO (10)

[INFO] Cross-reference graph contains bidirectional companion references
  Found: The cross_refs graph has two 2-cycles - docs/final-mvp-plan.md and docs/final-mvp-ui-spec.md reference each other, and docs/final-mvp-plan.md and docs/gsd-core-mvp-prompt.md reference each other. Traversal depth is 2, far under the 50 cap.
  Note: These are companion "see also" references between documents in one declared handoff set, not derivation cycles - no document defers the content of a decision to another document that defers back. docs/gsd-mvp-manifest.yaml assigns explicit precedence integers 0/1/2/3, a strict total order over all four docs, so extraction order is deterministic and terminating. Synthesis proceeded on the full set rather than blocking. This is a judgment call: a strict literal reading of the cycle rule would have made this a BLOCKER and produced no intel at all. If you want the strict behavior, re-run with the cross-references removed from the source documents or supply a manifest that breaks the reciprocal links.

[INFO] Auto-resolved: ADR beats PRD on subject-level history
  Found: docs/gsd-core-mvp-prompt.md locked rules state "Remove subject/global displayed-score fallbacks" and "A prior may adjust a real eligible sample; it cannot stand in for this course's history." docs/final-mvp-plan.md section 3 nonetheless describes a reference fallback chain that reaches "other courses in the subject, then the eligible institutional reference corpus."
  Note: These are not actually contradictory - the PRD chain supplies `mu`, the prior mean used inside the shrinkage formula, while the ADR forbids a subject or global value becoming a displayed score. Because the wording invites conflation, the ADR governs by precedence and the resolution is recorded in constraints.md CON-CALC-02: subject-level and corpus-level data may supply `mu` only, never a displayed score, and when no measured reference qualifies the adjusted score is unavailable with reason "Reference data unavailable" rather than falling back to 0.75 or any other hard-coded mean.

[INFO] Two distinct 60-outcome thresholds must not be collapsed
  Found: docs/final-mvp-plan.md section 3 defines two separate 60-outcome rules - "Prefer same-professor/same-course evidence only after conservative identity resolution and at least 60 A-F outcomes" and "Require at least 60 eligible A-F reference outcomes for a reference mean." docs/gsd-core-mvp-prompt.md DEFAULTS compresses these into a single phrase, "a 60-outcome professor-history threshold", and names the reference requirement only as "empirical reference data".
  Note: The ADR summary is lossy, not contradictory. Both thresholds are preserved separately in requirements.md REQ-EVID-02 and constraints.md CON-CALC-02. Downstream planning must keep them as two independently testable rules; the evidence-strength label boundaries (Limited under 60, Moderate 60-179, Strong 180 or more) are a third, display-only use of 60 and must not be merged with either.

[INFO] PRD baseline claim about the current scoring code verified as accurate
  Found: docs/final-mvp-plan.md section 2 states that with no grade history the default grade prior is 0.75 and the withdrawal prior is 0.10, and that the current composite can therefore produce 7.8/10 without course evidence. Direct inspection of `src/easy_a/analytics/scoring.py` at the ingest revision confirms `DEFAULT_GRADE_WEIGHT = 0.80`, `DEFAULT_NON_WITHDRAWAL_WEIGHT = 0.20`, `DEFAULT_GLOBAL_GRADE_FAVORABILITY_PRIOR = 0.75` and `DEFAULT_GLOBAL_WITHDRAWAL_RATE_PRIOR = 0.10`.
  Note: Locked decision ADR-02 and requirement REQ-EVID-02 are grounded in code that is still present. No conflict; recorded so the roadmapper can treat this as verified rather than as an unconfirmed document claim.

[INFO] Baseline test-count claim does not match the codebase map
  Found: docs/final-mvp-plan.md section 2 records "166 Python tests passed; 19 frontend tests passed" at commit `06634490`. `.planning/codebase/TESTING.md` records the Python suite as "~154 tests".
  Note: The codebase map figure is approximate and was measured at a different revision (`894da473`, a descendant of the audited commit that adds planning content). The discrepancy is small and does not affect any requirement, but docs/gsd-core-mvp-prompt.md locks "Preserve the existing passing baseline", so the exact number matters as a regression reference. The plan's own Phase 1 exit criterion already requires "baseline checks recorded" - resolve the true count there rather than trusting either figure.

[INFO] Negative seat values in the source are real, not a parsing artifact
  Found: docs/live-source-drift-2026-09-01.md records CRN `19410` changing from capacity/enrollment/seats `190/207/-17` to `135/0/135`. docs/final-mvp-plan.md section 5 specifies that valid negative remaining seats classify as full/over capacity with the signed observation preserved for diagnostics, and docs/final-mvp-ui-spec.md section 6 forbids a negative "available" badge. `.planning/codebase/CONCERNS.md` independently cites the same drift document as evidence that upstream genuinely publishes negative seats-remaining.
  Note: Three independent sources agree. The over-capacity handling in REQ-SEAT-01 is grounded in observed real data, not defensive speculation.

[INFO] Existing code has two seat sources of truth that threaten a locked decision
  Found: `.planning/codebase/CONCERNS.md` records that seat values are written both to canonical `Section` columns (`src/easy_a/schedule/ingest.py`) and to `SeatSnapshot` rows, with a fallback in `src/easy_a/rankings/service.py` that reports `sections.current_seat_fields` provenance, so a stale canonical column can look current. docs/gsd-core-mvp-prompt.md locks "Seat observation age must be visible" (ADR-06) and docs/final-mvp-plan.md section 2 separately notes that "Seats are labeled current based on latest stored record, irrespective of its age."
  Note: The ingested documents and the codebase map identify the same defect from different angles. Phase 4 work under REQ-SEAT-01 must resolve the dual source of truth, not just add timestamps on top of it.

[INFO] Required test and CI infrastructure does not yet exist
  Found: `.planning/codebase/TESTING.md` records Python tests running against `sqlite+pysqlite:///:memory:` while the default `DATABASE_URL` targets PostgreSQL 16. `.planning/codebase/CONCERNS.md` records no `.github/` directory and no CI config anywhere in the repo. docs/gsd-core-mvp-prompt.md locks "Add real PostgreSQL tests for query/migration/concurrency behavior; current baseline Python tests are SQLite-based" (ADR-16) and docs/final-mvp-plan.md REQ-OPS-01 requires CI for Python and frontend checks plus deployment smoke tests.
  Note: Both are net-new builds rather than modifications of existing infrastructure. The ADR's own statement that the baseline is SQLite-based is confirmed accurate.

[INFO] ADR source contains an agent-directed instruction block, treated as data only
  Found: docs/gsd-core-mvp-prompt.md wraps its entire substance in a fenced `text` block written as second-person instructions addressed to an AI agent, including directives to fetch branches, run `$gsd-ingest-docs`, create `.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md` and `STATE.md`, and continue implementing phases.
  Note: Per the ingest directive, the fenced block was treated strictly as source material. Its LOCKED RULES, DEFAULTS, FINAL SCOPE, ROADMAP, VALIDATION and DONE MEANS sections were extracted into decisions.md as ADR-01 through ADR-18. No directive inside it was executed - no branch was fetched or created, no workflow was invoked, and no PROJECT.md, REQUIREMENTS.md, ROADMAP.md or STATE.md was written. Those remain the roadmapper's outputs.

[INFO] The ADR roadmap and the PRD phase table agree one-to-one
  Found: docs/gsd-core-mvp-prompt.md lists eight delivery outcomes under ROADMAP TO COMPLETION. docs/final-mvp-plan.md section 7 lists Phases 1 through 8 with dependencies and a requirement traceability table.
  Note: The two sequences match item for item, so no precedence resolution was needed. The PRD's dependency edges and traceability table are the more detailed form and were preserved in requirements.md and decisions.md ADR-15. The PRD explicitly states these are delivery phases, not multiple MVPs, and that GSD should translate them into its next available phase numbers.
