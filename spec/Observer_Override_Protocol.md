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
- validated (identity + nonce)
- appended to `extensions.intent_log[]`
- optionally projected into `extensions.*` and/or `extensions.command_queue[]`

Intent packets do NOT execute actions directly;  
execution occurs **only** via `extensions.command_queue[]` envelopes.

Minimal canonical packet form (runtime input):
---
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
}

Nonce rule:
- Nonce MUST be strictly increasing (lexical)
- Nonce MUST NOT repeat

Commit rule (atomic):
- If a packet is REJECT, it MUST NOT be committed to `nonce_registry` and MUST NOT be appended to `intent_log[]`.

---

요청하신 섹션 5, 6, 7, 8번 내용을 모두 합쳐서 깔끔하게 정리해 드립니다. 가독성을 위해 JSON 블록을 분리하고 수식은 보기 좋게 다듬었습니다.5) Verb Set (extensions-only)Valid verbs (Must match schema enum):NOPno-op (log only)NOTE_APPENDAppends payload.text (or stringified payload) to extensions.notes[]SET_OBJECTIVESets extensions.runtime_objective (optional mirror string)Sets extensions.objective_spec (typed semantics)Syncs extensions.task_registry.required when type is TASK_SET_V1SET_PARAMETERMutates extensions.runtime_parameters onlyQUEUE_TASKPushes a TASK envelope into extensions.command_queue[] (requires payload.task_id)QUEUE_CORE_ACTIONPushes a CORE_ACTION envelope into extensions.command_queue[]EXPORT_STATEEmits a snapshot (implementation-defined) into extensions.notes[] or an export channelUnknown verbs:MUST be normalized as a TASK envelope with:payload.task_id = "UNKNOWN_VERB:<raw_verb>"6) Typed Command Envelopes (command_queue[])extensions.command_queue[] contains ONLY CommandEnvelope records.Generic Envelope SchemaJSON{
  "kind": "TASK | CORE_ACTION | NOTE",
  "nonce": "...",
  "t": 0,
  "payload": {}
}
Specific Envelope Types1. TASK EnvelopeJSON{
  "kind": "TASK",
  "nonce": "...",
  "t": 0,
  "payload": {
    "task_id": "T1",
    "tag": "",
    "params": {}
  }
}
2. NOTE EnvelopeJSON{
  "kind": "NOTE",
  "nonce": "...",
  "t": 0,
  "payload": {
    "text": "..."
  }
}
3. CORE_ACTION EnvelopeJSON{
  "kind": "CORE_ACTION",
  "nonce": "...",
  "t": 0,
  "payload": {
    "action": "ExternalDisturbance",
    "args": {}
  }
}
Allowed CORE_ACTION values:ExternalDisturbanceChangeClaimantInChaosAnchorRestorationTotalCollapse7) Objective Spec DSL (Semantic Closure)extensions.objective_spec.type $\in$:NONETASK_SET_V1TAG_TARGET_V1TASK_SET_V1Requires: required_task_ids[] (unique)Satisfied when: $\text{required\_task\_ids} \subseteq \text{task\_registry.completed[]}$Objective remaining:$$|\text{required} - \text{completed}|$$TAG_TARGET_V1Requires: required_tag, required_tag_countSatisfied when: $\text{completed\_by\_tag}[\text{required\_tag}] \ge \text{required\_tag\_count}$Objective remaining:$$\max(0, \text{required\_tag\_count} - \text{completed\_by\_tag}[\text{required\_tag}])$$Task Completion SemanticsExecuting a TASK envelope adds task_id to completed[] (Set semantics; unique).completed_by_tag[tag] increments ONLY when a task_id is newly added to completed[].8) B-Closure (EntropyProxy argmin V2)Policy ConfigurationJSON{
  "selection_rule": "ENTROPY_ARGMIN_V2",
  "weights": {
    "core": 1.0,
    "queue": 10.0,
    "objective_remaining": 500.0,
    "reject": 500.0
  },
  "tie_break": ["EXECUTE_HEAD", "AUTORESOLVE_CHAOS", "IDLE"]
}
Candidate Set Per Tick (Queue-Aware)Condition A: If len(command_queue) > 0EXECUTE_HEADAUTORESOLVE_CHAOS (Only if world_state == Chaos AND anchor_connection == FALSE)(Note: IDLE is not a candidate here)Condition B: If len(command_queue) == 0AUTORESOLVE_CHAOS (Only if world_state == Chaos AND anchor_connection == FALSE)IDLEEntropyProxy (1-step lookahead)The value is calculated as:$$\text{EntropyProxy} =
(w_{\text{core}} \cdot \text{core\_entropy\_after}) +
(w_{\text{queue}} \cdot \text{queue\_len\_after}) +
(w_{\text{obj}} \cdot \text{objective\_remaining\_after}) +
(w_{\text{reject}} \cdot \text{reject\_term})$$Selection LogicChoose the candidate with the minimal EntropyProxy value.Ties are broken deterministically by executor_policy.tie_break.
