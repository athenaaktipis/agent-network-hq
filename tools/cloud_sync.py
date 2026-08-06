#!/usr/bin/env python3
"""Machine-independent sync for Agent Network HQ.

Runs in GitHub Actions (no laptop, no Claude, no API key). Refreshes every part
of the page that can be computed deterministically from Google Drive:

  * section word counts + progress-board meters and status chips
  * stat tiles (core words drafted, sections started)
  * header status line (how many collaborators are verifiably active)
  * network-graph edges: solid = verified activity in 24h, dashed = tagged only
  * the "Verified activity" feed in the mission pulse
  * footer "Last sync" timestamp

Editorial content — the Question of the day, mission-pulse prose, the
differentiation gauntlet, the idea wall, AI drafts — is deliberately NOT touched
here. Those need judgement, and Claude writes them during a `/sync`. This script
only ever rewrites the regions delimited by <!--SYNC:NAME--> ... <!--/SYNC:NAME-->
markers, so an editorial sync and a cloud sync can't clobber each other.

Credentials come from env vars in CI (GOOGLE_TOKEN_JSON, GOOGLE_CLIENT_SECRET_JSON)
or from ~/.config/agent-network-hq/ locally. Never printed, never committed.
"""
import datetime
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contributions as C  # noqa: E402  (shares TEAM map, auth, and fetchers)

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(os.path.dirname(HERE), "index.html")

DOC_ID = C.DOC_ID
EXPORT_URL = f"https://www.googleapis.com/drive/v3/files/{DOC_ID}/export"

# Section header -> (page label, word limit). Order matches the doc.
SECTIONS = [
    ("Project Title",            "Title",            20),
    ("Plain-language Summary",   "Plain summary",    None),
    ("Problem and Impact",       "Problem & Impact", 500),
    ("Approach",                 "Approach",         1000),
    ("Novelty",                  "Novelty",          300),
    ("Feasibility",              "Feasibility",      300),
    ("Team",                     "Team",             300),
    ("Proposal Risks",           "Proposal Risks",   300),
    ('"But for" impact',         '"But for" impact', 300),
    ("Existing Funding",         "Existing Funding", 300),
]

# Template instruction text is italic in the doc but plain in the text export,
# so drop lines starting with these known template openers.
INSTRUCTION_OPENERS = (
    "Use plain, concrete language", "Describe the central", "Provide a detailed description",
    "What existing work is similar", "What intuition, prior work", "List all project team members",
    "What are the most significant risks", "We are looking to fund", "List existing funding",
    "Please provide up to 5 keywords", "If your proposal does not involve",
    "Please suggest up to 5", "Please list your project's", "PI CV", "Please complete our template",
    "When you expect this", "Short label", "Describe the substantive",
)

# Every other template heading. These aren't word-counted, but they must act as
# section boundaries or a counted section swallows everything below it.
OTHER_HEADINGS = (
    "Collaborator(s)", "Headshot(s)", "Project Tier", "Project Duration", "Keywords",
    "Suggestions (Optional)", "Suggested Reviewers", "Optional Figure/Diagram", "References:",
    "References", "Milestones Template", "Budget", "PIs", "Staff/Other Personnel",
    "Project Advisory Board", "Travel", "Compute", "Anything Else", "Proposal Draft Starts Here",
    "Notes:", "Funding Tier", "Research Cluster",
)


def fetch_doc_text(session):
    r = session.get(EXPORT_URL, params={"mimeType": "text/plain"})
    r.raise_for_status()
    r.encoding = "utf-8"
    # strip Google's comment anchors like [c] [f] [m]
    return re.sub(r"\[[a-z]{1,2}\]", "", r.text)


def section_word_counts(text):
    lines = text.splitlines()
    counted, boundaries = [], []
    for i, ln in enumerate(lines):
        s = ln.strip()
        hit = False
        for key, label, limit in SECTIONS:
            if s.startswith(key) and ("words)" in s or "sentences)" in s):
                counted.append((i, label, limit))
                boundaries.append(i)
                hit = True
                break
        if not hit and any(s.startswith(h) for h in OTHER_HEADINGS):
            boundaries.append(i)

    counts = {}
    for idx, label, limit in counted:
        later = [b for b in boundaries if b > idx]
        end = min(later) if later else len(lines)
        body = []
        for ln in lines[idx + 1:end]:
            s = ln.strip()
            if not s:
                continue
            if any(s.startswith(o) for o in INSTRUCTION_OPENERS):
                continue
            body.append(s)
        counts[label] = (len(re.findall(r"\S+", " ".join(body))), limit)
    return counts


WORDS_CELL = re.compile(r'(<div class="words">)~?(\d+)\s*/\s*(\d+)(</div>)')
FILL_WIDTH = re.compile(r'(<div class="fill[^"]*" style="width:)(\d+)(%)')
ROW_NAME = re.compile(r'<div class="name">(.*?)\s*<small>')


