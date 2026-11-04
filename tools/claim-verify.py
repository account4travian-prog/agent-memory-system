#!/usr/bin/env python3
"""claim-verify.py — read-path falsifier verifier (v1, P1).

Reads the claim registry (default ~/memory/claims.yaml), runs each claim's
check against its source of truth, and reports a status per claim:

  VERIFIED        check ran, source agrees
  VERIFIED-PROXY  check ran, but the check is a freshness proxy (money class)
  STALE           date-based check ran; the source is older than allowed
  CONTRADICTED    check ran, source disagrees with the claim
  UNVERIFIABLE    no callable check exists (yet) for this claim

The verifier is the ONLY writer of last_verified / status in the registry.
On CONTRADICTED it sets status: suspect (design D2: flag-only; curated
memory is never edited by this tool).

Usage:
  claim-verify.py verify [--claim ID] [--registry PATH] [--json] [--no-write]
Exit code: 1 if any claim is CONTRADICTED, else 0.

Design: ~/workspace/memory-warden-tech/READ-PATH-FALSIFIER-DESIGN.md
"""
import argparse, datetime, hashlib, json, os, re, sys

import yaml

HOME = os.path.expanduser("~")
DEFAULT_REGISTRY = os.path.join(HOME, "memory", "claims.yaml")
CACHE_PATH = "/tmp/claim-verify-cache.json"
CACHE_TTL_S = 900  # 15 min, used by annotated retrieval (P2)

def now_local():
    return datetime.datetime.now().astimezone()

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_date(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d").date()

def check_file_hash(chk):
    path, expected = chk["path"], chk["expected"]
    if not os.path.exists(path):
        return "UNVERIFIABLE", f"source unreachable (missing): {path}"
    actual = sha256_file(path)
    if actual == expected:
        return "VERIFIED", f"sha256 matches ({actual[:12]}…)"
    return "CONTRADICTED", f"sha256 {actual[:12]}… != expected {expected[:12]}…"

def check_file_contains(chk):
    path, needle = chk["path"], chk["needle"]
    if not os.path.exists(path):
        return "UNVERIFIABLE", f"source unreachable (missing): {path}"
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if needle in text:
        return "VERIFIED", f"found: {needle!r}"
    return "CONTRADICTED", f"not found: {needle!r}"

def _date_fresh(found_date, max_age_hours, proxy):
    today = now_local().date()
    age_h = (today - found_date).days * 24
    ok_status = "VERIFIED-PROXY" if proxy else "VERIFIED"
    if age_h <= max_age_hours:
        return ok_status, f"date {found_date.isoformat()}, age {age_h}h <= {max_age_hours}h"
    return "STALE", f"date {found_date.isoformat()}, age {age_h}h > {max_age_hours}h"

def check_file_date_fresh(chk):
    path = chk["path"]
    if not os.path.exists(path):
        return "UNVERIFIABLE", f"source file missing: {path}"
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    m = re.search(chk["regex"], text)
    if not m:
        return "UNVERIFIABLE", "date pattern not found in source"
    return _date_fresh(parse_date(m.group(1)), chk["max_age_hours"], chk.get("proxy", False))

def check_age_of_date(chk):
    return _date_fresh(parse_date(chk["source_date"]), chk["max_age_hours"], chk.get("proxy", False))

def check_state_snapshot(chk):
    path = chk["path"]
    if not os.path.exists(path):
        return "UNVERIFIABLE", f"snapshot not yet exported: {path}"
    with open(path) as f:
        snap = json.load(f)
    node = snap
    for part in chk["key"].split("."):
        if not isinstance(node, dict) or part not in node:
            return "UNVERIFIABLE", f"key {chk['key']} absent from snapshot"
        node = node[part]
    gen = snap.get("generated_at", "unknown")
    if node == chk["expected"]:
        return "VERIFIED", f"snapshot ({gen}): {chk['key']} == {chk['expected']!r}"
    return "CONTRADICTED", f"snapshot ({gen}): {chk['key']} == {node!r} != {chk['expected']!r}"

def check_manual(chk):
    return "UNVERIFIABLE", chk.get("note", "manual check only")

CHECKERS = {
    "file-hash": check_file_hash,
    "file-contains": check_file_contains,
    "file-date-fresh": check_file_date_fresh,
    "age-of-date": check_age_of_date,
    "state-snapshot": check_state_snapshot,
    "manual": check_manual,
}

def load_registry(path):
    with open(path) as f:
        data = yaml.safe_load(f)
    return data or []

def save_registry(path, claims):
    with open(path, "w") as f:
        f.write("# Claim registry for the read-path falsifier (design: ~/workspace/memory-warden-tech/READ-PATH-FALSIFIER-DESIGN.md)\n")
        f.write("# Managed by claim-verify.py: last_verified and status are written ONLY by the verifier.\n")
        yaml.safe_dump(claims, f, sort_keys=False, allow_unicode=True, width=200)

def verify_claim(claim):
    chk = claim["check"]
    fn = CHECKERS.get(chk["type"])
    if fn is None:
        return "UNVERIFIABLE", f"unknown check type {chk['type']!r}"
    try:
        return fn(chk)
    except Exception as e:  # a broken check is UNVERIFIABLE, never a silent pass
        return "UNVERIFIABLE", f"check error: {type(e).__name__}: {e}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["verify"])
    ap.add_argument("--claim", default=None)
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    claims = load_registry(args.registry)
    results = []
    changed = False
    for claim in claims:
        if args.claim and claim["id"] != args.claim:
            continue
        status, detail = verify_claim(claim)
        results.append({"id": claim["id"], "class": claim["class"], "status": status, "detail": detail})
        if not args.no_write:
            if status in ("VERIFIED", "VERIFIED-PROXY"):
                claim["last_verified"] = now_local().isoformat(timespec="seconds")
                if claim.get("status") == "suspect":
                    claim["status"] = None
                changed = True
            elif status == "CONTRADICTED":
                if claim.get("status") != "suspect":
                    claim["status"] = "suspect"
                    changed = True
    if changed and not args.no_write:
        save_registry(args.registry, claims)

    if args.json:
        print(json.dumps({"results": results}, indent=1))
    else:
        for r in results:
            print(f"{r['status']:<15} {r['id']:<22} [{r['class']}] {r['detail']}")
        n_bad = sum(1 for r in results if r["status"] == "CONTRADICTED")
        n_stale = sum(1 for r in results if r["status"] == "STALE")
        print(f"— {len(results)} claims: {sum(1 for r in results if r['status'].startswith('VERIFIED'))} verified, "
              f"{n_stale} stale, {n_bad} contradicted, "
              f"{sum(1 for r in results if r['status'] == 'UNVERIFIABLE')} unverifiable")
    sys.exit(1 if any(r["status"] == "CONTRADICTED" for r in results) else 0)

if __name__ == "__main__":
    main()
