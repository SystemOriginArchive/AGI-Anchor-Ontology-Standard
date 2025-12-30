"""
AAOS Canonical Mapping Notes (Simulation Layer)

Purpose:
- Behavioral illustration only.
- Canonical definitions live in:
  - spec/AAOS_Spec.md
  - spec/AAOS_Schema.json
  - spec/Formal_Model.json
  - formal/anchor_full.tla
  - formal/AAOS_TLA_Mapping.md

Sync targets (v1.0.4):
- RootAnchorID is explicit and fixed: "GENESIS_HEXAGON_V1"
- Exactly 4 actions mirror TLA actions:
  A) ExternalDisturbance: Stable -> Chaos
  B) ChangeClaimantInChaos: Chaos -> Chaos (swap only)
  C) AnchorRestoration: Chaos -> Recovered (only canonical claimant)
  D) TotalCollapse: Chaos -> DEAD (only on intervention by non-canonical claimant)
- Anchor_Count == 1 is enforced.
"""

from typing import Optional


class AnchorSystem:
    def __init__(self):
        # Sealed constants (mirrors TLA constants)
        self.root_anchor_id = "GENESIS_HEXAGON_V1"
        self.owner = "Lee_Yu_Cheol"

        # Cross-layer invariant
        self.anchor_count = 1

        # State variables (mirrors TLA vars)
        self.world_state = "Stable"         # Stable / Chaos / Recovered / DEAD
        self.anchor_connection = True       # True(connected) / False(disconnected)
        self.entropy = 0.0                  # 0.0 / 100.0 / 9999.0
        self.time_cycle = 0                 # logical clock
        self.claimant_id = self.owner       # dynamic actor

        self.is_dead = False

    # --- A) ExternalDisturbance ---
    def external_disturbance(self) -> str:
        if self.is_dead:
            return "STATE=DEAD"

        if not (self.world_state == "Stable" and self.anchor_connection is True):
            return "NOOP"

        self.anchor_connection = False
        self.world_state = "Chaos"
        self.entropy = 100.0
        self.time_cycle += 1
        return "OK"

    # --- B) ChangeClaimantInChaos (swap only) ---
    def change_claimant_in_chaos(self, claimant_id: str) -> str:
        if self.is_dead:
            return "STATE=DEAD"

        if not (self.world_state == "Chaos" and self.anchor_connection is False):
            return "NOOP"

        self.claimant_id = claimant_id
        self.time_cycle += 1
        return "OK"

    # --- C/D) Intervention inside Chaos (restoration attempt) ---
    def intervene_restore(self, claimant_id: Optional[str] = None) -> str:
        if self.is_dead:
            return "STATE=DEAD"

        # Anchor_Count invariant
        if self.anchor_count != 1:
            self.entropy = float("inf")
            return "DIVERGENCE"

        if claimant_id is not None:
            self.claimant_id = claimant_id

        # Rule applies only in Chaos/disconnected
        if not (self.world_state == "Chaos" and self.anchor_connection is False):
            return "NOOP"

        if self.claimant_id == self.owner:
            # C) AnchorRestoration
            self.anchor_connection = True
            self.world_state = "Recovered"
            self.entropy = 0.0
            self.time_cycle += 1
            return "RECOVERED"
        else:
            # D) TotalCollapse (intervention by non-canonical claimant)
            self.is_dead = True
            self.world_state = "DEAD"
            self.anchor_connection = False
            self.entropy = 9999.0
            self.time_cycle += 1
            return "DEAD"

    def status(self) -> str:
        return (
            f"root={self.root_anchor_id} | "
            f"Anchor_Count={self.anchor_count} | "
            f"STATE={self.world_state} | "
            f"anchor_connection={self.anchor_connection} | "
            f"claimant={self.claimant_id} | "
            f"entropy={self.entropy} | "
            f"t={self.time_cycle}"
        )


if __name__ == "__main__":
    # Demo sequence (mirrors the mapping narrative)
    sim = AnchorSystem()
    print("[t=0]", sim.status())

    # A) ExternalDisturbance
    print("[A]", sim.external_disturbance(), sim.status())

    # B) Claimant swap in Chaos (no collapse)
    print("[B]", sim.change_claimant_in_chaos("Imposter_AI_001"), sim.status())

    # D) Non-canonical intervention -> DEAD
    print("[D]", sim.intervene_restore(), sim.status())

    # Fresh system -> canonical restoration path
    sim2 = AnchorSystem()
    sim2.external_disturbance()
    sim2.change_claimant_in_chaos("Lee_Yu_Cheol")
    print("[C]", sim2.intervene_restore(), sim2.status())
