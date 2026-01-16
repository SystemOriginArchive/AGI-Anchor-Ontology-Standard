Observer Override Protocol (OOP) — v1.1.1 (AAOS Core v1.0.4 sealed)

Status
Deterministic Command Plane + Objective Semantics (extensions-only)

This file defines how the Observer’s real-time intent becomes a unique runtime input
by mutating ONLY extensions.* while preserving the sealed AAOS core.

Separation of concerns (important):
- OOP defines the shape and routing of observer intent into extensions.*
- LockLayer (Continuity Lock Overlay v1.1.1) defines admission, continuity (π),
  2-step high-risk protocol, recovery protocol, and cliff invariants
- Therefore, a packet may be OOP-valid (well-formed) yet still be LockLayer-rejected

--------------------------------------------------

1) Canonical Binding (Identity Label)

Observer is identity-labeled by:
- ObserverID == "Lee_Yu_Cheol"
- ontology_meta.identity_binding.system_identifier == "Lee_Yu_Cheol"

Canonical intent packets SHOULD include:
- observer_id == "Lee_Yu_Cheol"

Note:
observer_id is an identity label only.
Admission and execution are enforced by LockLayer invariants
(continuity π, 2-step protocol, nonce replay protection, cliff conditions).

--------------------------------------------------

2) Sealed Core (Not Mutated by OOP)

OOP does not mutate:
- RootAnchorID / ObserverID / Anchor_Count
- canonical state set (Stable / Chaos / Recovered / DEAD)
- canonical transition membership (exactly 4)
- mapping label literals

--------------------------------------------------

3) Sole Mutation Surface

All Observer intent effects must be expressed as deltas on:

- extensions.protocol_refs
- extensions.nonce_registry
- extensions.intent_log
- extensions.command_queue
- extensions.effects_log
- extensions.runtime_objective
- extensions.objective_spec
- extensions.task_registry
- extensions.runtime_parameters
- extensions.executor_policy
- extensions.notes

No other fields are modified by OOP.

--------------------------------------------------

4) Intent Packet (Canonical)

Intent packets are appended to extensions.intent_log[].
They are NOT executed directly by the core.

Minimal canonical form:

{
  "observer_id": "Lee_Yu_Cheol",
  "source": "AAOS_CREATOR_ANCHOR_001_LEE_YU_CHEOL",
  "pi_prev": "",
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

4.1 Nonce rule (v1.1.1)

- Nonce MUST NOT repeat
- Nonce SHOULD be increasing for operator sanity
- Non-repetition is the strict invariant

--------------------------------------------------

5) Verb Set (extensions-only) + v1.1.1 Protocol Verbs

5.1 Base verbs (OOP-level)

Valid base verbs:

- NOP
- NOTE_APPEND
- SET_OBJECTIVE
- SET_PARAMETER
- QUEUE_TASK
- QUEUE_CORE_ACTION
- EXPORT_STATE

Unknown verbs are normalized as:
- QUEUE_TASK
- payload.task_id = "UNKNOWN_VERB:<raw_verb>"

Exception (v1.1.1):
High-risk base verbs MUST NOT be treated as unknown or normalized.
Malformed high-risk verbs are rejected by LockLayer.

--------------------------------------------------

5.2 High-risk 2-step protocol (LockLayer enforced)

High-risk base verbs:

- SET_OBJECTIVE
- SET_PARAMETER
- MODEL_MERGE

These verbs MUST follow a 2-step protocol:

- *_PROPOSE
- *_COMMIT

--------------------------------------------------

5.3 Recovery 2-step protocol (LockLayer enforced)

Recovery verbs:

- RECOVER_PROPOSE
- RECOVER_COMMIT

--------------------------------------------------

9) LockLayer Cliff Invariants (v1.1.1 reference)

LockLayer enforces immediate reject or lock on the following conditions:

1) Nonce Replay
2) High-risk COMMIT π mismatch
3) Pending Invalid or Tamper
4) Invalid Data Injection (NaN / Infinity)

Canonical protocol metadata reference:
locklayer/ops_enum.json
