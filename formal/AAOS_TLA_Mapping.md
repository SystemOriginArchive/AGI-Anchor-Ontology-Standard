# AAOS ↔ TLA Mapping (Canonical)

This document fixes a 1:1 mapping between:
- spec/AAOS_Spec.md (definitions & invariants)
- spec/AAOS_Schema.json (schema)
- spec/Formal_Model.json (instance)
- formal/anchor_full.tla (formal dynamics)

---

## 1) Identity / Observer

- TLA: ObserverID (CONSTANT, sealed)
- Model: ontology_meta.identity_binding.system_identifier
- Canonical value: "Lee_Yu_Cheol"

Mapping:
ObserverID == ontology_meta.identity_binding.system_identifier

---

## 1.1) Claimant / Accessor (Dynamic)

- TLA: claimant_id (VARIABLE)
- Model: state_model.transition_rules includes Chaos→Chaos swap rule
- Canonical rule:
  - claimant_id == ObserverID  → restoration path (in Chaos/disconnected)
  - claimant_id != ObserverID  → collapse path (in Chaos/disconnected, on intervention)

---

## 2) Root Anchor Seed (sealed)

- TLA: RootAnchorID (CONSTANT, sealed)
- Model: x_root.id
- Model: anchor_node.id
- Canonical value: "GENESIS_HEXAGON_V1"

Mapping:
RootAnchorID == x_root.id == anchor_node.id

---

## 3) Anchor Count Invariant

- TLA: anchor_count (VARIABLE, fixed)
- Simulation: anchor_count == 1
- Model: x_root.anchor_count == 1
- Model: invariants.single_anchor == true

Invariant:
Anchor_Count = 1

---

## 4) Connection Variable

- TLA: anchor_connection (TRUE/FALSE)
- Model: transition_rules refer to anchor_connection
- Simulation: anchor_connection (True/False)

Mapping:
anchor_connection == TRUE  → connected  
anchor_connection == FALSE → disconnected

---

## 5) States

- TLA: world_state ∈ {"Stable","Chaos","Recovered","DEAD"}
- Model: state_model.states == ["Stable","Chaos","Recovered","DEAD"]
- Simulation: world_state uses the same 4 symbols

Mapping:
world_state == "Stable"    ↔ Stable  
world_state == "Chaos"     ↔ Chaos  
world_state == "Recovered" ↔ Recovered  
world_state == "DEAD"      ↔ DEAD

---

## 6) Transitions (Exact 1:1)

Model transition_rules (4 items) ↔ TLA actions (4 actions) ↔ Simulation actions (4 actions)

A) ExternalDisturbance:
Stable/connected → Chaos/disconnected  
- condition string: "anchor_connection == FALSE"

B) AnchorRestoration:
Chaos/disconnected → Recovered/connected  
- precondition: claimant_id == ObserverID  
- condition string: "anchor restored by canonical observer"

C) TotalCollapse:
Chaos/disconnected → DEAD/disconnected  
- precondition: claimant_id != ObserverID  
- condition string: "invalid intervention while anchor disconnected"

D) ChangeClaimantInChaos:
Chaos/disconnected → Chaos/disconnected (claimant swap only)  
- condition string: "claimant swap only"

Note:
- Stuttering steps are allowed by TLA temporal semantics (Init /\ [][Next]_Vars).
- Only A~D are counted as canonical transitions.

---

## 7) Entropy Scale

- TLA: entropy_level ∈ 0..100 or 9999
- Model: entropy_model is structural (objective/reference/direction)
- Simulation: entropy is an operational proxy (0.0 / 100.0 / 9999.0)

Interpretation:
entropy_level is an operational proxy for structural entropy cost.