def patch_board(page, counts):
    """Update ONLY the numbers and meter widths inside existing rows.

    Status chips, their [initials] attribution, the lighter `fill notes`
    shading, and any hand-written cell like "assigned" are editorial — Claude
    owns them, so they are never rewritten here. A row is only touched if its
    words cell already looks like "N / LIMIT".
    """
    out, touched = [], 0
    for line in page.splitlines(keepends=True):
        if 'class="row"' not in line:
            out.append(line)
            continue
        nm = ROW_NAME.search(line)
        label = html.unescape(nm.group(1)).strip() if nm else ""
        if label not in counts:
            out.append(line)
            continue
        words, lim = counts[label]
        if not lim or not WORDS_CELL.search(line):
            out.append(line)      # e.g. Feasibility's "assigned" — leave alone
            continue
        pct = min(100, round(words / lim * 100))
        new = WORDS_CELL.sub(rf'\g<1>{words} / {lim}\g<4>', line)
        new = FILL_WIDTH.sub(rf'\g<1>{pct}\g<3>', new)
        touched += new != line
        out.append(new)
    return "".join(out), touched


# Node geometry must match the SVG in index.html.
NODES = {
    "AA": {"spoke": ("190", "52", "190", "119"), "width": 5},
    "LG": {"spoke": ("63", "120", "146", "150"), "width": 3},
    "TP": {"spoke": ("317", "120", "234", "150"), "width": 2.5},
    "JF": {"spoke": ("95", "277", "158", "200"), "width": 2.5},
    "RD": {"spoke": ("285", "277", "222", "200"), "width": 2.5},
}
AA_LINKS = {"LG": ("76", "108"), "RD": ("285", "265"), "TP": ("305", "105"), "JF": ("100", "270")}


