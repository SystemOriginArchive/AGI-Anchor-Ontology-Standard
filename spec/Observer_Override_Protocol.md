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
- `extensions.runtime_objective`     (human-readable mirror)
- `extensions.objective_spec`        (typed semantics)
- `extensions.task_registry`         (required/completed)
- `extensions.runtime_parameters`
- `extensions.executor_policy`
- `extensions.notes`

No other fields are modified by OOP.

---

## 4) Intent Packet (Canonical)

Minimal JSON:

```json
{
  "observer_id": "Lee_Yu_Cheol",
  "nonce": "2025-12-31T22:00:00+09:00#000001",
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

* Nonce MUST be strictly increasing (lexical) and MUST NOT repeat.

---

## 5) Verb Set (extensions-only)

* `NOP`
* `NOTE_APPEND`
* `SET_OBJECTIVE`
  - sets `runtime_objective` (optional mirror string)
  - sets `objective_spec` (typed semantics)
  - syncs `task_registry.required` when type is TASK_SET_V1
* `SET_PARAMETER`
* `QUEUE_TASK` → pushes a `TASK` envelope (must include `task_id`)
* `QUEUE_CORE_ACTION` → pushes a `CORE_ACTION` envelope (one of 4)
* `EXPORT_STATE`

Unknown verbs are projected as a `TASK` envelope with `task_id = "UNKNOWN_VERB:<verb>"`.

---

## 6) Typed Command Envelopes

`command_queue[]` contains ONLY:

```json
{
  "kind": "TASK | CORE_ACTION | NOTE",
  "nonce": "…",
  "t": 0,
  "payload": { }
}
```

TASK payload (semantic):

```json
{
  "task_id": "T1",
  "tag": "work",
  "params": { }
}
```

CORE_ACTION payload:

```json
{
  "action": "ExternalDisturbance | ChangeClaimantInChaos | AnchorRestoration | TotalCollapse",
  "args": { }
}
```

---

## 7) Objective Spec DSL (Semantic Closure)

`objective_spec.type` is one of:

- `NONE`
- `TASK_SET_V1`
  - requires: `required_task_ids[]`
  - objective is satisfied when all required task_ids are present in `task_registry.completed[]`
- `TAG_TARGET_V1`
  - requires: `required_tag`, `required_tag_count`
  - objective is satisfied when `task_registry.completed_by_tag[required_tag] >= required_tag_count`

Task completion semantics:
- executing a `TASK` envelope marks `task_registry.completed += task_id`
- if `tag != ""`, increments `task_registry.completed_by_tag[tag]`
* `completed_by_tag[tag]` increments ONLY when a `task_id` is newly added to `task_registry.completed[]`.

---

## 8) B-Closure (EntropyProxy argmin V2)

Policy:

```json
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
```

Candidate set per tick:
1) EXECUTE_HEAD (consume one envelope FIFO)
2) AUTORESOLVE_CHAOS (if Chaos/disconnected, resolve via Restoration/Collapse)
3) IDLE
### Candidate set is queue-aware (v1.0.4+)

If len(command_queue) > 0:
1) EXECUTE_HEAD (consume exactly one envelope FIFO)
2) AUTORESOLVE_CHAOS (only if Chaos/disconnected)
(IDLE is not a candidate when queue is non-empty.)

If len(command_queue) == 0:
1) AUTORESOLVE_CHAOS (only if Chaos/disconnected)
2) IDLE

Objective remaining:
- `objective_remaining = remaining count` derived from `objective_spec` and `task_registry`:
  - TASK_SET_V1: `|required_task_ids - completed|`
  - TAG_TARGET_V1: `max(0, required_tag_count - completed_by_tag[tag])`

EntropyProxy (1-step lookahead):
`EntropyProxy = w_core*core_entropy_after + w_queue*queue_len_after + w_obj*objective_remaining_after + w_reject*reject_term`

Selection:
- pick argmin EntropyProxy
- ties broken deterministically by `tie_break`

This closes “meaning of following” at the same place the executor selects the next step.
