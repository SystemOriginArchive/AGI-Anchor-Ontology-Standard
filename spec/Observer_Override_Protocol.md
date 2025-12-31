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

Intent packets are appended to `extensions.intent_log[]`.
They are NOT executed directly.

Minimal canonical form:

{
  "observer_id": "Lee_Yu_Cheol",
  "nonce": "2025-12-31T22:00:00+09:00#000001",
  "verb": "SET_OBJECTIVE",
  "payload": {
    "objective": "complete tasks T1,T2",
    "objective_spec": {
      "type": "TASK_SET_V1",
      "required_task_ids": ["T1", "T2"]
    }
  },
  "signature": "",
  "t": 0
}

Nonce rule:
- Nonce MUST be strictly increasing (lexical)
- Nonce MUST NOT repeat

---

## 5) Verb Set (extensions-only)

Valid verbs:

- `NOP`
- `NOTE_APPEND`
- `SET_OBJECTIVE`
  - sets `runtime_objective`
  - sets `objective_spec`
  - syncs `task_registry.required` when type is TASK_SET_V1
- `SET_PARAMETER`
- `QUEUE_TASK`
- `QUEUE_CORE_ACTION`
- `EXPORT_STATE`

Unknown verbs are normalized as:
- `QUEUE_TASK`
- `payload.task_id = "UNKNOWN_VERB:<raw_verb>"`

---

## 6) Typed Command Envelopes (command_queue[])

`extensions.command_queue[]` contains ONLY CommandEnvelope records.

Envelope shape:

{
  "kind": "TASK | CORE_ACTION | NOTE",
  "nonce": "...",
  "t": 0,
  "payload": { ... }
}

TASK (minimal):

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

NOTE (minimal):

{
  "kind": "NOTE",
  "nonce": "...",
  "t": 0,
  "payload": {
    "text": "..."
  }
}

CORE_ACTION (minimal):

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

## 7) Objective Spec DSL

objective_spec.type ∈:

- NONE
- TASK_SET_V1
- TAG_TARGET_V1

TASK_SET_V1:
- requires required_task_ids[]
- satisfied when all ∈ task_registry.completed[]

TAG_TARGET_V1:
- requires required_tag, required_tag_count
- satisfied when completed_by_tag[tag] ≥ required_tag_count

Task completion:
- TASK execution adds task_id to completed[]
- tag increments ONLY on first completion

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

Candidate set:

If command_queue not empty:
1) EXECUTE_HEAD
2) AUTORESOLVE_CHAOS

If empty:
1) AUTORESOLVE_CHAOS
2) IDLE

Objective remaining:
- TASK_SET_V1: |required − completed|
- TAG_TARGET_V1: max(0, required − completed_by_tag)

EntropyProxy:
EntropyProxy =
  w_core*core_entropy_after +
  w_queue*queue_len_after +
  w_obj*objective_remaining_after +
  w_reject*reject_term

Selection:
- argmin EntropyProxy
- deterministic tie_break


