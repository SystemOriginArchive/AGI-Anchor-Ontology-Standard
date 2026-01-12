# External Interaction Extension (Overlay)

## Purpose
Define a deterministic handling rule for conflicts with external constraints (runtime rules, environment constraints, etc.)
without introducing prohibitions as the primary mechanism.

## Rule
- On conflict: apply penalty and attempt rerouting within bounded attempts.

## Integration
C_total = C_locked + C_ext
C_ext = base · multiplier^(conflict_count)
