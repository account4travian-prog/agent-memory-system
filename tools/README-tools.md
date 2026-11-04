# Memory-stack tools

Small Python3-stdlib tools for the memory stack's hygiene layer.
Built 2026-10-20 (stack repair, focus block F-stack-repair-1020).
Companion: `failure-candidates.py` (failure-ledger candidate sweep).

## secret-scan.py — credential-shaped string scanner

Scans memory writes for credential-shaped strings before they can
persist into future sessions' context. Reports **candidates only**:
`file:line: pattern-name first4…(len N)` — a matched value is never
printed (at most its first 4 characters and length).

    secret-scan.py [path ...]     # files or dirs (dirs walk *.md)
                                  # default: ~/memory/*.md + ~/MEMORY.md
    # exit 0 clean · 1 candidates found · 2 usage error

Patterns: `sk-` keys, `ghp_`-family tokens, `AKIA` ids, `xox[bap]-`
tokens, JWTs, Bearer values, password/api-key assignments, private-key
blocks, high-entropy tokens (≥40 chars, ≥4.2 bits/char), and unlabelled
long hex (≥48). Named patterns scan everywhere; the entropy class runs
outside code fences only and excludes path-shaped tokens, UUID-bearing
identifiers, and hex the line itself labels as a SHA/hash/digest —
those three exclusions took the real-corpus report from 705 noise hits
to 7 reviewable candidates. Candidates still need a human/agent
disposition; expect occasional prose false positives (e.g. "Bearer"
in a sentence).

## memory-manifest.py — core-file hash manifest

Tamper/drift detection for the core memory files (MEMORY.md,
invariants, focus, decisions, evidence, failures, memory/README).

    memory-manifest.py write  [--root DIR] [--manifest-dir DIR]
    memory-manifest.py verify [--root DIR] [--manifest-dir DIR]
    # write -> <root>/memory/manifest/manifest-YYYY-MM-DD.json + latest.json
    # verify exit 0 clean · 1 changed/missing · 2 no manifest

`verify` prints one line per core file; CHANGED lines carry expected
vs actual 12-char hash prefixes (hashes of our own files are safe to
print; contents never are). `--root`/`--manifest-dir` exist so the
tool is testable against fixture copies without touching real memory.
Known limits: a file absent at write time and still absent at verify
reads as OK; the dated filename uses the VM's system date.

## memory-index.py — verbatim FTS5 retrieval index

SQLite FTS5 index over MEMORY.md + ~/memory/*.md, chunked by heading /
paragraph (~800 chars). Chunks are **exact source text** (verified:
chunk boundaries reproduce source lines byte-for-byte), each stored
with file + line offset; search returns BM25-ranked citations, never
summaries.

    memory-index.py build [--root DIR] [--db PATH]
    memory-index.py search "query words" [--limit 8]
    # index: ~/workspace/tools/memory-stack/memory-index.db
    # full rebuild at build time: 46 files -> 7,249 chunks, ~1.5 s

Query terms are ANDed. Rebuild after bulk memory edits (the nightly
consolidation does this). Relevance is BM25 over verbatim text — good
for distinctive phrases ("hash-bound acceptance", "tombstone"), weaker
for generic word triples; that's the honest trade for never serving a
paraphrase as a source.

## Positive-control tests (run at build, 2026-10-20)

- secret-scan: planted `sk-proj-FAKE…` in a temp file → flagged
  (exit 1), report contained **zero** occurrences of the full value;
  clean file with a path, a `message:` UUID citation, and a labelled
  SHA256 → exit 0.
- manifest: fixture root with copies of 3 core files → write + verify
  clean (exit 0); appended a line to the fixture invariants copy →
  verify named `memory/invariants.md` CHANGED with both hash prefixes
  (exit 1). Real write + verify: 7/7 OK.
- index: real build (46 files, 7,249 chunks); searches for
  "hash-bound acceptance" (top hit: decisions.md:169, the decision
  itself), "Cash App Borrow", and "focus register budget" all returned
  real cited passages; a chunk's first line was byte-compared against
  its source line — identical.
