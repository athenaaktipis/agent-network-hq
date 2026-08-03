#!/usr/bin/env python3
"""Ground-truth contribution detection for Agent Network HQ.

Pulls, via the Google Drive API with Athena's own OAuth credentials:
  1. Revision history of the working doc  -> who edited and when
  2. Comment + reply history of the doc   -> who commented, when
  3. File activity in the project folder  -> who uploaded/modified files, when

Emits tools/contributions.json — the ground truth that /sync uses for the
network graph's activity edges and the mission pulse. Never guesses: anything
not attributable to a known team member is listed under "unmapped" for a human
(or the sync agent) to resolve.

Setup (one time):
  1. Save an OAuth "Desktop app" client secret at ~/.config/agent-network-hq/client_secret.json
     (Google Cloud console -> enable Drive API -> OAuth consent (add yourself as
     test user) -> Credentials -> Create OAuth client ID -> Desktop app -> download JSON)
  2. Run:  .venv/bin/python tools/contributions.py --auth
     A browser opens; approve with athena.aktipis@gmail.com. Token is cached at
     ~/.config/agent-network-hq/token.json and refreshes itself after that.

Normal run:  .venv/bin/python tools/contributions.py
"""
import argparse
import datetime
import json
import os
import re
import sys

CONF_DIR = os.path.expanduser("~/.config/agent-network-hq")
CLIENT_SECRET = os.path.join(CONF_DIR, "client_secret.json")
TOKEN_PATH = os.path.join(CONF_DIR, "token.json")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

DOC_ID = "1r6I20zgDDmYqaPdJbyD0-Lce_bgKA9Lp5O0-znEh248"
FOLDER_ID = "1N8P6VSj8_DohVSdijB8gG_pV062mBXVN"

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "contributions.json")
CACHE_PATH = os.path.join(HERE, ".revision_wordcount_cache.json")

ACTIVE_WINDOW_HOURS = 24   # blue-edge window on the network graph
EVENT_WINDOW_HOURS = 72    # how far back the events feed reaches

# Team mapping: lowercase substrings of display names / emails -> initials.
TEAM = {
    "AA": {"name": "Athena", "match": ["athena", "aktipis", "athena.aktipis@gmail.com"]},
    "JF": {"name": "Jennifer", "match": ["jennifer", "fewell"]},
    "TP": {"name": "Ted", "match": ["ted", "pavlic"]},
    "LG": {"name": "Liz", "match": ["liz", "elizabeth", "grumbach", "egrumbac@asu.edu", "egrumbac@gmail.com"]},
    "RD": {"name": "Reilly", "match": ["reilly", "donovan"]},
}


def to_initials(display_name, email=""):
    hay = f"{display_name or ''} {email or ''}".lower()
    for initials, spec in TEAM.items():
        if any(m in hay for m in spec["match"]):
            return initials
    return None


def phoenix(ts_iso):
    """RFC3339 UTC string -> 'Sun Aug 2, 5:36 PM' in America/Phoenix."""
    from zoneinfo import ZoneInfo
    dt = datetime.datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    local = dt.astimezone(ZoneInfo("America/Phoenix"))
    return local.strftime("%a %b %-d, %-I:%M %p")


