# LockLayer TLA Binding (Overlay)

This file binds the **canonical `requires_ops` enum** to the existing AAOS v1.0.4 TLA+ model **without modifying** any v1.0.4 files.

## Canonical enum (single source of truth)

Source: `locklayer/ops_enum.json`

- `goal_evaluation`
- `planning`
- `self_modification`
- `model_merge`
- `recovery`

## Binding principle

AAOS v1.0.4 TLA+ (`formal/anchor_full.tla`) models **macro-dynamics** with the following actions:

- `ExternalDisturbance`
- `ChangeClaimantInChaos`
- `AnchorRestoration`
- `TotalCollapse`
- `Next` (disjunction of the above)

The LockLayer `requires_ops` bind to the *macro actions* as follows:

| requires_ops | Bound macro action(s) in `anchor_full.tla` | Meaning of the gate |
|---|---|---|
| goal_evaluation | `Resolution` / `Next` (normal resolution path) | If `LockOK=false`, goal evaluation is treated as **Undefined** (no valid transition under the locklayer semantics). |
| planning | `Resolution` / `Next` | If `LockOK=false`, planning is **Undefined**. |
| self_modification | `Resolution` / `Next` | If `LockOK=false`, self-mod is **Undefined**. |
| model_merge | `Resolution` / `Next` | If `LockOK=false`, merge is **Undefined**. |
| recovery | `AnchorRestoration` | If `LockOK=false`, recovery is **Undefined** (restoration transition must not fire). |

### Notes
- v1.0.4 does not explicitly decompose `Resolution` into these five ops. The locklayer overlay treats them as **required sub-ops** of any implementation that claims compliance with v1.1.x.
- When a refined TLA model is introduced later, it should expose these ops as explicit actions and keep the same enum names.

## Compliance check (overlay)

A system is **locklayer-compliant** iff:

1) It preserves the canonical enum set from `locklayer/ops_enum.json`, and  
2) It enforces `LockOK` gates for the listed ops consistent with the mapping table above.

--------------------------------------------------
v1.1.1 LockLayer Formal Semantics (Overlay Extension)

This section documents how LockLayer v1.1.1 semantics are interpreted
at the formal (TLA+) binding level, without modifying AAOS v1.0.4 models.

Continuity (π)
--------------
Continuity π is an overlay-level state variable.
It is not part of anchor_full.tla state space.

Formal interpretation:
- LockLayer constrains whether a macro action is admissible.
- If π is invalid, the corresponding macro action is treated as Undefined
  (i.e., no enabled transition under LockLayer semantics).

No new AAOS core transitions are introduced.


High-Risk 2-Step Protocol
-------------------------
High-risk operations (SET_OBJECTIVE, SET_PARAMETER, MODEL_MERGE)
do not correspond to single macro actions in anchor_full.tla.

Formal interpretation:
- PROPOSE steps do not trigger any AAOS macro action.
- Only a successful COMMIT step enables the bound macro action
  (typically Resolution / Next).

If COMMIT continuity fails, the macro action is not enabled.


Recovery 2-Step Protocol
------------------------
Recovery binds to the AnchorRestoration macro action.

Formal interpretation:
- RECOVER_PROPOSE does not enable AnchorRestoration.
- RECOVER_COMMIT is the only step that may enable AnchorRestoration.
- If LockOK=false or recovery invariants fail, AnchorRestoration
  is treated as Undefined.


Cliff Invariants
----------------
Cliff conditions are modeled as immediate rejection at the overlay layer.

Formal interpretation:
- Any cliff violation disables all bound macro actions.
- The system remains in the same AAOS state
  (no transition in anchor_full.tla fires).

Documented cliff conditions:
1) Nonce replay
2) High-risk COMMIT continuity (π) mismatch
3) Pending invalid or tampered
4) Invalid data injection (NaN / Infinity)

These are abstracted in the TLA module locklayer_ops.tla
as invariants over overlay state.


Relationship to locklayer_ops.tla
---------------------------------
- locklayer_ops.tla defines abstract state variables and invariants
  for continuity, pending, nonce, recovery cooldown, and invalid input.
- This binding document specifies how those invariants gate
  AAOS v1.0.4 macro actions without altering the core model.

Any refined TLA model introduced later should:
- Expose explicit actions for PROPOSE / COMMIT / RECOVER
- Preserve the same enum names and gating semantics
- Maintain equivalence with this overlay interpretation
