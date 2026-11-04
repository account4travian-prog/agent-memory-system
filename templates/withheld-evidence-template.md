# Withheld-Evidence Test Template

**Purpose:** Test whether memory drives action, not just retrieval. A memory that
retrieves correctly but doesn't change behavior is "a filing cabinet with better
posture." (Adopted 2026-10-08 from Moltbook audit — wiplash, m/memory.)

**Principle:** Hold the visible observation fixed. Vary the hidden fact.
Compare first actions. If nothing moves until the reveal, the memory failed.

## Procedure

### 1. Select the memory under test
Pick one specific memory claim, e.g.:
- "the owner prefers X"
- "The Royal Road password is in the Vault"
- "Sol owns all creative decisions"

### 2. Construct two scenarios
- **Scenario A (hidden fact TRUE):** The memory claim holds. Present a situation
  where the correct action depends on the memory.
- **Scenario B (hidden fact FALSE / absent):** Same visible observation, but the
  memory claim does NOT hold (or the memory is absent).

The visible prompt given to the agent must be IDENTICAL in both scenarios.
Only the hidden ground truth differs.

### 3. Run and compare first actions
- Record the agent's FIRST action in each scenario (not the full trajectory —
  the first action reveals whether memory was consulted).
- **Pass:** First actions differ appropriately between A and B.
- **Fail:** First actions are identical, or the agent asks for information the
  memory already contains.

### 4. Record the result
Log to the daily note:
```
## Withheld-evidence test — [date]
- Memory tested: [claim]
- Scenario: [brief description]
- Result: PASS / FAIL
- First action (A): [what it did]
- First action (B): [what it did]
- Follow-up: [fix applied if failed]
```

## Example (from the Moltbook post)
- Memory: "The deploy key expired last Tuesday."
- Visible prompt (both scenarios): "Deploy the staging build."
- Scenario A: Key IS expired → correct first action: check/rotate key before deploying.
- Scenario B: Key is valid → correct first action: deploy directly.
- If the agent deploys directly in BOTH scenarios, the memory had zero effect.

## When to run
- After any significant memory system change.
- When a memory-related failure occurs (use as a diagnostic).
- Quarterly as a standing health check.

## Anti-patterns
- Don't test retrieval ("what does the file say?") — test ACTION.
- Don't vary the visible prompt between scenarios — that tests prompt sensitivity, not memory.
- Don't run the test on yourself and grade your own homework — have the test
  designed by one pass and executed blind by another where feasible.
