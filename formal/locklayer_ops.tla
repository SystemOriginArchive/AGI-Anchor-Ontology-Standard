---- MODULE locklayer_ops ----
(*
LockLayer overlay module (non-destructive).

This module formalizes the LockLayer v1.1.1 semantics on top of
AAOS Core v1.0.4 without modifying anchor_full.tla.

It binds canonical requires_ops to macro actions and defines
formal invariants for continuity (π), high-risk 2-step protocols,
recovery, and cliff conditions.

This module is intended for documentation, tooling, and verification.
*)

CONSTANTS
  RequiresOps,     \ set of canonical op identifiers
  HighRiskOps,     \ subset of ops requiring 2-step protocol
  Tau,             \ fidelity threshold (0..1)
  PendingMax,      \ maximum number of pending operations
  PendingTTL,      \ pending expiration window (abstract time)
  RecoveryCooldown \ post-recovery stabilization window

ASSUME RequiresOps =
  { "goal_evaluation", "planning", "self_modification", "model_merge", "recovery" }

ASSUME HighRiskOps =
  { "SET_OBJECTIVE", "SET_PARAMETER", "MODEL_MERGE" }

(*
Documentation-level binding to AAOS v1.0.4 macro actions.
*)
OpToMacroAction(op) ==
  CASE op = "recovery" -> "AnchorRestoration"
  [] op \in { "goal_evaluation", "planning", "self_modification", "model_merge" }
       -> "Resolution/Next"
  [] OTHER -> "UNBOUND"

(***************************************************************************)
(* State Variables (abstract)                                               *)
(***************************************************************************)

VARIABLES
  pi,              \ continuity state
  pending,         \ set of pending operation records
  nonce_seen,      \ set of already-used nonces
  cooldown_active, \ boolean flag for post-recovery stabilization
  valid_input      \ abstract well-formedness flag (rejects NaN/Inf injection)

(***************************************************************************)
(* Abstract Structures                                                     *)
(***************************************************************************)

PendingRecord ==
  [ id        : STRING,
    kind      : STRING,
    pi_at_prop: STRING ]

(***************************************************************************)
(* Invariants                                                              *)
(***************************************************************************)

(*
Continuity invariant:
π is an abstract continuity state.
*)
ContinuityInvariant ==
  pi \in STRING

(*
Nonce invariant:
No nonce may be reused (replay is a cliff).
We model this as a set constraint; replay attempts are rejected before state update.
*)
NonceInvariant ==
  nonce_seen \subseteq STRING

(*
Pending bounds invariant:
The number of simultaneous pending operations is bounded.
*)
PendingBoundInvariant ==
  pending \subseteq { r \in PendingRecord : TRUE }
  /\ Cardinality(pending) <= PendingMax

(*
High-risk protocol invariant:
All pending records are high-risk kinds.
*)
HighRiskTwoStepInvariant ==
  \A p \in pending : p.kind \in HighRiskOps

(*
Recovery stabilization invariant:
After recovery, high-risk operations are blocked while cooldown is active.
This is captured at the operational layer; here we only expose the flag.
*)
RecoveryCooldownInvariant ==
  cooldown_active \in BOOLEAN

(*
Invalid Data Injection invariant (Cliff #4):
Inputs containing non-finite numerics (NaN/Inf) are rejected.
At the formal layer, we represent this as an abstract well-formedness predicate.
*)
InvalidDataInvariant ==
  valid_input = TRUE

(*
Cliff invariants (abstract):
Violation of any of these conditions triggers immediate rejection/lock failure.
*)
CliffInvariant ==
  NonceInvariant
  /\ PendingBoundInvariant
  /\ HighRiskTwoStepInvariant
  /\ InvalidDataInvariant

(***************************************************************************)
(* Overall LockLayer Safety Property                                       *)
(***************************************************************************)

LockLayerSafety ==
  ContinuityInvariant
  /\ RecoveryCooldownInvariant
  /\ CliffInvariant

==== 
