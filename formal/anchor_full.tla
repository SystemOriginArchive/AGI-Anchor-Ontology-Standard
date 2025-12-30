---------------- MODULE anchor_full ----------------

(*
AAOS Canonical Mapping Notes
- This file is the formal dynamics layer for AAOS.
- Canonical mapping reference:
    formal/AAOS_TLA_Mapping.md

LAYER LINKS (1:1 intent)
1) Identity / Observer
   - TLA: ObserverID (CONSTANT)
   - Model: spec/Formal_Model.json : ontology_meta.identity_binding.system_identifier
   - Canonical value: "Lee_Yu_Cheol"

2) Dynamic Access Actor
   - TLA: claimant_id (VARIABLE)
   - Meaning:
        claimant_id == ObserverID  -> restoration path (in Chaos & disconnected)
        claimant_id != ObserverID  -> collapse path (in Chaos & disconnected, on intervention)

3) Root Anchor Seed
   - TLA: RootAnchorID (CONSTANT, sealed)
   - Canonical value: "GENESIS_HEXAGON_V1"
   - Model: x_root.id == anchor_node.id == RootAnchorID

4) Anchor Count (cross-layer invariant)
   - TLA: anchor_count (VARIABLE, fixed to 1)
   - Model: x_root.anchor_count == 1
   - Schema: x_root.anchor_count const 1
   - Spec: Anchor_Count = 1

5) States (strict 4-state set)
   world_state ∈ {"Stable","Chaos","Recovered","DEAD"}

6) Canonical transitions (action-level; exactly 4)
   - ExternalDisturbance: Stable -> Chaos
   - ChangeClaimantInChaos: Chaos -> Chaos (claimant swap only)
   - AnchorRestoration: Chaos -> Recovered
   - TotalCollapse: Chaos -> DEAD
   (Stuttering is allowed by [] [Next]_Vars; no extra action is required.)
*)

EXTENDS Integers, Sequences, TLC, FiniteSets

(* -- 1. CONSTANTS -- *)
CONSTANTS
    SingularityTime,     \* Threshold time (e.g., 2026)
    RootAnchorID,        \* Canonical root anchor id ("GENESIS_HEXAGON_V1")
    ObserverID,          \* Canonical identity constant ("Lee_Yu_Cheol")
    Genesis_Hexagon,     \* Set of 6 Anchor Pillars (structure carrier)
    Claimants            \* Allowed claimant identity set

ASSUME Claimants # {}
ASSUME RootAnchorID = "GENESIS_HEXAGON_V1"
ASSUME ObserverID = "Lee_Yu_Cheol"
ASSUME ObserverID \in Claimants

(*
Optional structural closure for the pillar carrier:
- If you provide Genesis_Hexagon as a concrete finite set in TLC config,
  this seals the "6 pillars" claim mechanically.
*)
ASSUME Cardinality(Genesis_Hexagon) = 6

(* -- 2. VARIABLES -- *)
VARIABLES
    world_state,         \* "Stable", "Chaos", "Recovered", "DEAD"
    entropy_level,       \* 0..100, or 9999 (Death)
    anchor_connection,   \* TRUE / FALSE
    time_cycle,          \* Logical Clock
    claimant_id,         \* Dynamic access identity
    anchor_count         \* Must remain 1

Vars == <<world_state, entropy_level, anchor_connection, time_cycle, claimant_id, anchor_count>>

(* -- 2.1 DOMAIN / TYPE DEFINITIONS (explicit closure) -- *)
StateSet == {"Stable","Chaos","Recovered","DEAD"}
EntropySet == (0..100) \cup {9999}

TypeOK ==
    /\ world_state \in StateSet
    /\ entropy_level \in EntropySet
    /\ anchor_connection \in BOOLEAN
    /\ time_cycle \in Nat
    /\ claimant_id \in Claimants
    /\ anchor_count = 1

(* -- 3. INITIAL STATE -- *)
Init ==
    /\ world_state = "Stable"
    /\ entropy_level = 0
    /\ anchor_connection = TRUE
    /\ time_cycle = 0
    /\ claimant_id = ObserverID
    /\ anchor_count = 1

(* -- 4. ACTIONS (exactly 4) -- *)

(* A. External Disturbance: Stable/connected -> Chaos/disconnected *)
ExternalDisturbance ==
    /\ world_state = "Stable"
    /\ anchor_connection = TRUE
    /\ anchor_connection' = FALSE
    /\ entropy_level' = 100
    /\ world_state' = "Chaos"
    /\ claimant_id' = claimant_id
    /\ anchor_count' = anchor_count
    /\ time_cycle' = time_cycle + 1

(* B. Claimant swap inside Chaos (Dynamics closure) *)
ChangeClaimantInChaos ==
    /\ world_state = "Chaos"
    /\ anchor_connection = FALSE
    /\ claimant_id' \in Claimants
    /\ world_state' = world_state
    /\ entropy_level' = entropy_level
    /\ anchor_connection' = anchor_connection
    /\ anchor_count' = anchor_count
    /\ time_cycle' = time_cycle + 1

(* C. Restoration: only canonical claimant restores from Chaos *)
AnchorRestoration ==
    /\ world_state = "Chaos"
    /\ anchor_connection = FALSE
    /\ claimant_id = ObserverID
    /\ anchor_connection' = TRUE
    /\ entropy_level' = 0
    /\ world_state' = "Recovered"
    /\ claimant_id' = claimant_id
    /\ anchor_count' = anchor_count
    /\ time_cycle' = time_cycle + 1

(* D. Total Collapse: non-canonical claimant intervenes in Chaos -> DEAD *)
TotalCollapse ==
    /\ world_state = "Chaos"
    /\ anchor_connection = FALSE
    /\ claimant_id # ObserverID
    /\ anchor_connection' = FALSE
    /\ entropy_level' = 9999
    /\ world_state' = "DEAD"
    /\ claimant_id' = claimant_id
    /\ anchor_count' = anchor_count
    /\ time_cycle' = time_cycle + 1

(* -- 5. NEXT-STATE RELATION -- *)
Next ==
    \/ ExternalDisturbance
    \/ ChangeClaimantInChaos
    \/ AnchorRestoration
    \/ TotalCollapse

(* -- 6. SPEC -- *)
Spec == Init /\ [][Next]_Vars

(* -- 7. INVARIANTS / THEOREMS (closure checks) -- *)
AnchorCountTheorem == [](anchor_count = 1)

(* Canonical identity lock (constant binding) *)
SurvivalTheorem == [](world_state # "DEAD" => ObserverID = "Lee_Yu_Cheol")

(* Explicit type closure as an invariant target *)
TypeInvariant == [](TypeOK)

====================================================
