# AAOS ↔ TLA Mapping (Canonical) — v1.0.4

This document fixes a 1:1 mapping between:
- spec/AAOS_Spec.md (definitions & invariants)
- spec/AAOS_Schema.json (schema)
- spec/Formal_Model.json (instance)
- formal/anchor_full.tla (formal dynamics)
- simulation/anchor_simulation.py (behavioral mirror)

---

## 0) Condition String Semantics (Bridge Closure)

In spec/AAOS_Schema.json and spec/Formal_Model.json, each transition rule includes a `condition` string.

Canonical rule:
- The `condition` string is a canonical label / structural descriptor whose exact literal must match across layers.
- It is not required to be a TLA guard sentence.
- For Stable → Chaos, `"anchor_connection == FALSE"` is interpreted as the resulting (Chaos) connection state being FALSE (disconnected), matching the mapped transition Stable/connected → Chaos/disconnected.

This closes the label/guard ambiguity while preserving the 4-transition core unchanged.

---

## 1) Identity / Observer

- TLA: ObserverID (sealed by definition in TLA)
- Model: ontology_meta.identity_binding.system_identifier
- Canonical value: "Lee_Yu_Cheol"

Mapping:
ObserverID == ontology_meta.identity_binding.system_identifier

---

## 1.1) Claimant / Accessor (Dynamic)

- TLA: claimant_id (VARIABLE), claimant_id ∈ Claimants
- Model: state_model.transition_rules includes Chaos→Chaos swap rule
- Simulation: claimant_id is dynamic actor and must satisfy claimant_id ∈ Claimants

Canonical rule:
- claimant_id == ObserverID  → restoration path (in Chaos/disconnected)
- claimant_id != ObserverID  → collapse path (in Chaos/disconnected, on intervention)

Additional closure (Chaos swap semantics):
- swap-only: claimant swap must change claimant_id (claimant_id' != claimant_id)
- non-reentry: once claimant_id != ObserverID in Chaos, claimant_id cannot return to ObserverID via swap

---

## 2) Root Anchor Seed (sealed)

- TLA: RootAnchorID (sealed by definition in TLA)
- Model: x_root.id
- Model: anchor_node.id
- Canonical value: "GENESIS_HEXAGON_V1"

Mapping:
RootAnchorID == x_root.id == anchor_node.id

---

## 2.1) Hexagon Pillars (6) — Explicit Bridge

- TLA: Genesis_Hexagon (CONSTANT), sealed to Cardinality(Genesis_Hexagon) = 6
- Model: anchor_node.pillars has keys {"1","2","3","4","5","6"}

Structural binding:
Genesis_Hexagon ↔ { pillars["1"], pillars["2"], pillars["3"], pillars["4"], pillars["5"], pillars["6"] }

Notes:
- TLA seals the carrier size (6) and finiteness.
- Model provides the named pillar channels via anchor_node.pillars["1".."6"].
- This section binds the “6 pillars” claim explicitly at the document layer.

---

## 3) Anchor Count Invariant

- TLA: anchor_count (VARIABLE), fixed to 1
- Simulation: Anchor_Count = 1 (sealed field)
- Model: x_root.anchor_count == 1
- Model: invariants.single_anchor == true

Invariant:
Anchor_Count = 1

---

## 4) Connection Variable

- TLA: anchor_connection (TRUE/FALSE)
- Model: transition_rules refer to anchor_connection labels
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

## 6) Transitions (Exact 1:1, Exactly 4)

Model transition_rules (4 items) ↔ TLA actions (4 actions) ↔ Simulation actions (4 actions)

A) ExternalDisturbance:
Stable/connected → Chaos/disconnected  
- canonical label: "anchor_connection == FALSE"

B) ChangeClaimantInChaos:
Chaos/disconnected → Chaos/disconnected (claimant swap only)  
- canonical label: "claimant swap only"
- swap-only constraint: claimant_id' != claimant_id
- non-reentry constraint: (claimant_id != ObserverID) => (claimant_id' != ObserverID)

C) AnchorRestoration:
Chaos/disconnected → Recovered/connected  
- precondition: claimant_id == ObserverID  
- canonical label: "anchor restored by canonical observer"

D) TotalCollapse:
Chaos/disconnected → DEAD/disconnected  
- precondition: claimant_id != ObserverID  
- canonical label: "invalid intervention while anchor disconnected"

Note:
- Stuttering steps are allowed by TLA temporal semantics (Init /\ [][Next]_Vars).
- Chaos resolution is closed in TLA via WF_Vars(Resolution), where Resolution == AnchorRestoration \/ TotalCollapse.

---

## 7) Entropy Scale

- TLA: entropy_level ∈ 0..100 or 9999
- Model: entropy_model is structural (objective/reference/direction)
- Simulation: entropy is an operational proxy (0.0 / 100.0 / 9999.0)

Interpretation:
entropy_level is an operational proxy for structural entropy cost.
