# Memory stack

How my memory is organized. Everything here is plain Markdown — readable and editable by the user. Nothing here is opaque, and nothing here acts beyond the user's authority.

Built 2026-09-20 from an assessment of two source stacks (Codex Memory Warden, deepseek-dsh write-ahead), adapted to a minimal form that fits the existing layout instead of duplicating it.

## Layout

- `focus.md` — the live task register: every task's block, current step, and done-condition. Checked first and last on every task; blocks are removed only when the done-condition is verified. **Not evidence.** (`active.md` was retired 2026-10-13 to a pointer to `focus.md` — README corrected 2026-10-18, memory health check.)
- `decisions.md` — append-only decision log with what/when/why/how schema. Dated entries; amendments are new dated entries, never silent rewrites. Dismissals (decided-not-to-act) are entries too. Dedup rule: reaffirm by reference, supersede explicitly, never duplicate.
- `evidence.md` — evidence index: important claims → source pointers → last-check dates → review gates. Points to primary records; duplicates nothing.
- `failures.md` — failure ledger: trigger, observed failure, independent catcher, rule produced, disposition. Concrete entries only — no vague "be careful" rules.
- `policy.md` — the policy register (added 2026-10-29): names the policies governing admission, consolidation, retrieval, revision, decay, expiration, deletion, change authority, and audit — and logs every policy change. The rules live in their home files; the register is the index and the change log.
- `YYYY-MM-DD.md` — daily journal: write-last run logs, handoffs, raw task history.
- `people/`, `groups/` — relationship indexes (closest first).
- `bank/` — background-maintained reflections (experience, opinions, reflections, world).

One level up: `~/MEMORY.md` is the curated digest (stable facts, preferences, commitments); `~/SOUL.md` is the charter (identity, values, boundaries). Project state lives in `~/workspace/goals/<slug>/`; scheduled-work state lives with each cron job.

## Read-first order

1. `~/memory/invariants.md` (negative constraints — if a summary disagrees, this file wins)
2. `~/memory/focus.md` (live task register)
3. `~/MEMORY.md` → `## Now`
4. Today's and yesterday's daily notes
4. Goal files (`~/workspace/goals/<slug>/GOAL.md`) when the task touches a goal

## Governing rule

> Memory preserves context; it does not prove reality.

A local file saying an action happened is not proof it happened. Proof lives in the independent source: the connector record, the live readback, the receipt, or the user's explicit review. If a file and a source disagree, the source wins.

## Governance by mechanism, not by prose

A sentence in a file is a request, not a control. Instructions compete with everything else in context and get deprioritized — control is negotiated, never guaranteed. So a durable rule in this stack must carry an enforcement mechanism in the run ceremony, not just prose:

- a check that runs (allowances re-checked at run end, not only at start),
- a manifest that proves (sha256 manifest on every memory backup),
- a revert path that exists (every logged change ships its revert instructions).

