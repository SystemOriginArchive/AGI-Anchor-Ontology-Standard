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
