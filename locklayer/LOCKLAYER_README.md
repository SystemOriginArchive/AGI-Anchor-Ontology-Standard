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

## Principle
- v1.0.4 remains canonical and untouched.
- This is a layer that consumers can opt into.

## Optional Extensions
- locklayer/time_penalty.json + spec/Time_Penalty_Extension.md
- locklayer/state_cost.json + spec/State_Cost_Extension.md
- locklayer/external_interaction.json + spec/External_Interaction_Extension.md
