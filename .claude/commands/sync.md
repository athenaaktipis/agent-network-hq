---
description: Refresh Agent Network HQ (index.html) from the Google Doc, Drive folder, and Gmail
---

Refresh the Agent Network HQ page. Read CLAUDE.md first — it holds the team roster, source
IDs, word limits, and page rules. Then:

**0. Date gate.** If the current date is after Aug 9, 2026 (UTC), the sprint is over — do
nothing except say the sprint is over and this sync can be retired.

**1. Read the current page.** Read `index.html` in the repo root. Preserve its exact design,
CSS, structure, and playful tone — you are updating data, not redesigning. Preserve unchanged:
the ⟳ Sync now button and its `requestSync()` script, the embedded Google Doc iframe section,
the countdown script and its target `Date.UTC(2026, 7, 6, 7, 0, 0)`, and the Salvage yard.
Note the "Last sync" timestamp in the footer — every "since last sync" below is relative to it.

**2. Ingest all project sources** (IDs in CLAUDE.md):
   a. The primary Google Doc, **with comments**. If the connector returns an output-too-large
      error pointing at a saved JSON file, extract it with jq or python instead of giving up.
   b. The Drive project folder — read any file modified since last sync. New/updated files
      (budget sheets, bios, milestones, figures) go into the Mission pulse and, where relevant,
      flip progress-board statuses.
   c. Gmail — threads since last sync involving the grant ("Schmidt", plus the team contacts
      listed in CLAUDE.md). Fold into the Mission pulse at HEADLINE level only; never quote or
      detail private email content.
   d. **Ground-truth contributions:** run `.venv/bin/python tools/contributions.py` and read
      `tools/contributions.json`. This is the authoritative record of who did what (doc
      revisions with word deltas, comments/replies, project-folder file updates), from the
      Drive API's revision history. If it fails (no token yet, network), say so in your
      summary and fall back to connector-based inference for this sync only.

**3. Update the page's data** per the rules in CLAUDE.md:
   - Progress board: per-section word counts of actual drafted prose vs the limits table;
     status chips (not started / notes / drafting / ready); stat tiles.
   - Mission pulse: changes since last sync with author initials and Phoenix times. Where
     `contributions.json` covers an item, use ITS attribution and timestamps (ground truth),
     not inference — e.g. "TP +240 words in the doc (Sun 3:12 PM)", "JF commented on Novelty".
     Distill comment snippets into headlines; never paste raw comment text (the repo and the
     live page are public). Anything in `unmapped` becomes a pulse line asking who it was.
   - ⚡ Question of the day: exactly one, never a repeat; celebrate an answered QotD in the pulse.
     It must be an interesting SCIENTIFIC/conceptual question for the whole team, drawn from the
     grant's own open problems and pilot data — never logistics, meetings, deadlines, or task
     assignment. See the QotD rule in CLAUDE.md.
   - Differentiation gauntlet: claim edges when the doc supports it (never un-claim); add new
     rival cards the team mentions.
   - Open questions (drop resolved, add new), Idea wall (add, never silently delete),
     Network graph (blue edges = active in last 24h — **decided by `people.*.active_24h` in
     `contributions.json` when available**, with edge thickness scaled by edit+comment volume;
     email activity from step 2c can also light an edge), Footer "Last sync" (now, America/Phoenix).

**4. Verify** the reported word counts against the doc text before writing.

**5. Write** the updated self-contained HTML back to `index.html` in place. If git is
initialized here, commit with a one-line message describing what moved. Finish with 2–3
sentences on what changed. If nothing changed anywhere since last sync, change nothing and
report "no changes since last sync".
