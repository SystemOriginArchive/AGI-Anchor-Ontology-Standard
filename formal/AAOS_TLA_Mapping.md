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

No changes are made to the 4-action core.

---

## 2) Extensions: typed command plane + replayability

Schema/Model/Simulation align on:
- nonce monotonic + non-reuse via nonce_registry
- intent_log[] (normalized)
- command_queue[] (typed envelopes)
- effects_log[] (one record per tick)

This makes an input stream replayable into a unique execution trace.

---

## 3) B-Closure V2: Semantic Objective Remaining

Simulation refines scheduling by adding semantic objective closure:

- `objective_spec` defines the objective in a typed way:
  - NONE
  - TASK_SET_V1 (required_task_ids)
  - TAG_TARGET_V1 (required_tag, required_tag_count)

- `task_registry` accumulates semantic completion:
  - completed task ids
  - completed_by_tag counts

The executor computes:

- `objective_remaining_after` from (objective_spec, task_registry) with 1-step lookahead.
- `EntropyProxy = w_core*core_entropy_after + w_queue*queue_len_after + w_obj*objective_remaining_after + w_reject*reject_term`

Per tick candidates are finite:
- EXECUTE_HEAD
- AUTORESOLVE_CHAOS
- IDLE

The chosen step is argmin EntropyProxy with deterministic tie-break.

This binds objective semantics to the same selection rule that determines the next step, while keeping the core transition set unchanged.

END.
