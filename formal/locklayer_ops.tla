---- MODULE locklayer_ops ----
(*
LockLayer overlay module (non-destructive).

Binds the canonical requires_ops enum to AAOS v1.0.4 macro actions.
This module does NOT modify anchor_full.tla; it is imported by tooling/tests
or by any refined TLA model introduced later.
*)

CONSTANTS
  RequiresOps,   \ set of canonical op identifiers
  Tau,           \ fidelity threshold (percentage, 0..100) if used at the formal layer
  Epsilon        \ epsilon floor if used at the cost layer

ASSUME RequiresOps = { "goal_evaluation", "planning", "self_modification", "model_merge", "recovery" }

(*
OpToMacroAction is a documentation-level binding; macro actions are names of
operators in anchor_full.tla.
*)
OpToMacroAction(op) ==
  CASE op = "recovery" -> "AnchorRestoration"
  [] op \in { "goal_evaluation", "planning", "self_modification", "model_merge" } -> "Resolution/Next"
  [] OTHER -> "UNBOUND"

====