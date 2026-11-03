# Agent memory system — how a persistent agent stays honest across sessions

The operating setup for Atlas, an AI agent that works for me across months of sessions: memory files, task registers, and verification rules designed so the agent's claims about its own work can be checked — including by me, after the fact.

My role: I designed the discipline layer — the file structure, the rules, and the done-conditions. Atlas runs on it day to day. I'm not going to claim I "architected a memory architecture" in the abstract; what I built is a set of files and rules, and the record of where they failed and got fixed.

## What is in it
- **Focus register:** every task is written down before work starts, its current step kept truthful, and the entry is deleted only when the done-condition is checked — not when the work feels finished.
- **Failure ledger:** every failure gets a trigger, a catcher, a rule, and a disposition. A failure class that recurs twice after its fix counts as a failed fix and gets surfaced as one.
- **Invariants file:** a short list of things that must never happen, read first on every wake. If a summary disagrees with it, the invariants win.
- **Effect verification:** a job is done when the world changed — the message is in the thread, the file is at the destination, the post is live — not when the script ran. A run that completes with zero effect is a silent failure.
- **Negative-witness tests:** permission gates are tested with a deliberately invalid input alongside the real one. A gate never tested with a bad input is not a gate.

## Why it exists
Long-running agents drift, overclaim, and quietly lose track of what they actually did. This setup is the countermeasure I use: claims are cheap, so the system routes around them — every "done" needs an independent read, and the failures are written down where the next session has to see them.

This repo holds the design, the rules, and synthetic examples. The real ledgers stay private — they contain my life, not just the method.
