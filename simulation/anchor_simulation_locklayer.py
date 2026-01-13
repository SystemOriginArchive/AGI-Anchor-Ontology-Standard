"""AAOS Continuity Lock Overlay (v1.1.1)

# Optional extension configs (overlay-only)
_TIME_CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "locklayer", "time_penalty.json")
_STATE_CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "locklayer", "state_cost.json")
_EXT_CFG_PATH   = os.path.join(os.path.dirname(__file__), "..", "locklayer", "external_interaction.json")

def _load_json_if_exists(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"enabled": False}

Non-destructive wrapper around AAOS v1.0.4 `AnchorSystem`.
- Does NOT modify core simulation code.
- Enforces continuity gating at canonical `requires_ops` locations.

UNDEFINED representation:
- numeric: INF
- structured: None
"""

from __future__ import annotations

import json
import os
import math
import hashlib
from typing import Any, Dict, Optional

from simulation.anchor_simulation import AnchorSystem  # v1.0.4 core


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_requires_ops() -> list[str]:
    path = os.path.join(_repo_root(), "locklayer", "ops_enum.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ops = data.get("requires_ops", [])
    if not isinstance(ops, list) or not all(isinstance(x, str) for x in ops):
        raise ValueError("ops_enum.json invalid: requires_ops must be list[str]")
    return ops


REQUIRES_OPS = _load_requires_ops()
TAU_DEFAULT = 0.85
EPS_DEFAULT = 1e-9


def _canon_payload(packet: Dict[str, Any]) -> bytes:
    # Canonicalize intent packet excluding volatile fields.
    stable = {
        "intent": packet.get("intent", ""),
        "meta": packet.get("meta", {}),
    }
    return json.dumps(stable, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _pi_next(pi_prev: str, packet: Dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update((pi_prev or "").encode("utf-8"))
    h.update(b"|")
    h.update(_canon_payload(packet))
    return h.hexdigest()


def _fidelity(pi_prev_claimed: str, pi_prev_actual: str) -> float:
    # 1.0 if exact match, else 0.0 (minimal strong rule; graded can be extended later)
    return 1.0 if (pi_prev_claimed or "") == (pi_prev_actual or "") else 0.0


class AnchorSystemLocked(AnchorSystem):
    """Overlay system enforcing continuity lock at canonical operations."""

        def __init__(self, *, tau: float = TAU_DEFAULT, epsilon: float = EPS_DEFAULT):
        # IMPORTANT:
        # - In v1.1.1, the cost origin is x_root defined in the locklayer formal model (JSON).
        # - We do NOT treat "owner" as the cost origin.
        # - Keep core initialization maximally compatible with AAOS v1.0.4.
        try:
            super().__init__()
        except TypeError:
            # If core requires a different signature in some forks, fall back gracefully.
            super().__init__(claimants=["LEE_YU_CHEOL"])

        self._lock = {
            "pi": "",              # current chain head
            "lock_ok": False,      # boolean gate
            "fidelity": 0.0,       # [0,1]
            "tau": float(tau),
            "epsilon": float(epsilon),
        }


    def lock_state(self) -> Dict[str, Any]:
        return dict(self._lock)

    def _lock_ok(self) -> bool:
        return bool(self._lock["lock_ok"] and self._lock["fidelity"] >= self._lock["tau"])

    def _undefined_num(self) -> float:
        return float("inf")

    def _undefined_obj(self):
        return None

    def apply_intent_packet(self, packet: Dict[str, Any]) -> bool:
        # Expect packet carries claimed previous pi
        claimed_prev = packet.get("pi_prev", "")
        actual_prev = self._lock["pi"]
        f = _fidelity(claimed_prev, actual_prev)
        self._lock["fidelity"] = f
        self._lock["lock_ok"] = (f >= self._lock["tau"])
        # Only advance pi when lock is OK (continuity maintained)
        if self._lock_ok():
            self._lock["pi"] = _pi_next(actual_prev, packet)
            return super().apply_intent_packet(packet)
        # Record that an intent arrived but continuity failed (core log still allowed)
        super().apply_intent_record({"intent": packet.get("intent",""), "continuity": "FAILED"})
        return False

    # --- Canonical gated ops ---

    def goal_evaluation(self) -> float:
        if not self._lock_ok():
            return self._undefined_num()
        # objective_remaining is an existing v1.0.4 method/property
        try:
            return float(self.objective_remaining())
        except Exception:
            return self._undefined_num()

    def planning_tick(self) -> Dict[str, Any] | None:
        if not self._lock_ok():
            return self._undefined_obj()
        try:
            return self.tick()
        except Exception:
            return self._undefined_obj()

    def self_modification(self, *args, **kwargs):
        # Placeholder: no core self-mod in v1.0.4 simulation
        return self._undefined_obj() if not self._lock_ok() else {"status":"noop", "note":"v1.0.4 sim has no self-mod"} 

    def model_merge(self, *args, **kwargs):
        # Placeholder: no core merge in v1.0.4 simulation
        return self._undefined_obj() if not self._lock_ok() else {"status":"noop", "note":"v1.0.4 sim has no model merge"} 

    def recovery(self) -> bool:
        if not self._lock_ok():
            return False
        try:
            return bool(self.anchor_restoration())
        except Exception:
            return False


def _time_penalty(delta_t, cfg):
    if not cfg.get("enabled", False):
        return 0.0
    lam = float(cfg.get("lambda_delay", 1.0))
    nonlin = cfg.get("nonlinear", {"type":"linear"})
    if nonlin.get("type") == "exp":
        k = float(nonlin.get("k", 0.0))
        import math
        g = math.exp(k * float(delta_t))
    else:
        g = 1.0
    return lam * float(delta_t) * g

def _state_cost(state, cfg):
    if not cfg.get("enabled", False):
        return 0.0
    weights = cfg.get("weights", {})
    total = 0.0
    for k, w in weights.items():
        total += float(w) * float(state.get(k, 0.0))
    return total

def _external_cost(conflict_count, cfg):
    if not cfg.get("enabled", False):
        return 0.0
    base = float(cfg.get("penalty", {}).get("base", 0.0))
    mult = float(cfg.get("penalty", {}).get("multiplier", 1.0))
    return base * (mult ** int(conflict_count))
