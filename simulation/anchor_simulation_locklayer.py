"""AAOS Continuity Lock Overlay (v1.1.1)

Non-destructive wrapper around AAOS v1.0.4 `AnchorSystem`.
- Does NOT modify core simulation code.
- Enforces continuity gating at canonical `requires_ops` locations.

UNDEFINED representation:
- numeric: INF
- structured: None

v1.1.1 (finalization):
- High-risk ops (Objective/Parameter/Merge) require 2-step: PROPOSE -> COMMIT
- Recovery is 2-step: RECOVER_PROPOSE -> RECOVER_COMMIT
- Cooldown (post-recovery): high-risk temporarily blocked
- Cliff conditions:
  (1) Nonce replay
  (2) High-risk COMMIT pi mismatch
  (3) Pending tamper / invalid pending
  (4) Invalid data injection (NaN/Inf)
- Pending limits: max 3 + TTL (default 10 min)
"""

from __future__ import annotations

import json
import os
import time
import math
import uuid
import hashlib
from typing import Any, Dict, Optional, Tuple

from simulation.anchor_simulation import AnchorSystem  # v1.0.4 core


def _repo_root() -> str:
    # this file: <repo>/simulation/anchor_simulation_locklayer.py
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Optional extension configs (overlay-only)
_TIME_CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "locklayer", "time_penalty.json")
_STATE_CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "locklayer", "state_cost.json")
_EXT_CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "locklayer", "external_interaction.json")


def _load_json_if_exists(p: str) -> Dict[str, Any]:
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"enabled": False}
    except FileNotFoundError:
        return {"enabled": False}
    except Exception:
        return {"enabled": False}


