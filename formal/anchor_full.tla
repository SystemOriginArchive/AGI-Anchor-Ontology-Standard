---- MODULE anchor_full ----

(*
AAOS v1.0.4 Formal Dynamics (0-gap closure)

Core closures:
- 4 states / 4 actions only
- Anchor_Count = 1
- RootAnchorID / ObserverID sealed by definition (B-closure)
- Nat domain closed via EXTENDS Naturals
- Chaos must resolve (Recovered or DEAD) via WF on Resolution

v1.0.4+ patch:
- ChangeClaimantInChaos is swap-only
- Non-reentry: once claimant_id != ObserverID in Chaos, claimant_id cannot return to ObserverID via swap
*)

EXTENDS Naturals, TLC, FiniteSets

(*
-- 1) SEALED DEFINITIONS (no TLC cfg needed for these) --
*)
RootAnchorID == "GENESIS_HEXAGON_V1"
ObserverID   == "Lee_Yu_Cheol"

(*
-- 2) CONSTANTS (cfg-supplied) --
*)
CONSTANTS
    Genesis_Hexagon,     \* 6 pillars carrier set
    Claimants            \* allowed claimant identity set

ASSUME IsFiniteSet(Claimants)
ASSUME Claimants # {}
ASSUME ObserverID \in Claimants

ASSUME IsFiniteSet(Genesis_Hexagon)
ASSUME Cardinality(Genesis_Hexagon) = 6

(*
-- 3) VARIABLES --
*)
VARIABLES
    world_state,         \* "Stable", "Chaos", "Recovered", "DEAD"
    entropy_level,       \* 0..100, or 9999 (Death)
    anchor_connection,   \* TRUE / FALSE
    time_cycle,          \* logical clock
    claimant_id,         \* dynamic actor
    anchor_count         \* must remain 1

Vars == <<world_state, entropy_level, anchor_connection, time_cycle, claimant_id, anchor_count>>

(*
-- 3.1) DOMAIN / TYPE (explicit closure) --
*)
StateSet == {"Stable","Chaos","Recovered","DEAD"}
EntropySet == (0..100) \cup {9999}

TypeOK ==
    /\ world_state \in StateSet
    /\ entropy_level \in EntropySet
    /\ anchor_connection \in BOOLEAN
    /\ time_cycle \in Nat
    /\ claimant_id \in Claimants
    /\ anchor_count = 1

(*
-- 4) INIT --
*)
Init ==
    /\ world_state = "Stable"
    /\ entropy_level = 0
    /\ anchor_connection = TRUE
    /\ time_cycle = 0
    /\ claimant_id = ObserverID
    /\ anchor_count = 1

(*
-- 5) ACTIONS (exactly 4) --
*)

(* A) Stable/connected -> Chaos/disconnected *)
ExternalDisturbance ==
    /\ world_state = "Stable"
    /\ anchor_connection = TRUE
    /\ anchor_connection' = FALSE
    /\ entropy_level' = 100
    /\ world_state' = "Chaos"
    /\ claimant_id' = claimant_id
    /\ anchor_count' = anchor_count
    /\ time_cycle' = time_cycle + 1

(* B) Chaos/disconnected -> Chaos/disconnected (claimant swap only) *)
ChangeClaimantInChaos ==
    /\ world_state = "Chaos"
    /\ anchor_connection = FALSE
    /\ claimant_id' \in Claimants
    /\ claimant_id' # claimant_id                       \* swap-only
    /\ (claimant_id # ObserverID => claimant_id' # ObserverID)  \* non-reentry
    /\ world_state' = world_state
    /\ entropy_level' = entropy_level
    /\ anchor_connection' = anchor_connection
    /\ anchor_count' = anchor_count
    /\ time_cycle' = time_cycle + 1

(* C) Chaos/disconnected -> Recovered/connected (canonical claimant only) *)
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

(* D) Chaos/disconnected -> DEAD/disconnected (non-canonical claimant intervention) *)
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

(*
-- 6) NEXT --
*)
Next ==
    \/ ExternalDisturbance
    \/ ChangeClaimantInChaos
    \/ AnchorRestoration
    \/ TotalCollapse

(*
-- 7) CHAOS RESOLUTION FAIRNESS --
*)
Resolution == AnchorRestoration \/ TotalCollapse

Spec ==
    Init
    /\ [][Next]_Vars
    /\ WF_Vars(Resolution)

(*
-- 8) INVARIANTS / THEOREMS --
*)
RootAnchorSealed == (RootAnchorID = "GENESIS_HEXAGON_V1")
IdentitySealed   == (ObserverID   = "Lee_Yu_Cheol")

AnchorCountTheorem == [](anchor_count = 1)

StateConnectionInvariant ==
    [](
        (world_state = "Stable"    => anchor_connection = TRUE)  /\
        (world_state = "Chaos"     => anchor_connection = FALSE) /\
        (world_state = "Recovered" => anchor_connection = TRUE)  /\
        (world_state = "DEAD"      => anchor_connection = FALSE)
      )

StateEntropyInvariant ==
    [](
        (world_state \in {"Stable","Recovered"} => entropy_level = 0) /\
        (world_state = "Chaos" => entropy_level = 100) /\
        (world_state = "DEAD"  => entropy_level = 9999)
      )

RecoveredClaimantInvariant ==
    [](world_state = "Recovered" => claimant_id = ObserverID)

(* Bound name used by Formal_Model.json formal_binding *)
SurvivalTheorem ==
    [](world_state = "Recovered" => (claimant_id = ObserverID /\ anchor_connection = TRUE /\ entropy_level = 0))

TypeInvariant == [](TypeOK)


====

