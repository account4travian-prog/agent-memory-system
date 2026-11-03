# Agent memory system: how a persistent agent stays honest across sessions

The operating setup for Atlas, an AI agent that works for me across months of sessions: plain Markdown memory files, task registers, and verification rules designed so the agent's claims about its own work can be checked, including by me, after the fact.

**My role:** I designed the discipline layer, the file structure, the rules, and the done-conditions. Atlas works from it. I did not build the agent or its runtime; I designed the rules it operates under, and I keep correcting them.

## What is in it
- **Focus register:** every task is written down before work starts, with a done-condition and a truthful next step. The entry is deleted only when that condition is verified against a source, never because work was attempted or handed off. Before the deletion rule (2026-10-20), closed entries had grown the register to 2,841 lines, 2,008 of them tombstones.
- **Failure ledger:** a 443-line ledger in a fixed shape: trigger, observed failure, independent catcher, rule produced, disposition. A failure class that recurs twice after its lesson was adopted counts as a failed lesson.
- **Invariants file:** a short list of things that must never happen, read first on every wake. If a summary disagrees with it, the invariants win.
- **Effect verification:** a job is done when the world changed, not when the script ran. A run that completes with zero effect is a silent failure.
- **Negative-witness tests:** permission gates are tested with a deliberately invalid input alongside the real one. A gate never tested with a bad input is not a gate.

## What the record shows
The rules came from failures in the agent's own record: a delegated browser task returned a detailed capture of a conversation that never happened (2026-10-21); a stalled run was reported as progressing because its scheduler said running (2026-10-30); the register was found at zero bytes and was treated as a loss incident, never as a clean slate (2026-10-22). The 2026-11-01 audit's first recurrence tally named four failed lessons, and the same audit found the freshness stamp on the curated memory 12 days stale.

This repo holds the design, the rules, and synthetic examples. The real ledgers stay private because they contain personal material, not just method.
