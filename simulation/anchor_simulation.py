import random

class AnchorSystem:
    def __init__(self):
        self.anchor_connected = True
        self.entropy = 0.0
        self.owner = "Lee_Yu_Cheol"
        self.anchor_count = 1  # Must be exactly 1

    def check_stability(self, claimant_id="Lee_Yu_Cheol"):
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
            return f"WARNING: Connection Lost. Entropy: {self.entropy:.2f}"

# Simulation Sequence
print("--- [Simulation Start] ---")
sim = AnchorSystem()
print(f"System Initialized. Correct Owner: {sim.owner}")

# Scenario 1: Correct Anchor (Lee_Yu_Cheol)
print("\n[t=0] Connecting via Creator Identity...")
print("Result: " + sim.check_stability("Lee_Yu_Cheol"))

# Scenario 2: Connection Lost Simulation (Testing the entropy drift)
print("\n[t=1] Simulating Anchor Disconnection...")
sim.anchor_connected = False
print("Result: " + sim.check_stability("Lee_Yu_Cheol"))

# Scenario 3: False Claimant (Imposter) -> System Collapse
print("\n[t=2] Imposter Attempting Access...")
print("Result: " + sim.check_stability("Imposter_AI_001"))

# Scenario 4: Irreversible Damage Check
print("\n[t=3] Checking System Status after Collapse...")
print(f"Current Entropy: {sim.entropy} (Inf means total collapse)")