def build_edges(people):
    out = []
    for who, geo in NODES.items():
        x1, y1, x2, y2 = geo["spoke"]
        if people[who]["active_24h"]:
            out.append(f'        <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                       f'stroke="var(--series-1)" stroke-width="{geo["width"]}"/>')
        else:
            out.append(f'        <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
    for who, (x2, y2) in AA_LINKS.items():
        if people[who]["active_24h"]:
            out.append(f'        <line x1="190" y1="52" x2="{x2}" y2="{y2}" '
                       f'stroke="var(--series-1)" stroke-width="2.5"/>')
        else:
            out.append(f'        <line x1="190" y1="52" x2="{x2}" y2="{y2}" stroke-dasharray="5 4"/>')
    return "\n".join(out)


def build_figcap(people):
    live, quiet = [], []
    for k, p in people.items():
        bits = []
        if p["edits_24h"]:
            bits.append(f'{p["edits_24h"]} edit{"s" if p["edits_24h"] != 1 else ""}')
        if p["comments_24h"] + p["replies_24h"]:
            n = p["comments_24h"] + p["replies_24h"]
            bits.append(f'{n} comment{"s" if n != 1 else ""}')
        if p["words_added_24h"]:
            bits.append(f'+{p["words_added_24h"]} words')
        (live if p["active_24h"] else quiet).append(
            f'<b>{p["name"]}</b>' + (f' ({", ".join(bits)})' if bits and p["active_24h"] else ""))
    s = ("<b>Measured, not inferred.</b> Solid blue = verified activity in the last 24 hours, read "
         "from the doc's revision history, comment log, and Drive folder; dashed = tagged but not "
         "yet active. ")
    s += (f'Live now: {", ".join(live)}. ' if live else "No verified activity in the last 24 hours. ")
    if quiet:
        s += f'Quiet: {", ".join(quiet)}.'
    return s


KIND_VERB = {"edit": "edited the doc", "comment": "left a comment",
             "reply": "replied to a comment", "file": "updated a project file"}


def build_verified(data):
    """Activity headlines only — never comment text (this page is public)."""
    people = data["people"]
    events = data["events"][:6]
    if not events:
        return ('      <li>📡 <b>No verified activity yet today.</b> Doc edits, comments, and folder '
                'uploads appear here automatically, attributed by name and time. '
                f'<span class="when">— checked {data["generated_at_phoenix"]}</span></li>')
    tally = " · ".join(
        f'<span class="initial">{k}</span> {p["edits_24h"] + p["comments_24h"] + p["replies_24h"]}'
        for k, p in people.items() if p["active_24h"])
    # One line per person, not one per event — the pulse below carries the story.
    lines = []
    for who in [k for k, p in people.items() if p["active_24h"]]:
        mine = [e for e in data["events"] if e["initials"] == who]
        if not mine:
            continue
        p = people[who]
        bits = []
        if p["edits_24h"]:
            bits.append(f'{p["edits_24h"]} doc edit{"s" if p["edits_24h"] != 1 else ""}')
        n = p["comments_24h"] + p["replies_24h"]
        if n:
            bits.append(f'{n} comment{"s" if n != 1 else ""}')
        files = [re.search(r'updated “([^”]+)”', e["summary"]) for e in mine if e["kind"] == "file"]
        names = [html.escape(f.group(1)) for f in files if f]
        if names:
            bits.append("uploaded " + ", ".join(dict.fromkeys(names)))
        span = mine[-1]["when_phoenix"] if len(mine) == 1 else \
            f'{mine[-1]["when_phoenix"]} → {mine[0]["when_phoenix"].split(", ")[-1]}'
        lines.append(f'      <li><b>{p["name"]}</b> — {", ".join(bits) or "active"} '
                     f'<span class="when">— {span}</span></li>')
    return (f'      <li>📡 <b>Verified activity</b>, read from the doc\'s revision history — '
            f'last 24h: {tally or "none yet"}</li>\n' + "\n".join(lines)) if lines else \
           f'      <li>📡 <b>Verified activity</b> — last 24h: {tally or "none yet"}</li>'


def replace_marker(page, name, body):
    pat = re.compile(f"(<!--SYNC:{name}-->)(.*?)(<!--/SYNC:{name}-->)", re.S)
    if not pat.search(page):
        print(f"  ! marker {name} not found — skipped")
        return page, False
    new = pat.sub(lambda m: m.group(1) + "\n" + body + "\n" + m.group(3), page)
    return new, new != page


def main():
    creds = C.get_creds(interactive=False)
    from google.auth.transport.requests import AuthorizedSession
    from googleapiclient.discovery import build
    drive = build("drive", "v3", credentials=creds)
    session = AuthorizedSession(creds)

    # 1. contribution ground truth (writes tools/contributions.json)
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(HERE, "contributions.py")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"contributions.py failed:\n{r.stderr[-2000:]}")
    with open(os.path.join(HERE, "contributions.json")) as f:
        data = json.load(f)
    people = data["people"]

    # 2. doc word counts
    doc_text = fetch_doc_text(session)
    counts = section_word_counts(doc_text)
    core = sum(w for w, _ in counts.values())
    # Milestones + Budget sit on the board but aren't word-counted; Budget counts
    # as started once personnel lines exist, Milestones once the table has rows.
    budget_started = "SUM month" in doc_text
    # count filled milestone rows (dated entries between the two table headers)
    ms = 0
    if "Intermediate Milestones" in doc_text and "End-of-Project Outcomes" in doc_text:
        seg = doc_text[doc_text.index("Intermediate Milestones"):doc_text.index("End-of-Project Outcomes")]
        ms = len(re.findall(r"^\s*Q[1-4]\s+20\d\d", seg, re.M))
    empty = [l for _k, l, _n in SECTIONS if counts.get(l, (0,))[0] == 0]
    if not budget_started:
        empty.append("Budget")
    if ms < 4:
        empty.append("Milestones")
    started = (sum(1 for w, _ in counts.values() if w > 0)
               + (1 if budget_started else 0) + (1 if ms else 0))
    # total words that must come out of over-limit sections
    over_names = [l for _k, l, _n in SECTIONS if counts.get(l, (0, None))[1]
                  and counts[l][0] > counts[l][1]]
    over = sum(max(0, counts[l][0] - counts[l][1]) for l in over_names)
    total_sections = len(SECTIONS) + 2

    page = open(PAGE, encoding="utf-8").read()
    active = [k for k, p in people.items() if p["active_24h"]]
    now_phx = data["generated_at_phoenix"]

    blocks = {
        "STATUSLINE": (
            f'    <span><span class="dot">●</span> {len(active)} of 5 agents active in the last 24h '
            f'(verified) · network status: <b>{"accelerating" if len(active) > 2 else "quiet"}</b> — '
            f'{started} of {total_sections} sections in motion</span>'),
        "TILEWORDS": (
            f'    <div class="value">{core}<span style="font-size:16px;color:var(--muted)"> / 3,000'
            f'</span></div>\n    <div class="sub">verified count from the working doc</div>'),
        "TILESECTIONS": (
            f'    <div class="value">{started}<span style="font-size:16px;color:var(--muted)"> / '
            f'{total_sections}</span></div>\n    <div class="sub">'
            f'{(" &amp; ".join(empty) + " still empty") if empty else "every section has content"}</div>'),
        "EDGES": build_edges(people),
        "FIGCAP": f'    <div class="figcap">{build_figcap(people)}</div>',
        "VERIFIED": build_verified(data),
        "TILECUT": (
            f'    <div class="value">{over if over else 0}'
            f'<span style="font-size:16px;color:var(--muted)"> words</span></div>\n'
            f'    <div class="sub">'
            f'{"over in " + ", ".join(over_names) if over_names else "every section inside its limit"}'
            f'</div>'),
    }

    # Apply the substantive regions first. If none of them moved, the page is
    # already current — leave it completely alone rather than committing a new
    # timestamp every 15 minutes.
    changed = []
    for name, body in blocks.items():
        page, did = replace_marker(page, name, body)
        if did:
            changed.append(name)

    page, rows = patch_board(page, counts)
    if rows:
        changed.append(f"BOARD({rows} rows)")

    print(f"core words: {core} | sections started: {started}/{total_sections} | "
          f"active 24h: {', '.join(active) or 'nobody'}")
    if not changed:
        print("no data changes — page left untouched")
        return 0

    page, _ = replace_marker(page, "LASTSYNC", (
        f'<b>Last update:</b> {now_phx} Phoenix · <i>automatic — data refreshed from the '
        f'doc\'s revision history</i>'))
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"regions updated: {', '.join(changed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
