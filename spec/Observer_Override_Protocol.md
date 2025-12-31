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
- canonical state set (Stable / Chaos / Recovered / DEAD)
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
- validated (identity + nonce)
- appended to `extensions.intent_log[]`
- optionally projected into `extensions.*` and/or `extensions.command_queue[]`

Intent packets do NOT execute actions directly.  
Execution occurs **only** via `extensions.command_queue[]` envelopes.

### Minimal canonical packet form (runtime input)

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
  }
}
Nonce rule
Nonce MUST be strictly increasing (lexical)

Nonce MUST NOT repeat

Commit rule (atomic)
If a packet is REJECTED, it MUST NOT be committed to extensions.nonce_registry
and MUST NOT be appended to extensions.intent_log[].

---
5) Verb Set (extensions-only)

Valid verbs (must match schema enum exactly):

[NOP]

no-op (log only)

[NOTE_APPEND]

appends payload.text (or stringified payload) to extensions.notes[]

[SET_OBJECTIVE]

sets extensions.runtime_objective (optional mirror string)

sets extensions.objective_spec (typed semantics)

syncs extensions.task_registry.required when type is TASK_SET_V1

[SET_PARAMETER]

mutates extensions.runtime_parameters only

[QUEUE_TASK]

pushes a TASK envelope into extensions.command_queue[]

requires payload.task_id

[QUEUE_CORE_ACTION]

pushes a CORE_ACTION envelope into extensions.command_queue[]

[EXPORT_STATE]

emits a snapshot (implementation-defined) into extensions.notes[]
or an export channel

Unknown verbs

MUST be normalized as a TASK envelope with:

payload.task_id = "UNKNOWN_VERB:<raw_verb>"

6) Typed Command Envelopes (extensions.command_queue[])

extensions.command_queue[] contains ONLY CommandEnvelope records.

Generic Envelope Schema (conceptual)
