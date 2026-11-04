#!/usr/bin/env python3
"""memory-index.py — verbatim FTS5 index over the memory files.

A retrieval layer that returns SOURCE TEXT, never summaries: files are
chunked by heading / paragraph (~800 chars), stored verbatim in SQLite,
and searched with FTS5 BM25. Every hit cites file + line so any chunk
can be checked against the file it came from.

Sources (relative to --root, default ~): MEMORY.md and memory/*.md
(daily notes + ledgers). Index: ~/workspace/tools/memory-stack/memory-index.db

Usage:
    memory-index.py build [--root DIR] [--db PATH]
    memory-index.py search "query words" [--root DIR] [--db PATH] [--limit 8]
"""

import argparse
import glob
import os
import sqlite3
import sys

HOME = os.path.expanduser("~")
DEFAULT_DB = os.path.join(HOME, "workspace", "tools", "memory-stack", "memory-index.db")
CHUNK_TARGET = 800


def chunk_file(path):
    """Yield (line_start, verbatim_text) chunks split on headings and
    paragraph boundaries, flushed once a chunk passes CHUNK_TARGET."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    chunks = []
    cur = []          # list of (lineno, raw line)
    cur_len = 0

    def flush():
        nonlocal cur, cur_len
        while cur and not cur[0][1].strip():
            cur.pop(0)
        while cur and not cur[-1][1].strip():
            cur.pop()
        if cur:
            text = "".join(line for _ln, line in cur).rstrip("\n")
            if text.strip():
                chunks.append((cur[0][0], text))
        cur = []
        cur_len = 0

    for lineno, line in enumerate(lines, 1):
        is_heading = line.lstrip().startswith("#")
        is_blank = not line.strip()
        if is_heading and cur:
            flush()
        cur.append((lineno, line))
        cur_len += len(line)
        if cur_len >= CHUNK_TARGET and is_blank:
            flush()
    flush()
    return chunks


def sources(root):
    files = sorted(glob.glob(os.path.join(root, "memory", "*.md")))
    top = os.path.join(root, "MEMORY.md")
    if os.path.isfile(top):
        files.append(top)
    return files


def cmd_build(root, db):
    files = sources(root)
    if not files:
        print("build: no source files under %s" % root, file=sys.stderr)
        return 2
    if os.path.exists(db):
        os.remove(db)
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, file TEXT, line INTEGER, text TEXT)")
    conn.execute("CREATE VIRTUAL TABLE chunks_fts USING fts5(text)")
    n_chunks = 0
    for path in files:
        for line_start, text in chunk_file(path):
            cur = conn.execute("INSERT INTO chunks (file, line, text) VALUES (?, ?, ?)", (path, line_start, text))
            conn.execute("INSERT INTO chunks_fts (rowid, text) VALUES (?, ?)", (cur.lastrowid, text))
            n_chunks += 1
    conn.commit()
    conn.close()
    print("build: indexed %d chunks from %d files -> %s" % (n_chunks, len(files), db))
    return 0


def fts_query(raw):
    words = [w for w in raw.replace('"', " ").split() if w]
    return " AND ".join('"%s"' % w for w in words)


def cmd_search(root, db, query, limit):
    if not os.path.isfile(db):
        print("search: no index at %s (run build first)" % db, file=sys.stderr)
        return 2
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT c.file, c.line, c.text FROM chunks_fts f JOIN chunks c ON c.id = f.rowid "
        "WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?",
        (fts_query(query), limit),
    ).fetchall()
    conn.close()
    if not rows:
        print("search: no matches for %r" % query)
        return 0
    for i, (path, line, text) in enumerate(rows, 1):
        snippet = " ".join(text.split())
        if len(snippet) > 320:
            snippet = snippet[:320] + " […]"
        print("%d. %s:%d" % (i, path, line))
        print("   %s" % snippet)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build or search the verbatim FTS5 memory index.")
    ap.add_argument("mode", choices=["build", "search"])
    ap.add_argument("query", nargs="?", help="search terms (search mode)")
    ap.add_argument("--root", default=HOME)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--limit", type=int, default=8)
    args = ap.parse_args(argv)
    if args.mode == "build":
        return cmd_build(args.root, args.db)
    if not args.query:
        print("search: a query is required", file=sys.stderr)
        return 2
    return cmd_search(args.root, args.db, args.query, args.limit)


if __name__ == "__main__":
    sys.exit(main())