def get_creds(interactive):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    # In CI the token arrives as an env var (GitHub Actions secret) instead of a file.
    env_token = os.environ.get("GOOGLE_TOKEN_JSON")
    if env_token and not os.path.exists(TOKEN_PATH):
        os.makedirs(CONF_DIR, exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(env_token)
        os.chmod(TOKEN_PATH, 0o600)
    env_secret = os.environ.get("GOOGLE_CLIENT_SECRET_JSON")
    if env_secret and not os.path.exists(CLIENT_SECRET):
        os.makedirs(CONF_DIR, exist_ok=True)
        with open(CLIENT_SECRET, "w") as f:
            f.write(env_secret)
        os.chmod(CLIENT_SECRET, 0o600)

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        return creds
    if not interactive:
        sys.exit(
            "No usable token. Run once interactively:\n"
            "  .venv/bin/python tools/contributions.py --auth"
        )
    if not os.path.exists(CLIENT_SECRET):
        sys.exit(
            f"Missing {CLIENT_SECRET}\n"
            "Create an OAuth 'Desktop app' client in the Google Cloud console "
            "(with the Drive API enabled) and save its JSON there. See the "
            "docstring at the top of this file."
        )
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
    creds = flow.run_local_server(port=0)
    os.makedirs(CONF_DIR, exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    os.chmod(TOKEN_PATH, 0o600)
    return creds


def word_count(text):
    return len(re.findall(r"\S+", text))


def fetch_revisions(drive, session):
    """All doc revisions with per-revision word counts (cached; revisions are immutable)."""
    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            cache = json.load(f)

    revs, token = [], None
    while True:
        resp = drive.revisions().list(
            fileId=DOC_ID,
            fields="nextPageToken,revisions(id,modifiedTime,exportLinks,"
                   "lastModifyingUser(displayName,emailAddress))",
            pageSize=200,
            pageToken=token,
        ).execute()
        revs.extend(resp.get("revisions", []))
        token = resp.get("nextPageToken")
        if not token:
            break

    for rev in revs:
        rid = rev["id"]
        if rid in cache:
            rev["words"] = cache[rid]
            continue
        link = (rev.get("exportLinks") or {}).get("text/plain")
        if not link:
            rev["words"] = None
            continue
        r = session.get(link)
        rev["words"] = word_count(r.text) if r.status_code == 200 else None
        cache[rid] = rev["words"]

    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)
    return revs


def fetch_comments(drive):
    comments, token = [], None
    while True:
        resp = drive.comments().list(
            fileId=DOC_ID,
            fields="nextPageToken,comments(author(displayName),createdTime,"
                   "modifiedTime,content,resolved,quotedFileContent(value),"
                   "replies(author(displayName),createdTime,content))",
            includeDeleted=False,
            pageSize=100,
            pageToken=token,
        ).execute()
        comments.extend(resp.get("comments", []))
        token = resp.get("nextPageToken")
        if not token:
            break
    return comments


def fetch_folder_files(drive):
    resp = drive.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed = false",
        fields="files(id,name,mimeType,modifiedTime,"
               "lastModifyingUser(displayName,emailAddress))",
        pageSize=200,
    ).execute()
    return resp.get("files", [])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--auth", action="store_true",
                    help="allow the interactive browser OAuth flow")
    args = ap.parse_args()

    creds = get_creds(interactive=args.auth)
    from google.auth.transport.requests import AuthorizedSession
    from googleapiclient.discovery import build
    drive = build("drive", "v3", credentials=creds)
    session = AuthorizedSession(creds)

    now = datetime.datetime.now(datetime.timezone.utc)
    active_cut = now - datetime.timedelta(hours=ACTIVE_WINDOW_HOURS)
    event_cut = now - datetime.timedelta(hours=EVENT_WINDOW_HOURS)

    def ts(s):
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))

    people = {
        k: {"name": v["name"], "last_activity": None, "active_24h": False,
            "edits_24h": 0, "words_added_24h": 0, "words_removed_24h": 0,
            "comments_24h": 0, "replies_24h": 0}
        for k, v in TEAM.items()
    }
    events, unmapped = [], []

    def bump(initials, when_iso, kind):
        p = people[initials]
        if p["last_activity"] is None or when_iso > p["last_activity"]:
            p["last_activity"] = when_iso
        if ts(when_iso) >= active_cut:
            p["active_24h"] = True
            p[kind] += 1

    # --- 1. doc revisions -> who edited, when ---
    # NOTE: no word deltas here. Google's per-revision text/plain export
    # includes template boilerplate inconsistently (and is missing entirely
    # for some revisions), so revision-to-revision deltas are meaningless.
    # cloud_sync.py counts drafted words per section instead.
    revs = fetch_revisions(drive, session)
    revs.sort(key=lambda r: r["modifiedTime"])
    prev_words = None
    for rev in revs:
        user = rev.get("lastModifyingUser") or {}
        who = to_initials(user.get("displayName"), user.get("emailAddress"))
        when = rev["modifiedTime"]
        words = rev.get("words")
        delta = (words - prev_words) if (words is not None and prev_words is not None) else None
        if words is not None:
            prev_words = words
        if who is None:
            if ts(when) >= event_cut:
                unmapped.append({"who": user.get("displayName") or "unknown",
                                 "when": when, "what": "doc revision"})
            continue
        bump(who, when, "edits_24h")
        if ts(when) >= event_cut:
            desc = "edited the doc"
            events.append({"when": when, "when_phoenix": phoenix(when),
                           "initials": who, "kind": "edit", "summary": desc})

    # --- 2. comments + replies ---
    for c in fetch_comments(drive):
        author = (c.get("author") or {}).get("displayName", "")
        who = to_initials(author)
        when = c.get("createdTime")
        snippet = (c.get("content") or "").strip().replace("\n", " ")[:90]
        anchor = ((c.get("quotedFileContent") or {}).get("value") or "").strip()[:40]
        if who is None:
            if when and ts(when) >= event_cut:
                unmapped.append({"who": author or "unknown", "when": when, "what": "comment"})
        else:
            bump(who, when, "comments_24h")
            if ts(when) >= event_cut:
                summary = f"commented: “{snippet}”"
                if anchor:
                    summary += f" (on “{anchor}…”)"
                events.append({"when": when, "when_phoenix": phoenix(when),
                               "initials": who, "kind": "comment", "summary": summary})
        for rep in c.get("replies", []):
            rauthor = (rep.get("author") or {}).get("displayName", "")
            rwho = to_initials(rauthor)
            rwhen = rep.get("createdTime")
            if rwho is None:
                if rwhen and ts(rwhen) >= event_cut:
                    unmapped.append({"who": rauthor or "unknown", "when": rwhen, "what": "reply"})
                continue
            bump(rwho, rwhen, "replies_24h")
            if ts(rwhen) >= event_cut:
                rsnip = (rep.get("content") or "").strip().replace("\n", " ")[:90]
                events.append({"when": rwhen, "when_phoenix": phoenix(rwhen),
                               "initials": rwho, "kind": "reply",
                               "summary": f"replied: “{rsnip}”"})

    # --- 3. project-folder file activity ---
    for f in fetch_folder_files(drive):
        if f["id"] == DOC_ID:
            continue
        user = f.get("lastModifyingUser") or {}
        who = to_initials(user.get("displayName"), user.get("emailAddress"))
        when = f["modifiedTime"]
        if who is None:
            if ts(when) >= event_cut:
                unmapped.append({"who": user.get("displayName") or "unknown",
                                 "when": when, "what": f"file: {f['name']}"})
            continue
        bump(who, when, "edits_24h")
        if ts(when) >= event_cut:
            events.append({"when": when, "when_phoenix": phoenix(when),
                           "initials": who, "kind": "file",
                           "summary": f"updated “{f['name']}” in the project folder"})

    events.sort(key=lambda e: e["when"], reverse=True)
    out = {
        "generated_at": now.isoformat(timespec="seconds"),
        "generated_at_phoenix": phoenix(now.isoformat()),
        "doc_id": DOC_ID,
        "active_window_hours": ACTIVE_WINDOW_HOURS,
        "event_window_hours": EVENT_WINDOW_HOURS,
        "doc_total_words_latest_revision": prev_words,
        "people": people,
        "events": events,
        "unmapped": unmapped,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)

    active = [k for k, p in people.items() if p["active_24h"]]
    print(f"Wrote {OUT_PATH}")
    print(f"  revisions: {len(revs)}  events(72h): {len(events)}  "
          f"active(24h): {', '.join(active) if active else 'nobody'}")
    if unmapped:
        print(f"  WARNING: {len(unmapped)} recent action(s) by unmapped people "
              f"— see 'unmapped' in the JSON")


if __name__ == "__main__":
    main()
