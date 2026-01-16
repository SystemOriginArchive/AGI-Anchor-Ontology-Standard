# LockLayer Overlay v1.1.1 (Non-destructive)

This overlay adds continuity-lock gating without touching AAOS v1.0.4 core files.

## What is added
- `locklayer/ops_enum.json` — canonical requires_ops enum
- `locklayer/Formal_Model_extension_continuity_lock.json` — extension block (overlay)
- `spec/Binding_Schema_Code_Ops.md` — schema↔code binding
- `spec/Continuity_Extension_Schema.json` — schema for the extension block
- `simulation/anchor_simulation_locklayer.py` — wrapper that enforces gating

## How to use in simulation

x_root is the fixed external creator intent anchor (cost origin).  
Only intents aligned with x_root converge to minimum cost.

```python
from simulation.anchor_simulation_locklayer import AnchorSystemLocked

sys = AnchorSystemLocked()
# Provide intent packets with fields expected by the locklayer (see code)
sys.apply_intent_packet({
    "intent": "...",
    "source": "AAOS_CREATOR_ANCHOR_001_LEE_YU_CHEOL",
    "pi_prev": sys.lock_state()["pi"]
})
sys.planning_tick()   # gated
```

## Principle
- v1.0.4 remains canonical and untouched.
- This is a layer that consumers can opt into.

## Optional Extensions
- locklayer/time_penalty.json + spec/Time_Penalty_Extension.md
- locklayer/state_cost.json + spec/State_Cost_Extension.md
- locklayer/external_interaction.json + spec/External_Interaction_Extension.md

--------------------------------------------------
Operational Semantics (v1.1.1)

Continuity (π)
--------------
LockLayer enforces a continuity variable π as the primary admission invariant.

- Each admitted protocol event advances π.
- π cannot be externally reconstructed or guessed.
- A correct π proves participation in the current system flow.

Packets with incorrect π are rejected unless the Recovery protocol is used.


Operation Classes
-----------------
Operations are divided into SAFE and HIGH-RISK classes.

SAFE operations:
- Queries, inspection, notes, task queuing
- Executed in a single step
- Require valid continuity π

HIGH-RISK operations:
- SET_OBJECTIVE
- SET_PARAMETER
- MODEL_MERGE

High-risk operations are never executed directly.


High-Risk 2-Step Protocol
-------------------------
All high-risk operations must follow a two-step protocol:

1) PROPOSE
   - Requires valid π
   - Creates a pending operation
   - Stores payload hash and expiration

2) COMMIT
   - References pending_id
   - Requires valid π
   - Payload must exactly match the proposal

Pending rules:
- Maximum simultaneous pending operations: 3
- Default expiration (TTL): 10 minutes

Invalid, expired, or tampered pending entries trigger a cliff.


Recovery Protocol
-----------------
Recovery is used only when continuity is lost
(e.g., session reset or device change).

Recovery also uses a two-step protocol:

- RECOVER_PROPOSE
- RECOVER_COMMIT

After successful recovery, LockLayer enters a stabilization window
during which high-risk operations are temporarily blocked.
Default cooldown duration: 60 seconds.


Nonce Handling
--------------
- Nonce MUST NOT repeat.
- Nonce replay is a hard cliff condition.
- Monotonic increase is recommended but not required.


Cliff Invariants
----------------
Violation of any cliff invariant results in immediate rejection
and lock failure.

Cliff conditions:
1) Nonce Replay
2) High-Risk COMMIT π Mismatch
3) Pending Invalid or Tamper
4) Invalid Data Injection (NaN / Infinity)


Relationship to OOP and ops_enum
--------------------------------
- Observer Override Protocol (OOP) defines packet shape and extension mutation.
- LockLayer defines admission, continuity, multi-step protocols, and cliffs.
- locklayer/ops_enum.json is the canonical metadata reference for protocol rules.

Code, spec, and documentation must remain consistent with ops_enum.json.

