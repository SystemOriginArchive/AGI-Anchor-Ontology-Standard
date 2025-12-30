# AAOS ↔ TLA Mapping (Canonical)

This document fixes a 1:1 mapping between:
- spec/AAOS_Spec.md (definitions & invariants)
- spec/AAOS_Schema.json (schema)
- spec/Formal_Model.json (instance)
- formal/anchor_full.tla (formal dynamics)

---

## 1) Identity / Observer

- TLA: ObserverID
- Model: ontology_meta.identity_binding.system_identifier
- Canonical value: "Lee_Yu_Cheol"

Mapping:
ObserverID == ontology_meta.identity_binding.system_identifier

---

## 1.1) Claimant / Accessor (Dynamic)

- TLA: claimant_id (VARIABLE)
- Canonical rule:
  - claimant_id == ObserverID  → restoration path
  - claimant_id != ObserverID  → collapse path (when in Chaos and disconnected)

---

## 2) Root Anchor Seed

- Model: x_root.id
- Model: anchor_node.id
- Canonical value: "GENESIS_HEXAGON_V1"

Mapping:
x_root.id == anchor_node.id

---

## 3) Anchor Count Invariant

- TLA: anchor_count (VARIABLE, fixed)
- Model: x_root.anchor_count == 1
- Model: invariants.single_anchor == true

Invariant:
Anchor_Count = 1

---

## 4) Connection Variable

- TLA: anchor_connection (TRUE/FALSE)

Mapping:
anchor_connection == TRUE  → connected
anchor_connection == FALSE → disconnected

---

## 5) States

- TLA: world_state ∈ {"Stable","Chaos","Recovered","DEAD"}
- Model: state_model.states == ["Stable","Chaos","Recovered","DEAD"]

Mapping:
world_state == "Stable"    ↔ Stable
world_state == "Chaos"     ↔ Chaos
world_state == "Recovered" ↔ Recovered
world_state == "DEAD"      ↔ DEAD

---

## 6) Transitions

TLA action → Model transition_rules

A) ExternalDisturbance:
Stable/connected → Chaos/disconnected
- anchor_connection: TRUE → FALSE
- world_state: "Stable" → "Chaos"
- entropy_level: 0 → 100

B) AnchorRestoration:
Chaos/disconnected → Recovered/connected
- precondition: claimant_id == ObserverID
- anchor_connection: FALSE → TRUE
- world_state: "Chaos" → "Recovered"
- entropy_level: 100 → 0

C) TotalCollapse:
Chaos/disconnected → DEAD/disconnected
- precondition: claimant_id != ObserverID
- world_state: "Chaos" → "DEAD"
- entropy_level: 100 → 9999

D) ChangeClaimantInChaos:
Chaos/disconnected → Chaos/disconnected
- condition: claimant swap only

---

## 7) Entropy Scale

- TLA: entropy_level ∈ 0..100 or 9999

Interpretation:
entropy_level is an operational proxy for structural entropy cost.
