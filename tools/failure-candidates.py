#!/usr/bin/env python3
"""failure-candidates.py — surface failure-ledger candidates from daily notes.

Mechanical recall, not judgment. Two passes:

1. Daily-note scan: lines carrying STRONG incident markers surface on
   their own; WEAK markers surface only with a second corroborating
   signal. Routine operational noise (poller/sweeper logs, user quotes,
   fact entries, ledger-machinery bookkeeping) is excluded.
2. AGENTS.md lesson cross-check: dated lessons with no matching
   failures.md entry.

Candidate identity (v2, 2026-10-24): a content hash of the line's
60-char snippet prefix — the same text the legacy `file:line:snippet`
keys carried. Line numbers and file names are display-only now, so
dispositions survive note edits that move lines around. Legacy rows in
reviewed-candidates.jsonl are migrated transparently at load: their
cid is derived from the stored key's snippet component.

Vanished-candidate detection (v2): every scan records undispositioned
candidates in scan-state.json. A candidate that was pending at the
previous scan, is absent now, and still has no disposition is reported
in a VANISHED section instead of silently dropping out of the queue
(the 2026-10-22 stop-scope/Litmus loss).

The script NEVER writes to failures.md. It prints a review queue; the
agent dispositions each candidate (file / reject / defer) and records
the disposition in reviewed-candidates.jsonl so it is not re-surfaced.

Usage:
    failure-candidates.py [--days N] [--since YYYY-MM-DD]
                          [--reviewed PATH] [--failures PATH]
                          [--state PATH]
    failure-candidates.py --mark-reviewed <key> <disposition> [note]
        <key> is the printed `c:<hash>` token (a legacy
        file:line:snippet key is also accepted and converted).
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import re

HOME = os.path.expanduser("~")
MEMORY = os.path.join(HOME, "memory")
TOOL_DIR = os.path.join(HOME, "workspace", "tools", "memory-stack")
DEFAULT_REVIEWED = os.path.join(TOOL_DIR, "reviewed-candidates.jsonl")
DEFAULT_FAILURES = os.path.join(MEMORY, "failures.md")
DEFAULT_STATE = os.path.join(TOOL_DIR, "scan-state.json")
AGENTS = os.path.join(HOME, "AGENTS.md")

# High-precision markers: a line carrying one of these is almost always
# describing a real incident or a rule born from one.
STRONG = re.compile(
    r"(process failure|workflow failure|failure to avoid|worth the rule|"
    r"never probe|silently failed|gotcha|owned breach|"
    r"self-correction|burned \d|independent catcher|rule produced|"
    r"near miss|failure mode|lesson learned|"
    r"never (use|share|run|push|rebuild|treat)[^.]{0,80}(fail|hang|wipe|lose|burn|silent|break))",
    re.IGNORECASE,
)

# Low-precision markers: only count when corroborated by a second signal.
WEAK = re.compile(
    r"(fail(?:ed|ure)?s?|broke|broken|went wrong|mistake|silently|burned|"
    r"hung|hangs|stall(?:ed|s)?|never returned|wiped|clobber|"
    r"exit 137|502|timed? out|\bdead\b|lost)",
    re.IGNORECASE,
)

# Second signals that corroborate a weak marker.
CORROBORATE = re.compile(
    r"(instead of|rather than|should have|never use|do not|don't|"
    r"rule\b|avoid|caught|fixed|workaround|retry|instead)",
    re.IGNORECASE,
)

# Routine operational noise: never a ledger candidate. The bookkeeping
# patterns (v2) keep the sweep/triage machinery's own paperwork — run
# summaries, quoted review keys, disposition tallies — from becoming
# tomorrow's candidates.
NOISE = re.compile(
    r"(RESULT:\s*(WAIT|OK|EXPIRED)|routine no-op|poller|sweeper|"
    r"cron check|no hung tasks|^\s*-\s*quote:|\[fact\||"
    r"no new failures since last sweep|failures\.md|^\s*#{1,6}\s|"
    r"^\s*\"|^\s*-\s*(\*\*)?c\d{5}\b|"
    r"\bc:[0-9a-f]{16}\b|20\d\d-\d\d-\d\d\.md:\d+:|"
    r"scanner self-reference|review queue|marked reviewed|audit batch|"
    r"backup gate|candidates scanned|dispositions recorded|"
    r"^\s*-\s*(Rejected|Filed|Deferred)\b|"
    r"(failure-ledger |ledger )?(triage|sweep)( run| batch| report| complete| summary))",
    re.IGNORECASE,
)

DATE_PAT = re.compile(r"20\d\d-\d\d-\d\d")


def cid_of(snippet_prefix):
    """Content identity: hash of the snippet prefix exactly as the
    legacy keys carried it (stripped line, 60-char cut, rstripped)."""
    return hashlib.sha256(snippet_prefix.rstrip().encode("utf-8")).hexdigest()[:16]


def cid_from_legacy_key(key):
    """Derive a cid from a legacy `file:line:snippet` key. The snippet
    component is everything after the second colon (snippets may
    themselves contain colons)."""
    parts = key.split(":", 2)
    snippet = parts[2] if len(parts) == 3 else key
    return cid_of(snippet)


def parse_key(key):
    """Accept a printed `c:<hash>` token or a legacy key; return cid."""
    key = key.strip()
    if key.startswith("c:"):
        return key[2:]
    return cid_from_legacy_key(key)


def daily_notes(days, since):
    cutoff = dt.date.today() - dt.timedelta(days=days)
    if since:
        cutoff = max(cutoff, dt.date.fromisoformat(since))
    out = []
    for name in sorted(os.listdir(MEMORY)):
        m = re.fullmatch(r"(20\d\d-\d\d-\d\d)\.md", name)
        if not m:
            continue
        d = dt.date.fromisoformat(m.group(1))
        if d >= cutoff:
            out.append((d, os.path.join(MEMORY, name)))
    return out


def logged_signals(failures_path):
    dates, words = set(), set()
    try:
        text = open(failures_path).read()
    except FileNotFoundError:
        return dates, words
    dates = set(DATE_PAT.findall(text))
    for line in text.splitlines():
        if line.startswith("## "):
            words.update(w.lower() for w in re.findall(r"[a-z]{4,}", line))
    return dates, words


def load_reviewed(path):
    """Return {cid: row}. Handles new rows ({"cid": ...}) and legacy
    rows ({"key": "file:line:snippet"}) transparently."""
    done = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if "cid" in r:
                    done[r["cid"]] = r
                elif "key" in r:
                    done[cid_from_legacy_key(r["key"].rstrip())] = r
    except FileNotFoundError:
        pass
    return done


def load_state(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"pending": {}}


def save_state(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, path)


def is_candidate(line):
    if NOISE.search(line):
        return False
    if len(line.strip()) < 40 or len(line.strip()) > 600:
        return False
    if STRONG.search(line):
        return True
    if WEAK.search(line) and CORROBORATE.search(line):
        return True
    return False


def scan_notes(notes, reviewed):
    cands = []
    seen = set()
    for d, path in notes:
        with open(path) as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            if not is_candidate(line):
                continue
            snippet = line.strip()
            cid = cid_of(snippet[:60])
            if cid in reviewed or cid in seen:
                continue
            seen.add(cid)
            cands.append(
                {
                    "cid": cid,
                    "key": f"c:{cid}",
                    "date": str(d),
                    "source": f"{os.path.basename(path)}:{i}",
                    "snippet": snippet,
                }
            )
    return cands


def scan_agents_lessons(logged_dates, logged_words, reviewed):
    cands = []
    try:
        lines = open(AGENTS).readlines()
    except FileNotFoundError:
        return cands
    for i, line in enumerate(lines, 1):
        # Long AGENTS.md lines pack several lessons; scan per sentence.
        chunks = re.split(r"(?<=[.;])\s+(?=[A-Z*`(\"])", line.strip())
        for chunk in chunks:
            dates = DATE_PAT.findall(chunk)
            if not dates:
                continue
            if not (STRONG.search(chunk)
                    or (WEAK.search(chunk) and CORROBORATE.search(chunk))):
                continue
            if NOISE.search(chunk):
                continue
            if len(chunk) < 40 or len(chunk) > 600:
                continue
            cid = cid_of(chunk[:60])
            if cid in reviewed:
                continue
            if any(d in logged_dates for d in dates):
                continue
            words = set(w.lower() for w in re.findall(r"[a-z]{4,}", chunk))
            if logged_words and len(words & logged_words) >= 4:
                continue
            cands.append(
                {
                    "cid": cid,
                    "key": f"c:{cid}",
                    "date": dates[0],
                    "source": f"AGENTS.md:{i}",
                    "snippet": chunk,
                }
            )
    return cands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--since")
    ap.add_argument("--reviewed", default=DEFAULT_REVIEWED)
    ap.add_argument("--failures", default=DEFAULT_FAILURES)
    ap.add_argument("--state", default=DEFAULT_STATE)
    ap.add_argument("--mark-reviewed", nargs="+", metavar="KEY DISPOSITION [NOTE]",
                    help="record a disposition: file | reject | defer (note optional)")
    args = ap.parse_args()

    if args.mark_reviewed:
        key = args.mark_reviewed[0]
        cid = parse_key(key)
        disp = args.mark_reviewed[1]
        note = " ".join(args.mark_reviewed[2:])
        assert disp in ("file", "reject", "defer"), \
            "disposition must be file|reject|defer"
        with open(args.reviewed, "a") as f:
            f.write(json.dumps({
                "cid": cid,
                "disposition": disp,
                "note": note,
                "at": dt.datetime.now().isoformat(timespec="seconds"),
            }) + "\n")
        # A dispositioned candidate leaves the pending register.
        state = load_state(args.state)
        if cid in state.get("pending", {}):
            del state["pending"][cid]
            save_state(args.state, state)
        print(f"recorded {disp}: c:{cid}")
        return

    logged_dates, logged_words = logged_signals(args.failures)
    reviewed = load_reviewed(args.reviewed)
    notes = daily_notes(args.days, args.since)

    cands = scan_notes(notes, reviewed)
    cands += scan_agents_lessons(logged_dates, logged_words, reviewed)

    # Vanished-candidate tracking: diff this scan's undispositioned set
    # against the pending register from previous scans.
    today = str(dt.date.today())
    state = load_state(args.state)
    pending = state.get("pending", {})
    found = {c["cid"]: c for c in cands}
    vanished = []
    for cid, rec in list(pending.items()):
        if cid in reviewed:
            del pending[cid]  # dispositioned elsewhere; prune quietly
        elif cid not in found:
            if not rec.get("vanished_since"):
                rec["vanished_since"] = today
            vanished.append(rec | {"cid": cid, "key": f"c:{cid}"})
    for cid, c in found.items():
        rec = pending.get(cid, {})
        rec.update({
            "snippet": c["snippet"],
            "source": c["source"],
            "first_seen": rec.get("first_seen", today),
            "last_seen": today,
            "vanished_since": None,
        })
        pending[cid] = rec
    state["pending"] = pending
    save_state(args.state, state)

    if not cands and not vanished:
        print("No new failure-ledger candidates.")
        return

    if cands:
        print(f"# Failure-ledger candidates ({len(cands)} new)\n")
        print("Disposition each: file it in failures.md, or record with")
        print("`--mark-reviewed <key> reject|defer <note>`. The script never files.\n")
        for c in cands:
            print(f"## {c['source']} (note date {c['date']})")
            print(f"key: `{c['key']}`")
            print(f"> {c['snippet']}\n")

    if vanished:
        print(f"# VANISHED candidates ({len(vanished)}) — pending at the "
              "previous scan, absent now, no disposition recorded.\n")
        print("These fell out of the notes without being filed, rejected, "
              "or deferred. Disposition each from the snippet below, or "
              "investigate where the text went.\n")
        for v in vanished:
            print(f"## last seen {v.get('source')} "
              f"(first seen {v.get('first_seen')}, "
              f"vanished {v.get('vanished_since')})")
            print(f"key: `{v['key']}`")
            print(f"> {v.get('snippet')}\n")


if __name__ == "__main__":
    main()
