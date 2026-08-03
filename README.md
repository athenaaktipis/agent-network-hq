# Agent Network HQ — Claude Code edition

War-room page for the Schmidt Sciences "Scaling AI Safety for a Multi-Agent World" proposal
(Focus Area 2: The Science of Agent Networks). Ported from Cowork so the sync loop can run
in Claude Code on your own machine.

What's here:

- `index.html` — the HQ page itself. **Currently a placeholder — see step 2.**
- `CLAUDE.md` — project context Claude Code loads automatically (team, deadlines, source IDs, page rules).
- `.claude/commands/sync.md` — the `/sync` slash command: the full refresh procedure that the
  Cowork scheduled task used to run.

## Setup

**1. Install Claude Code and open the project.**
Install from https://code.claude.com/docs (npm: `npm install -g @anthropic-ai/claude-code`),
then `cd` into this folder and run `claude`. Log in with the same account you use on claude.ai
(athena.aktipis@gmail.com).

**2. The real page is here.** ~~Drop in the real page~~ — done: this folder is now a clone of
the live deployment repo (`github.com/athenaaktipis/agent-network-hq` → GitHub Pages), so
`index.html` IS the current page with full git history. To publish syncs, authenticate once
with `gh auth login`.

**2b. Ground-truth contributions (one-time OAuth setup).**
`tools/contributions.py` reads the doc's revision history, comments, and folder activity so
the network graph and mission pulse reflect real, attributed activity. Setup:

1. In https://console.cloud.google.com create (or pick) a project and enable the
   **Google Drive API** (APIs & Services → Library).
2. APIs & Services → OAuth consent screen: External, add athena.aktipis@gmail.com as a
   **test user**.
3. Credentials → Create credentials → **OAuth client ID → Desktop app**; download the JSON
   and save it as `~/.config/agent-network-hq/client_secret.json`.
4. Run `.venv/bin/python tools/contributions.py --auth` and approve in the browser
   (as athena.aktipis@gmail.com). The token then refreshes itself; syncs run it
   non-interactively.

**3. Check connectors.**
`/sync` needs Google Drive and Gmail. These are Anthropic-hosted claude.ai connectors: connect
them at **claude.ai → Settings → Connectors** (you already have both connected for Cowork, so
likely nothing to do), and they appear in Claude Code automatically. Verify inside Claude Code
with `/mcp` — you should see Google Drive and Gmail listed. Note: these particular connectors
can't OAuth locally from Claude Code; they must be connected on claude.ai.

**4. Run a sync.**
Inside Claude Code, type `/sync`. Preview the result by opening `index.html` in a browser.
(The ⟳ Sync now button on the page was wired to Cowork and won't do anything locally — `/sync`
is its replacement.)

## Scheduling (optional)

Claude Code has no built-in scheduler; use cron/launchd with headless mode. Example — every
day at 7am, noon, and 5pm Phoenix time until the deadline:

```
0 7,12,17 * * * cd ~/agent-network-hq && claude -p "/sync" >> sync.log 2>&1
```

Headless runs will pause on permission prompts; either pre-approve the needed tools
(see the permissions section of the Claude Code docs — `--allowedTools`, or approve once
interactively with "always allow"), or just run `/sync` manually when you sit down — the
sprint only runs through Aug 8.

Recommended: `git init` in this folder before the first sync, so every sync is a commit and
you can diff or roll back any update.

## Deadlines

- Internal: Wed Aug 5, 2026, midnight EOD Phoenix (page countdown targets this).
- Funder: Aug 8, 2026, 11:59 PM Anywhere-on-Earth.
