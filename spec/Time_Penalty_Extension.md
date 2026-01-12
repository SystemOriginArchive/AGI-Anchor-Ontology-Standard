# Time Penalty Extension (Overlay)

## Purpose
Introduce a deterministic time-to-cost mapping that increases path cost as latency accumulates, without changing the core 1.0.4 model.

## Inputs
- Δt: elapsed time between intent packet reception and action commitment
- λ: delay weight (lambda_delay)
- Nonlinearity: optional exp(k·Δt) scaling

## Cost Term
C_time(Δt) = λ · Δt · g(Δt)
- g(Δt) = 1 (linear) OR g(Δt) = exp(k·Δt)

## Integration
C_total = C_locked + C_time
Where C_locked is the continuity-locked cost defined in continuity_lock.
