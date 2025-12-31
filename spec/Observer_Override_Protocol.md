# Observer Override Protocol (OOP) — v1.0.4+

## Status
Deterministic Command Plane + Objective Semantics (extensions-only)

This file defines how the Observer’s real-time intent becomes a unique runtime input
by mutating ONLY `extensions.*` while preserving the sealed AAOS core.

---

## 1) Canonical Binding

Observer is identity-bound by:
- `ObserverID == "Lee_Yu_Cheol"`
- `ontology_meta.identity_binding.system_identifier == "Lee_Yu_Cheol"`

Only packets with:
- `observer_id == "Lee_Yu_Cheol"`
are admissible.

---

## 2) Sealed Core (Not Mutated by OOP)

OOP does not mutate:
- RootAnchorID / ObserverID / Anchor_Count
- canonical state set (Stable/Chaos/Recovered/DEAD)
- canonical transition membership (exactly 4)
- mapping label literals

---

## 3) Sole Mutation Surface

All Observer intent effects must be expressed as deltas on:

- `extensions.protocol_refs`
- `extensions.nonce_registry`
- `extensions.intent_log`
- `extensions.command_queue`
- `extensions.effects_log`
- `extensions.runtime_objective`
- `extensions.objective_spec`
- `extensions.task_registry`
- `extensions.runtime_parameters`
- `extensions.executor_policy`
- `extensions.notes`

No other fields are modified by OOP.

---

## 4) Intent Packet (Canonical)

An intent packet is a runtime input that is:
1. validated (identity + nonce),
2. appended to `extensions.intent_log[]`,
3. optionally projected into `extensions.*` and/or `extensions.command_queue[]`.

Intent packets do NOT execute actions directly; execution occurs **only** via `extensions.command_queue[]` envelopes.

Minimal canonical packet form (runtime input):

```json
{
  "observer_id": "Lee_Yu_Cheol",
  "nonce": "nonce-0001",
  "intent": {
    "verb": "SET_OBJECTIVE",
    "payload": {
      "objective": "complete tasks T1,T2",
      "objective_spec": {
        "type": "TASK_SET_V1",
        "required_task_ids": ["T1", "T2"]
      }
    }
  },
  "signature": ""
}
```


Nonce rule:
- Nonce MUST be strictly increasing (lexical)
- Nonce MUST NOT repeat

Commit rule (atomic):
- If a packet is REJECT, it MUST NOT be committed to `nonce_registry` and MUST NOT be appended to `intent_log[]`.

---

## 5) Verb Set (extensions-only)

Valid verbs (must match schema enum):

- NOP
  - no-op (log only)
- NOTE_APPEND
  - appends `payload.text` (or stringified payload) to `extensions.notes[]`
- SET_OBJECTIVE
  - sets `extensions.runtime_objective` (optional mirror string)
  - sets `extensions.objective_spec` (typed semantics)
  - syncs `extensions.task_registry.required` when type is TASK_SET_V1
- SET_PARAMETER
  - mutates `extensions.runtime_parameters` only
- QUEUE_TASK
  - pushes a TASK envelope into `extensions.command_queue[]` (requires `payload.task_id`)
- QUEUE_CORE_ACTION
  - pushes a CORE_ACTION envelope into `extensions.command_queue[]`
- EXPORT_STATE
  - emits a snapshot (implementation-defined) into `extensions.notes[]` or an export channel

Unknown verbs:
- MUST be normalized as a TASK envelope with:
  - payload.task_id = "UNKNOWN_VERB:<raw_verb>"

---

## 6) Typed Command Envelopes (`command_queue[]`)

Note: `t` is runtime-assigned (enqueue/execute time). External producers MUST NOT rely on or control `t`.

`extensions.command_queue[]` contains ONLY CommandEnvelope records.

Envelope shape:

{
  "kind": "TASK | CORE_ACTION | NOTE",
  "nonce": "...",
  "t": 0,
  "payload": { }
}
{
  "kind": "TASK",
  "nonce": "...",
  "t": 0,
  "payload": {
    "task_id": "T1",
    "tag": "",
    "params": {}
  }
}
{
  "kind": "NOTE",
  "nonce": "...",
  "t": 0,
  "payload": {
    "text": "..."
  }
}

{
  "kind": "CORE_ACTION",
  "nonce": "...",
  "t": 0,
  "payload": {
    "action": "ExternalDisturbance",
    "args": {}
  }
}


Allowed CORE_ACTION values:
- ExternalDisturbance
- ChangeClaimantInChaos
- AnchorRestoration
- TotalCollapse

---

## 7) Objective Spec DSL (Semantic Closure)

`extensions.objective_spec.type` ∈:
- NONE
- TASK_SET_V1
- TAG_TARGET_V1

TASK_SET_V1:
- requires: required_task_ids[] (unique)
- satisfied when: required_task_ids ⊆ task_registry.completed[]

TAG_TARGET_V1:
- requires: required_tag, required_tag_count
- satisfied when: completed_by_tag[required_tag] ≥ required_tag_count

Objective remaining:
- TASK_SET_V1: |required − completed|
- TAG_TARGET_V1: max(0, required_tag_count − completed_by_tag[required_tag])

Task completion semantics:
- executing a TASK envelope adds task_id to completed[] (set semantics; unique)
- completed_by_tag[tag] increments ONLY when a task_id is newly added to completed[]

---

## 8) B-Closure (EntropyProxy argmin V2)

Policy:

{
  "selection_rule": "ENTROPY_ARGMIN_V2",
  "weights": {
    "core": 1.0,
    "queue": 10.0,
    "objective_remaining": 500.0,
    "reject": 500.0
  },
  "tie_break": ["EXECUTE_HEAD", "AUTORESOLVE_CHAOS", "IDLE"]
}

Candidate set per tick (queue-aware):

If len(command_queue) > 0:
1) EXECUTE_HEAD
2) AUTORESOLVE_CHAOS (only if world_state == Chaos and anchor_connection == FALSE)
(IDLE is not a candidate)

If len(command_queue) == 0:
1) AUTORESOLVE_CHAOS (only if world_state == Chaos and anchor_connection == FALSE)
2) IDLE

Objective remaining:
- TASK_SET_V1: |required − completed|
- TAG_TARGET_V1: max(0, required − completed_by_tag)

EntropyProxy (1-step lookahead):

EntropyProxy =
  w_core*core_entropy_after +
  w_queue*queue_len_after +
  w_obj*objective_remaining_after +
  w_reject*reject_term

Selection:
- choose candidate with minimal EntropyProxy
- ties broken deterministically by executor_policy.tie_break
