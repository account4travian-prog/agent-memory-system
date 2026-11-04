#!/usr/bin/env python3
"""Check the ~/memory stack files: structure, required fields, resolvable sources.

Exit 0 = all checks pass. Exit 1 = one or more failures (details on stdout).
"""
import os
import re
import sys

HOME = os.path.expanduser("~")
MEM = os.path.join(HOME, "memory")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def entries(text):
    """Split markdown into (heading, body) per ## entry."""
    parts = re.split(r"^## ", text, flags=re.M)
    out = []
    for p in parts[1:]:
        heading, _, body = p.partition("\n")
        out.append((heading.strip(), body))
    return out


# --- existence ---
files = ["README.md", "active.md", "decisions.md", "evidence.md", "failures.md"]
for fn in files:
    p = os.path.join(MEM, fn)
    check(f"exists:{fn}", os.path.isfile(p) and os.path.getsize(p) > 0,
          p if not (os.path.isfile(p)) else f"{os.path.getsize(p)} bytes")

text = {fn: read(os.path.join(MEM, fn)) for fn in files}

# --- README ---
check("readme:read-first-order", "Read-first order" in text["README.md"])
check("readme:governing-rule", "does not prove reality" in text["README.md"])
check("readme:decay-policy", "Decay changes retrieval priority only" in text["README.md"])
check("readme:write-ahead", "Write-ahead convention" in text["README.md"])
check("readme:no-secrets", "does not store secrets" in text["README.md"])

# --- active.md ---
check("active:not-evidence-marker", "not evidence" in text["active.md"].lower())
check("active:objective", "## Current objective" in text["active.md"])
check("active:next-action", "## Next action" in text["active.md"])
check("active:dated", bool(re.search(r"20\d\d-\d\d-\d\d", text["active.md"])))

# --- decisions.md ---
dec_fields = ["**Status:**", "**Decision:**", "**Reason:**",
              "**Alternatives considered:**", "**Reversal condition:**"]
decs = entries(text["decisions.md"])
check("decisions:entry-count", len(decs) >= 1, f"{len(decs)} entries")
for i, (h, b) in enumerate(decs):
    check(f"decisions:entry{i}:date", bool(re.match(r"20\d\d-\d\d-\d\d", h)), h[:60])
    for f in dec_fields:
        check(f"decisions:entry{i}:has:{f.strip('*:')}", f in b, h[:60])

# --- failures.md ---
fail_fields = ["**Trigger:**", "**Observed failure:**", "**Independent catcher:**",
               "**Rule produced:**", "**Disposition:**"]
fails = entries(text["failures.md"])
check("failures:entry-count", len(fails) >= 1, f"{len(fails)} entries")
for i, (h, b) in enumerate(fails):
    check(f"failures:entry{i}:date", bool(re.match(r"20\d\d-\d\d-\d\d", h)), h[:60])
    for f in fail_fields:
        check(f"failures:entry{i}:has:{f.strip('*:')}", f in b, h[:60])

# --- evidence.md ---
lines = text["evidence.md"].splitlines()
rows = [l for l in lines if l.startswith("|") and "---" not in l][1:]  # skip header
check("evidence:row-count", len(rows) >= 1, f"{len(rows)} rows")
for i, r in enumerate(rows):
    cells = [c.strip() for c in r.strip().strip("|").split("|")]
    check(f"evidence:row{i}:four-cells", len(cells) == 4, r[:80])
    if len(cells) == 4:
        check(f"evidence:row{i}:nonempty", all(cells), r[:80])
        claim, source, last_checked, gate = cells
        check(f"evidence:row{i}:date", bool(re.match(r"20\d\d-\d\d-\d\d", last_checked)),
              f"{claim[:40]} / {last_checked}")
        for m in re.findall(r"(~/[^\s,;`]+|/home/user/[^\s,;`]+)", source):
            p = os.path.expanduser(m)
            check(f"evidence:row{i}:source-exists", os.path.exists(p),
                  f"{claim[:40]} -> {m}")

failed = [r for r in results if not r[1]]
for name, ok, detail in results:
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed.")
sys.exit(1 if failed else 0)
