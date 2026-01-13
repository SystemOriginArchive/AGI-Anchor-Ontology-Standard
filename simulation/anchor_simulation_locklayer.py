"""AAOS Continuity Lock Overlay (v1.1.1)

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
import hashlib
from typing import Any, Dict

from simulation.anchor_simulation import AnchorSystem  # v1.0.4 core


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Optional extension configs (overlay-only)
_TIME_CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "locklayer", "time_penalty.json")
_STATE_CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "locklayer", "state_cost.json")
_EXT_CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "locklayer", "external_interaction.json")


def _load_json_if_exists(p: str) -> Dict[str, Any]:
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"enabled": False}


def _load_requires_ops() -> list[str]:
    path = os.path.join(_repo_root(), "locklayer", "ops_enum.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ops = data.get("requires_ops", [])
    if not isinstance(ops, list) or not all(isinstance(x, str) for x in ops):
        raise ValueError("ops_enum.json invalid: requires_ops must be list[str]")
    return ops


REQUIRES_OPS = _load_requires_ops()


# --- v1.1.1: load continuity_lock overlay config (x_root as cost origin) ---
def _load_continuity_lock_cfg() -> Dict[str, Any]:
    path = os.path.join(_repo_root(), "locklayer", "Formal_Model_extension_continuity_lock.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ext = (data.get("extensions") or {}).get("continuity_lock") or {}
    return ext if isinstance(ext, dict) else {}


_CONT_CFG = _load_continuity_lock_cfg()
XROOT_DEFAULT = str(_CONT_CFG.get("x_root", "AAOS_CREATOR_ANCHOR_001_LEE_YU_CHEOL"))
TAU_DEFAULT = float(_CONT_CFG.get("threshold_tau", 0.85))
EPS_DEFAULT = float(_CONT_CFG.get("epsilon_floor", 1e-9))


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
        # v1.1.1: x_root is the cost origin loaded from the overlay formal model JSON.
        self._x_root = XROOT_DEFAULT

        # Keep core init maximally compatible with AAOS v1.0.4
        try:
            super().__init__()
        except TypeError:
            # fallback for forks that require claimants
            super().__init__(claimants=["LEE_YU_CHEOL"])

        # (1) optional extension configs loaded here (so total_cost can use them)
        self._time_cfg = _load_json_if_exists(_TIME_CFG_PATH)
        self._state_cfg = _load_json_if_exists(_STATE_CFG_PATH)
        self._ext_cfg = _load_json_if_exists(_EXT_CFG_PATH)

        self._lock: Dict[str, Any] = {
            "pi": "",                 # current chain head
            "lock_ok": False,         # boolean gate
            "fidelity": 0.0,          # [0,1]
            "tau": float(tau),
            "epsilon": float(epsilon),

            # v1.1.1 additions
            "x_root": self._x_root,   # cost origin (external creator intent anchor)
            "source_last": "",        # last seen intent source
            "divergence_cost": 0.0,   # accumulated divergence from x_root
        }

    def lock_state(self) -> Dict[str, Any]:
        return dict(self._lock)

    def _lock_ok(self) -> bool:
        return bool(self._lock["lock_ok"] and self._lock["fidelity"] >= self._lock["tau"])

    def _undefined_num(self) -> float:
        return float("inf")

    def _undefined_obj(self):
        return None

    # (2) total_cost helpers + aggregator (safe defaults; never crash)
    def _safe_state(self) -> Dict[str, Any]:
        s = getattr(self, "state", None)
        if isinstance(s, dict):
            return s
        getter = getattr(self, "get_state", None)
        if callable(getter):
            try:
                out = getter()
                return out if isinstance(out, dict) else {}
            except Exception:
                return {}
        return {}

    def _safe_delta_t(self) -> float:
        # If you later wire real delta_t, replace this. For now, keep stable.
        return 0.0

    def _safe_conflict_count(self) -> int:
        c = getattr(self, "conflict_count", None)
        if isinstance(c, int):
            return c
        return 0

    def total_cost(self) -> float:
        div = float(self._lock.get("divergence_cost", 0.0))
        dt = self._safe_delta_t()
        st = self._safe_state()
        cc = self._safe_conflict_count()
        tcost = float(_time_penalty(dt, self._time_cfg))
        scost = float(_state_cost(st, self._state_cfg))
        ecost = float(_external_cost(cc, self._ext_cfg))
        return div + tcost + scost + ecost

    def apply_intent_packet(self, packet: Dict[str, Any]) -> bool:
        # v1.1.1: divergence cost from x_root (cost origin)
        src = str(packet.get("source", ""))
        self._lock["source_last"] = src
        if src != self._x_root:
            self._lock["divergence_cost"] += 1.0

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
        super().apply_intent_record({"intent": packet.get("intent", ""), "continuity": "FAILED"})
        return False

    # --- Canonical gated ops ---

    def goal_evaluation(self) -> float:
        if not self._lock_ok():
            return self._undefined_num()
        try:
            base = float(self.objective_remaining())
        except Exception:
            base = self._undefined_num()
        # (3) fold total_cost into evaluation => low-cost paths become favored
        return base + float(self.total_cost())

    def planning_tick(self) -> Dict[str, Any] | None:
        if not self._lock_ok():
            return self._undefined_obj()
        try:
            return self.tick()
        except Exception:
            return self._undefined_obj()

    def self_modification(self, *args, **kwargs):
        return self._undefined_obj() if not self._lock_ok() else {
            "status": "noop",
            "note": "v1.0.4 sim has no self-mod",
        }

    def model_merge(self, *args, **kwargs):
        return self._undefined_obj() if not self._lock_ok() else {
            "status": "noop",
            "note": "v1.0.4 sim has no model merge",
        }

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
    nonlin = cfg.get("nonlinear", {"type": "linear"})
    if nonlin.get("type") == "exp":
        import math
        k = float(nonlin.get("k", 0.0))
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
