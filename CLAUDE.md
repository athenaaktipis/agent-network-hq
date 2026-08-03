# Agent Network HQ — project context

This repo is the war room for **Athena Aktipis's team's Schmidt Sciences grant proposal**:
"Scaling AI Safety for a Multi-Agent World", **Focus Area 2: The Science of Agent Networks**.

The single deliverable in this repo is `index.html` — a self-contained, playful HTML "HQ"
page the whole team looks at. Your job in this repo is to keep that page's DATA current
(via the `/sync` command), never to redesign it.

## Deadlines (do not confuse these)

- **Internal team deadline:** Wednesday **Aug 5, 2026, midnight end-of-day Phoenix**.
  The page countdown targets `Date.UTC(2026, 7, 6, 7, 0, 0)` — never change this target.
- **Funder hard deadline:** **Aug 8, 2026, 11:59 PM Anywhere-on-Earth** (= Aug 9, 11:59 UTC).
- If today is after Aug 9, 2026 (UTC), the sprint is over: don't sync, just say so.

## Team (initials used for attribution on the page)

| Initials | Person | Notes |
|---|---|---|
| AA | Athena Aktipis | PI (this repo's owner) |
| JF | Jennifer Fewell | |
| TP | Ted Pavlic | |
| LG | Liz Grumbach | egrumbac@asu.edu / egrumbac@gmail.com |
| RD | Reilly Donovan | |

Attributions in the doc appear as initials tags `[AA] [JF] [TP] [LG] [RD]` or `(Name)` parentheticals.

## Data sources

- **Primary working doc (Google Doc):** fileId `1r6I20zgDDmYqaPdJbyD0-Lce_bgKA9Lp5O0-znEh248`
  — always read **with comments included**.
- **Project folder (Google Drive):** search with query `parentId = '1N8P6VSj8_DohVSdijB8gG_pV062mBXVN'`
  — budget sheets, bios, milestones, figures. Read anything modified since the page's last sync.
- **Gmail:** threads since last sync involving the grant — search "Schmidt" plus threads with
  egrumbac@asu.edu / egrumbac@gmail.com, Ted Pavlic, Jennifer Fewell, Reilly Donovan.
- **Ground-truth contributions (`tools/contributions.py`):** reads the working doc's revision
  history (who edited, when, word deltas), comments/replies, and project-folder file activity
  via the Drive API with Athena's own OAuth token (`~/.config/agent-network-hq/token.json`).
  Output: `tools/contributions.json`. This is AUTHORITATIVE for the network graph's blue
  activity edges and for Mission-pulse attribution — prefer it over inference whenever present.
  It is gitignored (public repo): only distilled headlines go into the page, never raw
  comment text or the JSON itself.

- **WhatsApp:** the group chat **"Schmidt Sciences (Multi-Agent) Group Chat"**, JID
  `120363427034331498@g.us` — read messages since the last sync. (A separate, older
  "Schmidt Sciences Group Chat", `120363427050636396@g.us`, is from the May proposal; check it
  only if something references it.) Team members coordinate here in real time, so this is often
  where a bio, a CV, or a decision lands first.

**Private-message privacy rule (email AND WhatsApp):** developments from email and WhatsApp go
into the Mission pulse at HEADLINE level only (e.g. "Ted sent his bio", "Liz confirmed headshots
received"). Never quote or paraphrase message content in detail, never reproduce a thread, and
never put a phone number or WhatsApp handle on the page. This page is PUBLIC — assume anyone
can read it. When in doubt, say that something happened without saying what was said.

## Section word limits (progress board)

Count ACTUAL drafted prose only — exclude the template's italicized instructions and call boilerplate.

| Section | Limit |
|---|---|
| Title | ≤ 20 words |
| Plain summary | 2–3 sentences |
| Problem & Impact | ≤ 500 |
| Approach | ≤ 1000 |
| Novelty | ≤ 300 |
| Feasibility | ≤ 300 |
| Team | ≤ 300 |
| Proposal Risks | ≤ 300 |
| "But for" impact | ≤ 300 |
| Existing Funding | ≤ 300 |
| Milestones | table rows filled |
| Budget/compute | option chosen |

Status chips: `not started` / `notes` / `drafting` / `ready`. Always verify reported word
counts against the actual doc text before publishing.

## Page rules (apply on every sync — see /sync for the full procedure)

- **Preserve exactly:** overall design/CSS/structure and playful tone; the ⟳ Sync now button
  and its `requestSync()` script; the embedded Google Doc iframe section; the countdown script
  and its target; the Salvage yard.
- **Mission pulse:** what changed since last sync (doc + folder + email), with author initials
  and America/Phoenix times.
- **⚡ Question of the day:** exactly ONE. It is addressed to **the whole team** and must be a
  genuinely **interesting intellectual question about the science of the grant** — a conceptual
  or methodological question the proposal itself has to answer (how we define a cooperation
  "failure", what the detector's decision threshold should be, which biological mechanism
  actually maps onto LLM agents, what the pilot data really shows, how to out-differentiate a
  gauntlet rival). Ground it in the doc's own open questions and the preliminary data.
  **Never** make it a logistics or project-management question — no meetings, calendars,
  deadlines, assignments, or "who takes first crack at X". Say which section it unblocks.
  Never repeat the previous QotD (it's visible in the current HTML). If the previous QotD got
  answered, celebrate that in the pulse.
- **Differentiation gauntlet:** when Novelty notes contain a distinguishing sentence for a rival
  card, flip its chip from `◑ edge unclaimed` (class `chip open`) to `✓ edge claimed`
  (class `chip claimed`), replace the italic candidate text with the team's actual sentence,
  credit initials. Add cards for newly mentioned competitors. **Never un-claim a card.**
- **Open questions:** drop resolved, add new.
- **Idea wall:** add cards for new Notes items; never delete unless explicitly dropped.
- **Network graph:** blue edges for people active in the last 24h (doc, comments, or email);
  keep node colors and layout.
- **Footer "Last sync":** current time in America/Phoenix.

## Notes for Claude Code

- Google Drive / Gmail / Calendar tools come from the claude.ai connectors (they appear here
  automatically once connected at claude.ai → Settings → Connectors). Check with `/mcp`.
  Exact tool names may differ from other Claude surfaces — use whatever Drive "read file /
  search files" and Gmail "search threads" tools are listed.
- The page is plain standalone HTML: preview by opening `index.html` in a browser.
  The ⟳ Sync now button was wired to the Cowork app and may be inert here; running `/sync`
  is its replacement.
