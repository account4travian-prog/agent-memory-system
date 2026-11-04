#!/usr/bin/env python3
"""secret-scan.py — scan memory files for credential-shaped strings.

Pre-write / nightly hygiene control: memory files get injected into
future sessions, so a credential-shaped string that lands in a daily
note persists. This scanner is mechanical recall, not judgment — it
prints CANDIDATES (file + line + pattern name) for disposition.

It NEVER prints a matched value: at most the first 4 characters and
the match length are reported, so the scan report itself is safe to
store and quote.

Usage:
    secret-scan.py [path ...]        # files or dirs (dirs: *.md walked)
    # default paths: ~/memory/*.md and ~/MEMORY.md

Exit status: 0 = clean, 1 = at least one candidate, 2 = usage error.
"""

import argparse
import glob
import math
import os
import re
import sys

HOME = os.path.expanduser("~")

# Specific credential shapes. Each entry: (name, regex, value group).
# group 0 = whole match; for assignment-style patterns group 1 is the
# secret value (used only for length / first-4 reporting).
PATTERNS = [
    ("openai-style-key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"), 0),
    ("github-token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), 0),
    ("aws-access-key-id", re.compile(r"AKIA[0-9A-Z]{16}"), 0),
    ("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), 0),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), 0),
    ("bearer-token", re.compile(r"(?i)bearer\s+([A-Za-z0-9._\-]{16,})"), 1),
    ("password-assignment", re.compile(r"(?i)pass(?:word|wd)\s*[:=]\s*(\S{4,})"), 1),
    ("api-key-assignment", re.compile(r"(?i)(?:api[_-]?key|secret|token)\s*[:=]\s*['\"]?([A-Za-z0-9._\-/+]{12,})"), 1),
    ("private-key-block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"), 0),
]

TOKEN_RE = re.compile(r"[A-Za-z0-9+/=_-]{40,}")
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
HASH_CONTEXT = re.compile(r"(?i)sha-?(?:256|1)?\b|hash|digest|fingerprint")
ENTROPY_MIN = 4.2  # bits/char; hex is capped at 4.0 so this targets b64-ish


def shannon(s):
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def redact(value):
    """The only permitted view of a match: first 4 chars + length."""
    return "%s…(len %d)" % (value[:4], len(value))


def scan_file(path, out):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError as exc:
        print("secret-scan: cannot read %s: %s" % (path, exc), file=sys.stderr)
        return 0
    found = 0
    in_fence = False
    for lineno, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        matched_spans = []
        for name, rx, group in PATTERNS:
            for m in rx.finditer(line):
                value = m.group(group)
                out.append("%s:%d: %s %s" % (path, lineno, name, redact(value)))
                matched_spans.append(m.span(group))
                found += 1
        # High-entropy long tokens, outside code fences only, and not
        # re-reporting spans already claimed by a specific pattern.
        # Path-shaped tokens are excluded: file paths and URLs dominate
        # these files and are not secrets. Discriminators: secrets do
        # not start with "/", contain no "." (no extensions/domains),
        # and a token containing "/" must be pure standard base64
        # (no "-" or "_", which paths are full of).
        if not in_fence:
            for m in TOKEN_RE.finditer(line):
                tok = m.group(0)
                if any(s <= m.start() and m.end() <= e for s, e in matched_spans):
                    continue
                if tok.startswith("/") or "." in tok:
                    continue
                if "/" in tok and not re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", tok):
                    continue
                if UUID_RE.search(tok):
                    continue  # message/citation identifiers, not credentials
                if not (any(c.isdigit() for c in tok) and any(c.isalpha() for c in tok)):
                    continue
                if shannon(tok) >= ENTROPY_MIN:
                    out.append("%s:%d: %s %s" % (path, lineno, "high-entropy-token", redact(tok)))
                    found += 1
                elif re.fullmatch(r"[0-9a-fA-F]{48,}", tok) and not HASH_CONTEXT.search(line):
                    # Pure hex caps at 4.0 bits/char so entropy never
                    # fires; long hex (>=48) is key/hash material —
                    # report it as its own, weaker class. A hex string
                    # the line itself labels as a SHA/hash/digest is a
                    # known quantity, not a candidate.
                    out.append("%s:%d: %s %s" % (path, lineno, "long-hex-string", redact(tok)))
                    found += 1
    return found


def expand(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                for name in sorted(names):
                    if name.endswith(".md"):
                        files.append(os.path.join(root, name))
        elif os.path.isfile(p):
            files.append(p)
        else:
            print("secret-scan: no such path: %s" % p, file=sys.stderr)
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scan files for credential-shaped strings (values never printed).")
    ap.add_argument("paths", nargs="*", help="files or directories (default: ~/memory/*.md, ~/MEMORY.md)")
    args = ap.parse_args(argv)

    paths = args.paths or sorted(glob.glob(os.path.join(HOME, "memory", "*.md"))) + [os.path.join(HOME, "MEMORY.md")]
    files = expand(paths)
    if not files:
        print("secret-scan: nothing to scan", file=sys.stderr)
        return 2
    out = []
    total = 0
    for f in files:
        total += scan_file(f, out)
    for line in out:
        print(line)
    print("secret-scan: %d candidate(s) in %d file(s)" % (total, len(files)), file=sys.stderr)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
