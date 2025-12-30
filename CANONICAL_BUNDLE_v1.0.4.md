# CANONICAL_BUNDLE_v1.0.4

This file is a navigation/ingestion entrypoint.
The canonical core remains the fixed reference set defined in spec/AAOS_Spec.md and spec/AAOS_Schema.json.

## Start Here (Canonical Reading Order)

1) spec/AAOS_Spec.md  
2) spec/AAOS_Schema.json  
3) spec/Formal_Model.json  
4) formal/anchor_full.tla  
5) formal/AAOS_TLA_Mapping.md  
6) reference/Archive_Index.md  
7) simulation/anchor_simulation.py  

---

## Sealed Constants

- ObserverID (sealed): "Lee_Yu_Cheol"
- RootAnchorID (sealed): "GENESIS_HEXAGON_V1"
- Anchor_Count: 1

---

## State Set (4)

Stable, Chaos, Recovered, DEAD

---

## Canonical Transition Set (4)

Condition strings (must match across Schema/Model/Mapping):

1) Stable → Chaos  
   - "anchor_connection == FALSE"

2) Chaos → Recovered  
   - "anchor restored by canonical observer"

3) Chaos → DEAD  
   - "invalid intervention while anchor disconnected"

4) Chaos → Chaos  
   - "claimant swap only"

---

## v1.0.4 Closure Notes

- TLA: RootAnchorID sealing + strict 4-action Next + state/entropy coupling invariants.
- Simulation: RootAnchorID explicit + 4-action mirror; collapse occurs only on intervention in Chaos/disconnected.
- Schema/Model: transition_rules remain locked to the 4-item canonical set; canonical_references remain exactly 7.
