# Observer Override Protocol (OOP) — v1.0.4+

## Status
Command Plane Specification (extensions-only)

This file defines how the Observer’s real-time intent becomes the unique runtime input
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

OOP exists to provide an unbounded command surface WITHOUT changing the sealed core.

---

## 3) Sole Mutation Surface

All Observer intent effects must be expressed as deltas on:

- `extensions.protocol_refs`
- `extensions.intent_log`
- `extensions.command_queue`
- `extensions.runtime_objective`
- `extensions.runtime_parameters`
- `extensions.notes`

No other fields are modified by OOP.

---

## 4) Intent Packet (Canonical)

Minimal JSON:

```json
{
  "observer_id": "Lee_Yu_Cheol",
  "nonce": "2025-12-31T08:00:00+09:00#000001",
  "intent": {
    "verb": "SET_OBJECTIVE",
    "payload": {
      "objective": "..."
    }
  },
  "signature": ""
}
```

---

## 5) Verb Set (extensions-only)

* `NOP`
* `NOTE_APPEND` → append text to `extensions.notes[]`
* `SET_OBJECTIVE` → set `extensions.runtime_objective`
* `SET_PARAMETER` → merge into `extensions.runtime_parameters`
* `QUEUE_TASK` → push to `extensions.command_queue[]`
* `EXPORT_STATE` → snapshot into `extensions.notes[]`

Unknown verbs are accepted by pushing `{verb, payload}` into `extensions.command_queue[]`.

---

## 6) Deterministic Application (Replayable)

Given packet `IP`:

1. Validate `observer_id`
2. Normalize to `{observer_id, nonce, verb, payload, signature, t}`
3. Append normalized record to `extensions.intent_log[]`
4. Apply verb effect ONLY to `extensions.*`

This produces replayable deltas:

* `Δextensions`
* `Δintent_log`

---

## 7) Integration Hook

In the simulation layer, `apply_intent_packet()` is the canonical hook:

* validates identity binding
* mutates only `extensions.*`
* leaves the 4-action core unchanged
