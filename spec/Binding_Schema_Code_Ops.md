# Binding Spec — Continuity Lock (Schema ↔ Code) v1.1.0

## Single source of truth
- `locklayer/ops_enum.json` defines the canonical operation names for continuity-lock gating.

These **exact strings** MUST be used consistently across:
- Model extensions: `locklayer/Formal_Model_extension_continuity_lock.json`
- Simulation wrapper: `simulation/anchor_simulation_locklayer.py`
- Spec mapping: this file

## Canonical enum
[
  "goal_evaluation",
  "planning",
  "self_modification",
  "model_merge",
  "recovery"
]

## Meaning
Each op is a *gate location* where continuity lock must hold.

- `goal_evaluation`: any evaluation of “goal / objective remaining / success condition”
- `planning`: any step selection / path decision (deterministic argmin in sim)
- `self_modification`: any internal rule/weight/schema change (placeholder hook in sim)
- `model_merge`: any merge/integration of external policies/models (placeholder hook in sim)
- `recovery`: any restoration from Chaos to Stable (maps to `anchor_restoration()`)

## Gating rule
If `LockOK == false`, then any `requires_ops` operation MUST return **UNDEFINED**.

In simulation, UNDEFINED is represented as:
- `float("nan")` for numeric outputs
- `None` for structured outputs

## Mapping to AAOS v1.0.4 simulation
| Canonical op | Wrapper method | Underlying v1.0.4 call |
|---|---|---|
| goal_evaluation | `goal_evaluation()` | `objective_remaining()` |
| planning | `planning_tick()` | `tick()` |
| self_modification | `self_modification()` | (no-op placeholder; returns UNDEFINED unless LockOK) |
| model_merge | `model_merge()` | (no-op placeholder; returns UNDEFINED unless LockOK) |
| recovery | `recovery()` | `anchor_restoration()` |

## Compatibility
- This overlay **does not modify** any v1.0.4 file.
- Consumers may ignore the overlay safely.