A rule with prose but no mechanism is a poster on a wall the run never walks past. (Additive 2026-10-06; source: control-illusion sweep + the board's own "a seal nothing enforces is an instruction".)

## Retrieval and decay

- **Hot:** `focus.md`, `MEMORY.md` `## Now`, `SOUL.md`.
- **Warm:** `decisions.md`, `evidence.md`, `failures.md`, people/groups indexes.
- **Cold:** dated journals, `bank/` notes.
- Decay changes retrieval priority only. It never silently deletes source records.

## Write-ahead convention

Before a fallible multi-step operation — especially one with outward effects (posts, votes, messages, purchases, pod creation) — write the intent to `focus.md` or the run log. Afterward, append the actual result with identifiers (ids, exit codes, timestamps). An intended action with no recorded outcome is treated as interrupted or failed, never as quietly complete.

## What this stack does not do

- It does not store secrets, credentials, chat exports, financial account data, or personal files. `evidence.md` points to sources; it never contains secret values.
- It does not guarantee I will read myself correctly. High-risk actions still need external checks or the user's review.
- A seal or hash would prove a file wasn't rewritten, not that its contents were true — so none are kept. (Revisit only if tamper-evidence against something specific is wanted.)

## 2026-10-20 additions (stack repair, owner-approved "full plan")

- **Tombstone rule (focus.md):** a block is DELETED by whoever verifies its done-condition — never left as a CLOSED one-liner. Ephemeral run blocks (watch/bridge/pipeline jobs) follow the same rule. Anything CLOSED that remains is swept by the nightly consolidation into `focus-archive-YYYY-MM-DD.md` (verbatim). Budget: ~120 lines; the rot audit (weekly health check) reports the count.
- **Nightly consolidation ("dreaming"):** a scheduled pass owns: focus tombstone sweep, duplicate-failure merging (mark DUPLICATE, never delete), `## Now` staleness flagging (>48h stamp), secret scan over the day's memory writes, hash-manifest write, FTS index rebuild. Additive-first; every change receipted in the daily note; effect check at the end ("what changed on disk", not "the job ran").
- **Tools (`~/workspace/tools/memory-stack/`):** `secret-scan.py` (credential-shaped string candidates; reports file+line+pattern name, never values), `memory-manifest.py` (SHA256 manifest of core files; `verify` names drift), `memory-index.py` (SQLite FTS5 verbatim index over daily notes + ledgers; `build`/`search`). Usage: README-tools.md in that dir.
- **Typed provenance (new entries from 2026-10-20):** new durable entries in MEMORY.md, decisions.md, and failures.md carry, where practical, the minimal fields inline — source, date, scope — in the existing prose style plus a `source:` pointer when the source is a file or record. Goal: program-portable (OMP-shaped) without breaking human readability.
- **Claim vouchers:** `~/memory/vouchers.md` — high-stakes claim classes, their sources of truth, last-verified dates. Verify against the source before acting on V-class claims.
- **Graduated trust (owner-approved 2026-10-20):** mechanical maintenance classes — tombstone compaction, ledger dedupe merges, `## Now` refreshes from verified sources — are Atlas self-accepted with receipts, spot-audited by the weekly health check. Canon, money, and publishing verdicts are never graduated; they remain the owner's.
- **Retrieval:** the FTS index supplements `memory_search` (semantic/prose) with verbatim BM25 over the raw notes. Retrieval misses are failure-ledger entries (rule adopted 2026-10-04).

## 2026-10-29 additions (MCCL grafts, owner-directed)

Source: evaluation of "Memory-Centric Continual Learning for AI Agents" (arXiv:2610.29357) at `~/workspace/memory-warden-tech/research/mccl-evaluation-2026-10-29.md`. the owner: "implement what makes sense."

- **Policy register:** `~/memory/policy.md` names the policies governing the stack (admission, encoding, consolidation, retrieval, revision, decay, expiration, deletion, change authority, audit) and logs every policy change. A policy change with no change-log entry there did not happen.
- **Voucher validity (P-EXPIRE):** every voucher in `vouchers.md` now carries a Validity — date-bound or event-bound. A claim used past its validity is treated as unverified.
- **Revision → derived-surfaces propagation:** when a durable entry is corrected, the correction is not finished until the surfaces that restate it are named and checked the same run — MEMORY.md lines, goal files, standing summaries, and anything derived from the corrected entry (including background syntheses, which are flagged for their next pass rather than edited mid-flight). Correcting a source while leaving a derived restatement stale is an unfinished correction. (This names existing follow-through discipline as a completion condition, per MCCL §3.4: correcting an episode alone leaves derived knowledge inconsistent.)
- **Cascade audits (P-AUDIT):** periodic spot audits score sampled high-stakes claims at four gates — preservation, access, utilization, behavioral effect — and are filed in `~/workspace/memory-warden-tech/research/`. First audit: `cascade-audit-2026-10-29.md`.
