---
sketch: 001
name: student-experience
question: "Which course summary helps students understand historical outcomes and choose a section?"
winner: "A"
status: direction_selected
tags: [discovery, course-results, grade-evidence, sections, responsive]
---

# Student experience visual review

Two working, responsive sketches. **A: Student guide was selected by the user on 2026-09-25.**
B remains available for comparison. The student walkthrough and final specification review remain open.
Production frontend, API, scoring, and database contents are unchanged.

## Open the review

From the repository root:

```sh
python3 -m http.server 4173 --bind 127.0.0.1 --directory .planning/sketches
```

Open <http://127.0.0.1:4173/001-student-experience/>. The server exposes only the sketch directory.
`index.html` is the review workspace: variant switch, real iframe viewport sizing, journey-state
selector, computed-style inspection, restart, and direct full-preview link. `experience.html`
contains both variants' inline CSS/JS and loads the shared theme and data snapshot. No build,
framework, CDN, font download, live API, or internet connection is needed for the prototypes.
The files also open directly in a browser; clipboard support depends on the browser's file policy.

- [A: Student guide](experience.html?variant=guide): generous separation, readable evidence sentences.
- [B: Compact comparison](experience.html?variant=compact): tighter desktop rows and labeled A–F strips.
- [Before/after](comparison.html): matching 1440 × 1000 and 390 × 844 captures.
- [Student guide specification](UI-SPEC.md): selected visual direction, interaction contract and future data work.
- [Review and walkthrough](REVIEW.md): critique, acceptance evidence, and actual-student test protocol.
- [Data record](DATA.md): sources, verified counts, limitations, refresh instructions.

The state selector covers discovery, MAC 1105 search, expanded grades, selected section,
limited history, unavailable history, empty results, and a direct 3000-level search.
These are working entry states: continue typing, filtering, sorting, opening, and selecting.
Compare A and B at the same state and width. The review wrapper scales down its iframe if the
window is too narrow; direct preview links and screenshot originals preserve exact viewports.

## Verification

The browser harness captures 28 variant/state/viewport combinations and checks real interactions,
grade denominators, complete MAC section selection, keyboard disclosure/focus, clipboard,
filters, sort, all-level direct search, missing evidence, reset, reduced motion, reflow, and axe.
`verification.json` is the machine-readable result; screenshots are in `screenshots/`.
These checks do not establish student comprehension or full assistive-technology conformance.

This machine's existing browser is under `~/.local/share/easy-a-browser/`. The review-only
Playwright/axe dependencies were installed in `/tmp/easy-a-sketch-browser`, outside the product.
To reproduce them if needed:

```sh
npm install --prefix /tmp/easy-a-sketch-browser playwright @axe-core/playwright --no-audit --no-fund
LD_LIBRARY_PATH="$HOME/.local/share/easy-a-browser/libs/usr/lib/x86_64-linux-gnu" \
NODE_PATH=/tmp/easy-a-sketch-browser/node_modules \
node .planning/sketches/001-student-experience/verify.cjs
```

Use the installed Chromium runtime (`chromium-1243`) and its shared-library directory. On another
machine, provision Playwright's browser normally; this is environment setup, not a product dependency.
The before screenshots require the unchanged application running with
`VITE_API_BASE_URL=http://127.0.0.1:8000`, its API, and hosted Supabase. They are real browser captures,
not recreations of the prior UI. Prototype checks run entirely from the stored aggregate snapshot.

## Workflow and supporting guidance

- [GSD sketch skill](/home/aatif101/.agents/skills/gsd-sketch/SKILL.md) and its
  [workflow](/home/aatif101/.agents/gsd-core/workflows/sketch.md): alternatives, interactions,
  shared tokens, manifest, visual review. The supplied plan is the alignment for building both
  alternatives. The user selected A; its winner marker and selection record are now saved.
  This selects the visual direction; it does not claim completed student validation or approval
  of every future API/implementation detail.
- [Frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md):
  read before building; applied to restraint, typography, meaningful structure, and copy.
- [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/ui-ux-pro-max/SKILL.md):
  targeted local queries for keyboard focus and chart labeling; React controlled-input guidance
  informs the later handoff. The general chart query's hierarchy result was rejected as irrelevant;
  the category-comparison result informed visible values and non-color alternatives.

No Figma connection was needed or claimed. No AI/LLM feature is introduced into Easy-A.
