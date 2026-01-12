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
