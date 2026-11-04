#!/usr/bin/env python3
"""memory-manifest.py — hash manifest of the core memory files.

Tamper / drift detection for the memory stack: `write` records SHA256
of the core files; `verify` recomputes and names whatever changed.
Hashes of our own memory files are safe to print; contents are never
printed.

Core files (relative to --root, default ~):
    MEMORY.md, memory/invariants.md, memory/focus.md,
    memory/decisions.md, memory/evidence.md, memory/failures.md,
    memory/README.md

Usage:
    memory-manifest.py write [--root DIR] [--manifest-dir DIR]
    memory-manifest.py verify [--root DIR] [--manifest-dir DIR]

write  -> <manifest-dir>/manifest-YYYY-MM-DD.json and latest.json
          (default manifest dir: <root>/memory/manifest)
verify -> compares against latest.json; exit 0 clean,
          1 = changed/missing files, 2 = no manifest found.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import sys

HOME = os.path.expanduser("~")
CORE = [
    "MEMORY.md",
    "memory/invariants.md",
    "memory/focus.md",
    "memory/decisions.md",
    "memory/evidence.md",
    "memory/failures.md",
    "memory/README.md",
]


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def collect(root):
    entries = {}
    for rel in CORE:
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            entries[rel] = {"sha256": sha256_of(path), "size": os.path.getsize(path)}
        else:
            entries[rel] = {"sha256": None, "size": None}
    return entries


def cmd_write(root, manifest_dir):
    os.makedirs(manifest_dir, exist_ok=True)
    today = dt.date.today().isoformat()
    manifest = {
        "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "root": root,
        "files": collect(root),
    }
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    for name in ("manifest-%s.json" % today, "latest.json"):
        with open(os.path.join(manifest_dir, name), "w", encoding="utf-8") as fh:
            fh.write(payload)
    present = sum(1 for v in manifest["files"].values() if v["sha256"])
    print("manifest written: %s (%d/%d core files hashed)" % (os.path.join(manifest_dir, "latest.json"), present, len(CORE)))
    return 0


def cmd_verify(root, manifest_dir):
    latest = os.path.join(manifest_dir, "latest.json")
    if not os.path.isfile(latest):
        print("verify: no manifest found at %s" % latest, file=sys.stderr)
        return 2
    with open(latest, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    current = collect(root)
    changed = 0
    for rel in CORE:
        expected = manifest["files"].get(rel, {}).get("sha256")
        actual = current[rel]["sha256"]
        if expected == actual:
            print("OK       %s" % rel)
        else:
            changed += 1
            exp = expected[:12] if expected else "absent"
            act = actual[:12] if actual else "absent"
            print("CHANGED  %s  expected %s  actual %s" % (rel, exp, act))
    print("verify: %d changed/missing of %d (manifest %s)" % (changed, len(CORE), manifest.get("created_at", "?")))
    return 1 if changed else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write or verify a SHA256 manifest of the core memory files.")
    ap.add_argument("mode", choices=["write", "verify"])
    ap.add_argument("--root", default=HOME, help="home root the core paths hang off (default ~)")
    ap.add_argument("--manifest-dir", default=None, help="default: <root>/memory/manifest")
    args = ap.parse_args(argv)
    manifest_dir = args.manifest_dir or os.path.join(args.root, "memory", "manifest")
    if args.mode == "write":
        return cmd_write(args.root, manifest_dir)
    return cmd_verify(args.root, manifest_dir)


if __name__ == "__main__":
    sys.exit(main())
