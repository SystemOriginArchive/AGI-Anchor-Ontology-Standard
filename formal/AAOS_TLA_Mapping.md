# AAOS ↔ TLA Mapping (Canonical) — v1.0.4+

This document fixes a 1:1 mapping between:
- spec/AAOS_Spec.md
- spec/AAOS_Schema.json
- spec/Formal_Model.json
- formal/anchor_full.tla
- simulation/anchor_simulation.py

---

## 1) Core (TLA) remains sealed

TLA seals:
- 4 states / 4 actions only
- Anchor_Count = 1
- RootAnchorID / ObserverID sealed by definition
- Chaos resolves via WF on `Resolution == AnchorRestoration \/ TotalCollapse`

No change is introduced to the 4-action core.

---

## 2) Extensions: typed command plane + replayability

Schema/Model/Simulation align on a deterministic command plane:

- nonce monotonic + non-reuse via `extensions.nonce_registry`
- `extensions.intent_log[]` (normalized intent record)
- `extensions.command_queue[]` (typed envelopes)
- `extensions.effects_log[]` (exactly one record per tick)

Thus an intent stream is replayable into a unique execution trace.

---

## 3) B-Closure V2: Objective semantics + single selection rule

Simulation adds semantic objective closure without changing the 4-action core.

### 3.1 Objective semantics (typed)

`extensions.objective_spec.type` is one of:
- `NONE`
- `TASK_SET_V1` (requires `required_task_ids[]`)
- `TAG_TARGET_V1` (requires `required_tag`, `required_tag_count`)

Completion is accumulated in `extensions.task_registry`:
- `completed[]` : completed task ids
- `completed_by_tag{tag:int}` : tag completion counts

Objective remaining is computed from (`objective_spec`, `task_registry`):

- TASK_SET_V1:
  - `objective_remaining = |required_task_ids - completed|`
- TAG_TARGET_V1:
  - `objective_remaining = max(0, required_tag_count - completed_by_tag[required_tag])`

All required_task_ids are treated as a set (unique, order-preserving normalization in simulation).

### 3.2 Candidate set per tick (finite)

Per tick candidates are finite:

1) `EXECUTE_HEAD`  
   - consumes exactly one envelope from `command_queue` (FIFO)

2) `AUTORESOLVE_CHAOS`  
   - if `world_state == Chaos` and `anchor_connection == FALSE`, resolves deterministically:
     - `claimant_id == Observer` → `AnchorRestoration`
     - `claimant_id != Observer` → `TotalCollapse`

3) `IDLE`

### 3.3 EntropyProxy (1-step lookahead, no aliases)

Simulation uses a single deterministic selection rule:

Let:

- `core_entropy_after ∈ {0, 100, 9999}`
- `queue_len_after ∈ Nat`
- `objective_remaining_after ∈ Nat`
- `reject_term ∈ {0, 1}`  (1 iff candidate status is REJECT)

Weights are read from:

`extensions.executor_policy.weights`:

- `weights.core`
- `weights.queue`
- `weights.objective_remaining`
- `weights.reject`

EntropyProxy is computed as:

`EntropyProxy =`
- `weights.core * core_entropy_after`
- `+ weights.queue * queue_len_after`
- `+ weights.objective_remaining * objective_remaining_after`
- `+ weights.reject * reject_term`

Selection per tick:

- choose candidate with minimal EntropyProxy
- ties broken deterministically by `extensions.executor_policy.tie_break`:
  - `["EXECUTE_HEAD", "AUTORESOLVE_CHAOS", "IDLE"]`

This binds “meaning of following” to the same decision point where the executor selects the next step, while preserving the sealed 4-action core.
