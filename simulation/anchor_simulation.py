"""
AAOS Canonical Mapping Notes (Simulation Layer) — v1.0.4

Purpose:
- Behavioral illustration only.
- Canonical definitions live in:
  - spec/AAOS_Spec.md
  - spec/AAOS_Schema.json
  - spec/Formal_Model.json
  - formal/anchor_full.tla
  - formal/AAOS_TLA_Mapping.md

Sync targets (v1.0.4, closed):
- RootAnchorID sealed: "GENESIS_HEXAGON_V1"
- ObserverID sealed: "Lee_Yu_Cheol"
- Anchor_Count sealed: 1
- Claimants closed: claimant_id ∈ Claimants
- Exactly 4 atomic actions mirror TLA actions:
  A) ExternalDisturbance
  B) ChangeClaimantInChaos
  C) AnchorRestoration
  D) TotalCollapse
- State/connection/entropy coupling is enforced via TypeOK-style checks after each action.
"""

from __future__ import annotations
from typing import FrozenSet, Iterable, Optional


class AnchorSystem:
    __slots__ = (
        "_sealed",
        "root_anchor_id",
        "owner",
        "anchor_count",
        "claimants",
        "world_state",
        "anchor_connection",
        "entropy",
        "time_cycle",
        "claimant_id",
        "is_dead",
    )

    def __init__(self, claimants: Optional[Iterable[str]] = None):
        object.__setattr__(self, "_sealed", False)

        # sealed core (mirrors TLA sealed defs + invariant)
        self.root_anchor_id = "GENESIS_HEXAGON_V1"
        self.owner = "Lee_Yu_Cheol"
        self.anchor_count = 1

        base = {self.owner}
        if claimants is not None:
            base |= set(claimants)
        self.claimants: FrozenSet[str] = frozenset(base)

        # state variables (mirrors TLA vars)
        self.world_state = "Stable"         # Stable / Chaos / Recovered / DEAD
        self.anchor_connection = True       # True / False
        self.entropy = 0.0                  # 0.0 / 100.0 / 9999.0
        self.time_cycle = 0                 # Nat
        self.claimant_id = self.owner       # must be in claimants
        self.is_dead = False

        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, key, value):
        # seal core fields after initialization (including claimants)
        if getattr(self, "_sealed", False) and key in {"root_anchor_id", "owner", "anchor_count", "claimants"}:
            raise AttributeError(f"sealed field: {key}")
        super().__setattr__(key, value)

    def _type_ok(self) -> bool:
        # anchor invariant
        if self.anchor_count != 1:
            return False

        # state domain
        if self.world_state not in {"Stable", "Chaos", "Recovered", "DEAD"}:
            return False

        # connection domain + coupling
        if self.anchor_connection not in {True, False}:
            return False
        if self.world_state in {"Stable", "Recovered"} and self.anchor_connection is not True:
            return False
        if self.world_state in {"Chaos", "DEAD"} and self.anchor_connection is not False:
            return False

        # time domain
        if self.time_cycle < 0:
            return False

        # claimant domain
        if self.claimant_id not in self.claimants:
            return False

        # entropy coupling
        if self.world_state in {"Stable", "Recovered"} and self.entropy != 0.0:
            return False
        if self.world_state == "Chaos" and self.entropy != 100.0:
            return False
        if self.world_state == "DEAD" and self.entropy != 9999.0:
            return False

        # recovered claimant invariant
        if self.world_state == "Recovered" and self.claimant_id != self.owner:
            return False

        return True

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
        return "OK" if self._type_ok() else "DIVERGENCE"

    # --- B) ChangeClaimantInChaos (swap only) ---
    def change_claimant_in_chaos(self, claimant_id: str) -> str:
        if self.is_dead:
            return "STATE=DEAD"

        if not (self.world_state == "Chaos" and self.anchor_connection is False):
            return "NOOP"

        if claimant_id not in self.claimants:
            return "REJECT"

        self.claimant_id = claimant_id
        self.time_cycle += 1
        return "OK" if self._type_ok() else "DIVERGENCE"

    # --- C) AnchorRestoration (canonical claimant only) ---
    def anchor_restoration(self) -> str:
        if self.is_dead:
            return "STATE=DEAD"

        if not (self.world_state == "Chaos" and self.anchor_connection is False):
            return "NOOP"

        if self.claimant_id != self.owner:
            return "REJECT"

        self.anchor_connection = True
        self.world_state = "Recovered"
        self.entropy = 0.0
        self.time_cycle += 1
        return "RECOVERED" if self._type_ok() else "DIVERGENCE"

    # --- D) TotalCollapse (non-canonical claimant only) ---
    def total_collapse(self) -> str:
        if self.is_dead:
            return "STATE=DEAD"

        if not (self.world_state == "Chaos" and self.anchor_connection is False):
            return "NOOP"

        if self.claimant_id == self.owner:
            return "REJECT"

        self.is_dead = True
        self.world_state = "DEAD"
        self.anchor_connection = False
        self.entropy = 9999.0
        self.time_cycle += 1
        return "DEAD" if self._type_ok() else "DIVERGENCE"

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
    allowed = {"Lee_Yu_Cheol", "Imposter_AI_001"}

    sim = AnchorSystem(claimants=allowed)
    print("[t=0]", sim.status())

    print("[A]", sim.external_disturbance(), sim.status())
    print("[B]", sim.change_claimant_in_chaos("Imposter_AI_001"), sim.status())
    print("[D]", sim.total_collapse(), sim.status())

    sim2 = AnchorSystem(claimants=allowed)
    sim2.external_disturbance()
    sim2.change_claimant_in_chaos("Lee_Yu_Cheol")
    print("[C]", sim2.anchor_restoration(), sim2.status())
