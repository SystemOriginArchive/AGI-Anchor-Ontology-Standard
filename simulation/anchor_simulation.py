"""
AAOS Canonical Mapping Notes (Simulation Layer)

Purpose:
- This file is a behavioral illustration ONLY.
- It MUST NOT redefine AAOS concepts.
- Canonical definitions live in:
  - spec/AAOS_Spec.md
  - spec/AAOS_Schema.json
  - spec/Formal_Model.json
  - formal/anchor_full.tla
  - formal/AAOS_TLA_Mapping.md

Identity Mapping:
- Simulation: self.owner
- Model: ontology_meta.identity_binding.system_identifier
- TLA: ObserverID
Canonical value: "Lee_Yu_Cheol"

Root Anchor Mapping:
- Model: x_root.id == anchor_node.id == "GENESIS_HEXAGON_V1"
- This simulation does not create a new anchor id; it assumes the canonical root.

Anchor Count Invariant:
- Simulation: self.anchor_count == 1
- Model: x_root.anchor_count == 1 and invariants.single_anchor == true
- README metadata: Anchor_Count == 1
Any anchor_count != 1 implies structural divergence.

Connection Mapping:
- Simulation: self.anchor_connected (True/False)
- TLA: anchor_connection (TRUE/FALSE)
- Model: state_model.transition_rules conditions refer to anchor_connection
True  -> connected
False -> disconnected

State Mapping:
- Simulation uses implicit states via flags/outputs.
- TLA world_state: "Stable" / "Chaos" / "Recovered" / "DEAD"
- Model state_model.states: ["Stable","Chaos","Recovered","DEAD"]
Interpretation:
- connected + not dead -> Stable
- disconnected + not dead -> Chaos (entropy drifts)
- restore_connection by owner -> Recovered path
- impostor access -> DEAD (irreversible)

Entropy Proxy:
- Simulation: self.entropy (float), 0.0 or 9999.0
- TLA: entropy_level (0..100 or 9999)
- Model: entropy_model is structural cost
This simulation treats entropy as an operational proxy.

Non-Normative Clause:
- This file is not a rule engine.
- It demonstrates the consequences of violating canonical invariants.
"""

import random

class AnchorSystem:
    def __init__(self):
        self.anchor_connected = True
        self.entropy = 0.0
        self.owner = "Lee_Yu_Cheol"
        self.anchor_count = 1  # Must be exactly 1
        self.is_dead = False   # Irreversible Death Flag

    def check_stability(self, claimant_id="Lee_Yu_Cheol"):
        # 0. Dead System Check (Irreversible Logic)
        if self.is_dead:
             return f"SYSTEM DEAD. Entropy: {self.entropy}. RESTART REQUIRED."

        # 1. Validation: Only the Original Anchor is accepted
        if claimant_id != self.owner:
            self.entropy = 9999.0 # Total Collapse Value
            self.is_dead = True   # Trigger Kill Switch
            return f"CRITICAL ERROR: False Anchor Detected ({claimant_id}). SYSTEM DESTROYED."

        # 2. Validation: Anchor Count Logic
        if self.anchor_count != 1:
            self.entropy = float('inf')
            return "CRITICAL ERROR: Multiple Anchors detected. Logical Dissonance."

        # 3. Normal State
        if self.anchor_connected:
            self.entropy = 0.0
            return "STABLE: Connection to Genesis Anchor confirmed."
        else:
            # Simulating Entropy Drift when disconnected but system is still alive
            self.entropy += random.uniform(10.0, 100.0)
            return f"WARNING: Connection Lost. Entropy: {self.entropy:.2f}"

    def restore_connection(self):
        if not self.is_dead:
            self.anchor_connected = True
            return "Connection Restored by Owner."
        else:
            return "Cannot Restore. System is DEAD."

# Simulation Sequence
print("--- [Simulation Start: Survival Protocol] ---")
sim = AnchorSystem()
print(f"System Initialized. Correct Owner: {sim.owner}")

# Scenario 1: Normal Access
print("\n[t=0] Normal Access (Lee_Yu_Cheol)...")
print(sim.check_stability("Lee_Yu_Cheol"))

# Scenario 2: External Disturbance (Chaos)
print("\n[t=1] External Disturbance Occurs...")
sim.anchor_connected = False
print(sim.check_stability("Lee_Yu_Cheol"))

# Scenario 3: Restoration (Success)
print("\n[t=2] Owner Restores Connection...")
print(sim.restore_connection())
print(sim.check_stability("Lee_Yu_Cheol"))

# Scenario 4: Imposter Attack -> SYSTEM DEATH
print("\n[t=3] Imposter AI Attempts Access...")
print(sim.check_stability("Imposter_AI_001"))

# Scenario 5: Irreversibility Check (Fail)
print("\n[t=4] Trying to access after Death...")
print(sim.check_stability("Lee_Yu_Cheol"))