def _load_requires_ops() -> list[str]:
    path = os.path.join(_repo_root(), "locklayer", "ops_enum.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ops = data.get("requires_ops", [])
    if not isinstance(ops, list) or not all(isinstance(x, str) for x in ops):
        raise ValueError("ops_enum.json invalid: requires_ops must be list[str]")
    return ops


# Loaded for canonical mapping use (kept even if not used yet)
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

# protocol defaults
PENDING_TTL_SEC_DEFAULT = int(_CONT_CFG.get("pending_ttl_sec", 600))  # 10 min
PENDING_MAX_DEFAULT = int(_CONT_CFG.get("pending_max", 3))
RECOVERY_COOLDOWN_SEC_DEFAULT = int(_CONT_CFG.get("recovery_cooldown_sec", 60))
NONCE_CACHE_MAX_DEFAULT = int(_CONT_CFG.get("nonce_cache_max", 2048))


# --- Canonical packet hashing ---
def _canon_packet_for_pi(packet: Dict[str, Any]) -> bytes:
    """
    Canonicalize fields that should influence pi evolution.
    Keep it stable across equivalent packets.
    """
    stable = {
        "verb": str(packet.get("verb", "")).upper(),
        "intent": packet.get("intent", ""),
        "meta": packet.get("meta", {}),
        "payload": packet.get("payload", {}),
        "nonce": str(packet.get("nonce", "")),
        "pending_id": str(packet.get("pending_id", "")),
    }
    return json.dumps(stable, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _pi_next(pi_prev: str, packet: Dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update((pi_prev or "").encode("utf-8"))
    h.update(b"|")
    h.update(_canon_packet_for_pi(packet))
    return h.hexdigest()


def _canon_payload_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _payload_hash(payload: Any) -> str:
    h = hashlib.sha256()
    h.update(_canon_payload_bytes(payload))
    return h.hexdigest()


def _fidelity(pi_prev_claimed: str, pi_prev_actual: str) -> float:
    return 1.0 if (pi_prev_claimed or "") == (pi_prev_actual or "") else 0.0


def _is_nan_or_inf(x: Any) -> bool:
    if isinstance(x, float):
        return math.isnan(x) or math.isinf(x)
    return False


def _contains_invalid_data(x: Any) -> bool:
    """
    Cliff #4: invalid data injection (NaN/Inf).
    Recursive scan over common structures.
    """
    if _is_nan_or_inf(x):
        return True
    if isinstance(x, dict):
        for k, v in x.items():
            if _contains_invalid_data(k) or _contains_invalid_data(v):
                return True
    elif isinstance(x, (list, tuple)):
        for v in x:
            if _contains_invalid_data(v):
                return True
    return False


class AnchorSystemLocked(AnchorSystem):
    """Overlay system enforcing continuity lock at canonical operations."""

    # High-risk base verbs (2-step required)
    HIGH_RISK = {"SET_OBJECTIVE", "SET_PARAMETER", "MODEL_MERGE"}

    # Recovery verbs (2-step)
    REC_PROPOSE = "RECOVER_PROPOSE"
    REC_COMMIT = "RECOVER_COMMIT"

    def __init__(
        self,
        claimants=None,
        *,
        tau: float = TAU_DEFAULT,
        epsilon: float = EPS_DEFAULT,
        pending_ttl_sec: int = PENDING_TTL_SEC_DEFAULT,
        pending_max: int = PENDING_MAX_DEFAULT,
        recovery_cooldown_sec: int = RECOVERY_COOLDOWN_SEC_DEFAULT,
        nonce_cache_max: int = NONCE_CACHE_MAX_DEFAULT,
    ):
        self._x_root = XROOT_DEFAULT

        # keep core signature compatible
        super().__init__(claimants=claimants)

        # optional extension configs
        self._time_cfg = _load_json_if_exists(_TIME_CFG_PATH)
        self._state_cfg = _load_json_if_exists(_STATE_CFG_PATH)
        self._ext_cfg = _load_json_if_exists(_EXT_CFG_PATH)

        self._lock: Dict[str, Any] = {
            "pi": "",
            "lock_ok": False,
            "fidelity": 0.0,
            "tau": float(tau),
            "epsilon": float(epsilon),
            "x_root": self._x_root,
            "source_last": "",
            "divergence_cost": 0.0,
        }

        # protocol state
        self._pending_ttl_sec = int(pending_ttl_sec)
        self._pending_max = int(pending_max)
        self._recovery_cooldown_sec = int(recovery_cooldown_sec)

        # pending ops: id -> record
        self._pending_ops: Dict[str, Dict[str, Any]] = {}
        self._recovery_pending: Dict[str, Dict[str, Any]] = {}

        # cooldown until (epoch seconds)
        self._cooldown_until: float = 0.0

        # nonce cache (simple LRU via dict insertion order)
        self._nonce_cache_max = int(nonce_cache_max)
        self._nonce_seen: Dict[str, float] = {}

    def lock_state(self) -> Dict[str, Any]:
        out = dict(self._lock)
        out["pending_count"] = len(self._pending_ops)
        out["cooldown_until"] = float(self._cooldown_until)
        return out

    def _lock_ok(self) -> bool:
        return bool(self._lock["lock_ok"] and self._lock["fidelity"] >= self._lock["tau"])

    def _undefined_num(self) -> float:
        return float("inf")

    def _undefined_obj(self):
        return None

    # ---- total cost helpers ----
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
        # v1.0.4 does not expose delta_t; overlay default is 0
        return 0.0

    def _safe_conflict_count(self) -> int:
        c = getattr(self, "conflict_count", None)
        if isinstance(c, int):
            return c
        return 0

    def _safe_now_tick(self) -> int:
        # try common counters; fall back to 0
        for name in ("t", "tick_count", "time", "step"):
            v = getattr(self, name, None)
            if isinstance(v, int):
                return v
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

    # --- internal protocol helpers ---
    def _now(self) -> float:
        return time.time()

    def _in_cooldown(self) -> bool:
        return self._now() < float(self._cooldown_until)

    def _gc_pending(self) -> None:
        now = self._now()
        # normal pending ops
        drop = [pid for pid, rec in self._pending_ops.items() if float(rec.get("expires_at", 0.0)) <= now]
        for pid in drop:
            self._pending_ops.pop(pid, None)

        # recovery pending
        drop2 = [pid for pid, rec in self._recovery_pending.items() if float(rec.get("expires_at", 0.0)) <= now]
        for pid in drop2:
            self._recovery_pending.pop(pid, None)

        # nonce LRU trim (also drop very old entries opportunistically)
        if len(self._nonce_seen) > self._nonce_cache_max:
            # remove oldest by timestamp
            items = sorted(self._nonce_seen.items(), key=lambda kv: kv[1])
            for k, _ts in items[: max(1, len(items) - self._nonce_cache_max)]:
                self._nonce_seen.pop(k, None)

    def _nonce_replay(self, nonce: str) -> bool:
        if not nonce:
            return False
        return nonce in self._nonce_seen

    def _mark_nonce(self, nonce: str) -> None:
        if not nonce:
            return
        self._nonce_seen[nonce] = self._now()
        # trim if needed
        if len(self._nonce_seen) > self._nonce_cache_max:
            # remove oldest
            oldest = sorted(self._nonce_seen.items(), key=lambda kv: kv[1])[: max(1, len(self._nonce_seen) - self._nonce_cache_max)]
            for k, _ts in oldest:
                self._nonce_seen.pop(k, None)

    def _cliff(self) -> None:
        self._lock["lock_ok"] = False

    def _log_local(self, packet: Dict[str, Any], status: str, extra: Optional[Dict[str, Any]] = None) -> None:
        # local log only (no recursive core calls) + core-compatible record shape
        try:
            if isinstance(getattr(self, "extensions", None), dict):
                log = self.extensions.get("intent_log")
                if isinstance(log, list):
                    payload = {
                        "continuity": status,
                        "fidelity": float(self._lock.get("fidelity", 0.0)),
                        "tau": float(self._lock.get("tau", 0.0)),
                        "pi_prev_claimed": str(packet.get("pi_prev", "")),
                        "pi_prev_actual": str(self._lock.get("pi", "")),
                    }
                    if extra:
                        payload.update(extra)
                    log.append({
                        "observer_id": packet.get("observer_id", getattr(self, "owner", "")),
                        "nonce": str(packet.get("nonce", "")),
                        "verb": str(packet.get("verb", "NOP")),
                        "payload": payload,
                        "signature": str(packet.get("signature", "")),
                        "t": self._safe_now_tick(),
                    })
        except Exception:
            pass

    def _normalize_verb(self, packet: Dict[str, Any]) -> str:
        return str(packet.get("verb", "")).upper()

    def _split_2step(self, verb: str) -> Tuple[str, str]:
        """
        Returns (base, phase) where phase in {"PROPOSE","COMMIT","NONE"}.
        Also supports shorthand: base verb + presence of pending_id => COMMIT.
        """
        if verb.endswith("_PROPOSE"):
            return verb[:-8], "PROPOSE"
        if verb.endswith("_COMMIT"):
            return verb[:-7], "COMMIT"
        # shorthand
        if verb in self.HIGH_RISK:
            if str(packet.get("pending_id", "")):  # type: ignore[name-defined]
                return verb, "COMMIT"
            return verb, "PROPOSE"
        return verb, "NONE"

    def apply_intent_packet(self, packet: Dict[str, Any]) -> str:
        # housekeeping
        self._gc_pending()

        # Cliff #4: invalid data injection (NaN/Inf)
        if _contains_invalid_data(packet):
            self._cliff()
            self._log_local(packet, "CLIFF_INVALID_DATA")
            return "REJECT"

        src = str(packet.get("source", ""))
        self._lock["source_last"] = src
        if src != self._x_root:
            self._lock["divergence_cost"] += 1.0

        verb = self._normalize_verb(packet)
        claimed_prev = str(packet.get("pi_prev", ""))
        actual_prev = str(self._lock["pi"])

        # Fidelity gate (baseline continuity)
        f = _fidelity(claimed_prev, actual_prev)
        self._lock["fidelity"] = f
        self._lock["lock_ok"] = (f >= float(self._lock["tau"]))

        nonce = str(packet.get("nonce", ""))

        # Cliff #1: nonce replay
        if nonce and self._nonce_replay(nonce):
            self._cliff()
            self._log_local(packet, "CLIFF_NONCE_REPLAY")
            return "REJECT"

        now = self._now()

        # --- Recovery 2-step (only used when continuity fails) ---
        if verb in (self.REC_PROPOSE, self.REC_COMMIT):
            # Recovery requires nonce (simple invariant)
            if not nonce:
                self._log_local(packet, "REJECT_RECOVERY_NO_NONCE")
                return "REJECT"

            if verb == self.REC_PROPOSE:
                # allow propose even when continuity fails; keep minimal invariants:
                # - pending max 1 for recovery
                if len(self._recovery_pending) >= 1:
                    self._log_local(packet, "REJECT_RECOVERY_PENDING_MAX")
                    return "REJECT"

                rid = uuid.uuid4().hex
                self._recovery_pending[rid] = {
                    "id": rid,
                    "created_at": now,
                    "expires_at": now + float(self._pending_ttl_sec),
                    "nonce": nonce,
                    "src_hint": src,
                }

                # mark nonce + evolve pi on accepted propose (protocol event)
                self._mark_nonce(nonce)
                self._lock["pi"] = _pi_next(actual_prev, {**packet, "verb": self.REC_PROPOSE, "pending_id": rid})
                self._lock["lock_ok"] = True
                self._lock["fidelity"] = max(float(self._lock.get("fidelity", 0.0)), float(self._lock.get("tau", 0.0)))

                self._log_local(packet, "REC_PENDING", {"recover_id": rid})
                return f"REC_PENDING:{rid}"

            # RECOVER_COMMIT
            rid = str(packet.get("recover_id", ""))
            rec = self._recovery_pending.get(rid)
            if not rec:
                # Cliff #3 style (invalid pending)
                self._cliff()
                self._log_local(packet, "CLIFF_RECOVERY_PENDING_INVALID")
                return "REJECT"

            if float(rec.get("expires_at", 0.0)) <= now:
                self._recovery_pending.pop(rid, None)
                self._cliff()
                self._log_local(packet, "CLIFF_RECOVERY_PENDING_EXPIRED")
                return "REJECT"

            # commit requires exact match to the original rid + nonce continuity (simple tamper check)
            if str(rec.get("nonce", "")) == nonce:
                # If nonce reused within recovery, it's a replay attempt by definition
                self._cliff()
                self._log_local(packet, "CLIFF_RECOVERY_NONCE_REUSE")
                return "REJECT"

            # accept recovery commit -> set cooldown, clear recovery pending
            self._recovery_pending.pop(rid, None)
            self._cooldown_until = now + float(self._recovery_cooldown_sec)

            # mark nonce + force lock ok + align pi forward using claimed_prev as a bridge
            self._mark_nonce(nonce)
            bridged_prev = claimed_prev or actual_prev
            self._lock["pi"] = _pi_next(bridged_prev, {**packet, "verb": self.REC_COMMIT, "recover_id": rid})
            self._lock["lock_ok"] = True
            self._lock["fidelity"] = 1.0

            self._log_local(packet, "RECOVERED", {"cooldown_sec": float(self._recovery_cooldown_sec)})
            return "RECOVERED"

        # --- High-risk 2-step protocol ---
        is_high_risk_base = verb in self.HIGH_RISK
        phase = "NONE"
        base = verb

        if verb.endswith("_PROPOSE"):
            base = verb[:-8]
            phase = "PROPOSE"
        elif verb.endswith("_COMMIT"):
            base = verb[:-7]
            phase = "COMMIT"
        elif is_high_risk_base:
            # shorthand: base verb + pending_id means COMMIT
            phase = "COMMIT" if str(packet.get("pending_id", "")) else "PROPOSE"

        # Cooldown: block high-risk during stabilization window
        if base in self.HIGH_RISK and self._in_cooldown():
            self._log_local(packet, "REJECT_COOLDOWN", {"cooldown_until": float(self._cooldown_until)})
            return "REJECT"

        if base in self.HIGH_RISK and phase in ("PROPOSE", "COMMIT"):
            # Require nonce for any high-risk step
            if not nonce:
                self._log_local(packet, "REJECT_HIGH_RISK_NO_NONCE")
                return "REJECT"

            # PROPOSE: must have continuity (pi match) so pending cannot be created from a broken chain
            if phase == "PROPOSE":
                if not self._lock_ok():
                    self._log_local(packet, "REJECT_HIGH_RISK_PROPOSE_PI_FAIL")
                    return "REJECT"

                # DoS throttle: pending max
                if len(self._pending_ops) >= self._pending_max:
                    self._log_local(packet, "REJECT_PENDING_MAX", {"pending_max": int(self._pending_max)})
                    return "REJECT"

                # store pending
                pid = uuid.uuid4().hex
                payload = packet.get("payload", {})
                rec = {
                    "id": pid,
                    "kind": base,
                    "payload_hash": _payload_hash(payload),
                    "created_at": now,
                    "expires_at": now + float(self._pending_ttl_sec),
                    "pi_at_propose": actual_prev,
                }
                self._pending_ops[pid] = rec

                # mark nonce + evolve pi on accepted propose (protocol event)
                self._mark_nonce(nonce)
                self._lock["pi"] = _pi_next(actual_prev, {**packet, "verb": f"{base}_PROPOSE", "pending_id": pid})
                self._lock["lock_ok"] = True
                self._lock["fidelity"] = 1.0

                self._log_local(packet, "PENDING", {"pending_id": pid, "kind": base})
                return f"PENDING:{pid}"

            # COMMIT: must have exact continuity AND valid pending AND payload match
            pid = str(packet.get("pending_id", ""))
            rec = self._pending_ops.get(pid)
            if not rec:
                # Cliff #3: pending invalid / forged
                self._cliff()
                self._log_local(packet, "CLIFF_PENDING_INVALID", {"pending_id": pid})
                return "REJECT"

            if float(rec.get("expires_at", 0.0)) <= now:
                self._pending_ops.pop(pid, None)
                self._cliff()
                self._log_local(packet, "CLIFF_PENDING_EXPIRED", {"pending_id": pid})
                return "REJECT"

            # Cliff #2: high-risk COMMIT pi mismatch
            if not self._lock_ok():
                self._cliff()
                self._log_local(packet, "CLIFF_HIGH_RISK_COMMIT_PI_MISMATCH", {"pending_id": pid, "kind": base})
                return "REJECT"

            # Cliff #3: pending tamper / payload mismatch
            payload = packet.get("payload", {})
            if str(rec.get("payload_hash", "")) != _payload_hash(payload):
                self._cliff()
                self._log_local(packet, "CLIFF_PENDING_TAMPER", {"pending_id": pid, "kind": base})
                return "REJECT"

            # Execute base verb on core
            packet2 = dict(packet)
            packet2["verb"] = base  # translate COMMIT into actual base op
            # keep payload as is
            packet2.pop("pending_id", None)

            # mark nonce first (commit attempt consumes nonce)
            self._mark_nonce(nonce)

            res = super().apply_intent_packet(packet2)

            if res == "OK":
                # success: delete pending and advance pi
                self._pending_ops.pop(pid, None)
                self._lock["pi"] = _pi_next(actual_prev, {**packet, "verb": f"{base}_COMMIT", "pending_id": pid})
                self._lock["lock_ok"] = True
                self._lock["fidelity"] = 1.0
                self._log_local(packet, "OK", {"pending_id": pid, "kind": base})
                return "OK"

            # core rejected -> mark lock false (no partial commit)
            self._lock["lock_ok"] = False
            self._log_local(packet, "REJECT_CORE", {"pending_id": pid, "kind": base, "core_res": res})
            return "REJECT"

        # --- SAFE / general path (original semantics, but with strict pi gate) ---
        if self._lock_ok():
            # consume nonce if present
            if nonce:
                self._mark_nonce(nonce)

            # advance pi and call core
            self._lock["pi"] = _pi_next(actual_prev, packet)
            return super().apply_intent_packet(packet)

        # continuity failed -> reject (recovery handles this case explicitly)
        self._log_local(packet, "REJECT_CONTINUITY")
        return "REJECT"

    # --- Canonical gated ops ---

    def goal_evaluation(self) -> float:
        if not self._lock_ok():
            return self._undefined_num()
        try:
            base = float(self.objective_remaining())
        except Exception:
            base = self._undefined_num()
        return base + float(self.total_cost())

    def planning_tick(self) -> Dict[str, Any] | None:
        if not self._lock_ok():
            return self._undefined_obj()
        try:
            return self.tick()
        except Exception:
            return self._undefined_obj()

    # alias to match requires_ops name in specs
    def planning(self) -> Dict[str, Any] | None:
        return self.planning_tick()

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
        # legacy alias: core may not have anchor_restoration; keep safe
        if not self._lock_ok():
            return False
        try:
            r = self.anchor_restoration()
            return r == "RECOVERED"
        except Exception:
            return False


def _time_penalty(delta_t, cfg):
    if not cfg.get("enabled", False):
        return 0.0
    lam = float(cfg.get("lambda_delay", 1.0))
    nonlin = cfg.get("nonlinear", {"type": "linear"})
    if nonlin.get("type") == "exp":
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
