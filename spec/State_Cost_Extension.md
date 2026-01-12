# State Cost Extension (Overlay)

## Purpose
Allow state/affect signals to influence path cost while preserving single-objective convergence.

## Signals
fatigue, stress, satisfaction, clarity

## Aggregation
C_state = Σ w_s · s
- fatigue/stress increase cost (positive weights)
- satisfaction/clarity decrease cost (negative weights)

## Integration
C_total = C_locked + C_state
