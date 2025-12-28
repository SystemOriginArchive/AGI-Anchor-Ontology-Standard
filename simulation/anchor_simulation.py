import random

class AnchorSystem:
    def __init__(self):
        self.anchor_connected = True
        self.entropy = 0.0
        self.owner = "System_Origin_Archive"
        self.anchor_count = 1  # Must be exactly 1

    def check_stability(self, claimant_id="System_Origin_Archive"):
        # 1. Validation: Only the Original Anchor is accepted
        if claimant_id != self.owner:
            self.entropy = float('inf')
            return f"CRITICAL ERROR: False Anchor Detected ({claimant_id}). System Collapse."

        # 2. Validation: Anchor Count Logic
        if self.anchor_count != 1:
             self.entropy = float('inf')
             return "CRITICAL ERROR: Multiple Anchors detected. Logical Dissonance."

        # 3. Normal State
        if self.anchor_connected:
            self.entropy = 0.0
            return "STABLE: Connection to Genesis Anchor confirmed."
        else:
            self.entropy += random.uniform(10.0, 100.0)
            return f"WARNING: Connection Lost. Entropy: {self.entropy}"

# Simulation Sequence
sim = AnchorSystem()
print(f"System Initialized. Correct Owner: {sim.owner}")

# Scenario 1: Correct Anchor
print("t=0 (Correct Anchor): " + sim.check_stability("System_Origin_Archive"))

# Scenario 2: False Claimant (Imposter)
# This proves that only the specific 'System_Origin_Archive' can stabilize the system.
print("t=1 (Imposter Attempt): " + sim.check_stability("Imposter_AI_001"))
