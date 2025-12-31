"""
AAOS Simulation (v1.0.4+)

Core:
- 4 states / 4 actions only (mirrors TLA)
- core actions unchanged

Extensions (B-closure, semantics-complete):
- objective_spec (typed)
- task_registry (required/completed + tag counts)
- EntropyProxy includes objective_remaining computed from objective_spec + task_registry
- tick() selects argmin of EntropyProxy with deterministic tie-break

Key sealing:
- EntropyProxy uses executor_policy.weights keys ONLY:
  - core, queue, objective_remaining, reject
(no aliases)

v1.0.4+ runtime fixes (simulation-only):
- intent_log.verb is schema-safe (enum only); raw verb preserved in payload["_raw_verb"] when needed
- tick counter is extensions.runtime_parameters["tick"] (monotone), independent from core time_cycle
- queue present => IDLE is not a candidate (prevents queue stall appearance)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Set, Tuple


# deterministic Decimal arithmetic context
getcontext().prec = 28

OWNER = "Lee_Yu_Cheol"
ROOT_ANCHOR_ID = "GENESIS_HEXAGON_V1"

CORE_ACTIONS = {
    "ExternalDisturbance",
    "ChangeClaimantInChaos",
    "AnchorRestoration",
    "TotalCollapse",
}

# Schema-safe intent verbs (must match AAOS_Schema.json $defs.IntentRecord.verb enum)
INTENT_VERBS = {
    "NOP",
    "NOTE_APPEND",
    "SET_OBJECTIVE",
    "SET_PARAMETER",
    "QUEUE_TASK",
    "QUEUE_CORE_ACTION",
    "EXPORT_STATE",
}


def _core_entropy_for_state(world_state: str) -> int:
    if world_state in {"Stable", "Recovered"}:
        return 0
    if world_state == "Chaos":
        return 100
    return 9999


def _d(x: Any) -> Decimal:
    """Deterministic Decimal conversion."""
    if isinstance(x, Decimal):
        return x
    if isinstance(x, bool):
        return Decimal(1) if x else Decimal(0)
    if isinstance(x, int):
        return Decimal(x)
    if isinstance(x, float):
        # str(float) is deterministic for a given float
        return Decimal(str(x))
    return Decimal(str(x))


def _uniq_preserve_order(items: Iterable[Any]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for x in items:
        sx = str(x)
        if sx not in seen:
            out.append(sx)
            seen.add(sx)
    return out


@dataclass(frozen=True)
class CoreSimResult:
    world_state: str
    anchor_connection: bool
    entropy: int
    claimant_id: str
    is_dead: bool
    result: str  # OK / NOOP / REJECT / RECOVERED / DEAD / STATE=DEAD


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
        "extensions",
    )

    def __init__(self, claimants: Optional[Iterable[str]] = None):
        object.__setattr__(self, "_sealed", False)

        # sealed core
        self.root_anchor_id = ROOT_ANCHOR_ID
        self.owner = OWNER
        self.anchor_count = 1

        base = {self.owner}
        if claimants is not None:
            base |= set(claimants)
        self.claimants: FrozenSet[str] = frozenset(base)

        # core state variables
        self.world_state = "Stable"    # Stable / Chaos / Recovered / DEAD
        self.anchor_connection = True  # True / False
        self.entropy = 0               # 0 / 100 / 9999 (mirrors world_state)
        self.time_cycle = 0            # Nat (core action only)
        self.claimant_id = self.owner
        self.is_dead = False

        # extensions: deterministic command plane + objective semantics
        self.extensions: Dict[str, Any] = {
            "protocol_refs": ["spec/Observer_Override_Protocol.md"],
            "nonce_registry": {"last_nonce": "", "seen": []},
            "intent_log": [],
            "command_queue": [],
            "effects_log": [],
            "runtime_objective": "",
            "objective_spec": {
                "type": "NONE",
                "required_task_ids": [],
                "required_tag": "",
                "required_tag_count": 0,
            },
            "task_registry": {
                "required": [],
                "completed": [],
                "completed_by_tag": {},
            },
            "runtime_parameters": {},  # will host monotone tick counter, overrides, etc.
            "executor_policy": {
                "selection_rule": "ENTROPY_ARGMIN_V2",
                "weights": {"core": 1.0, "queue": 10.0, "objective_remaining": 500.0, "reject": 500.0},
                "tie_break": ["EXECUTE_HEAD", "AUTORESOLVE_CHAOS", "IDLE"],
            },
            "notes": [],
        }

        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, key, value):
        if getattr(self, "_sealed", False) and key in {"root_anchor_id", "owner", "anchor_count", "claimants"}:
            raise AttributeError(f"sealed field: {key}")
        super().__setattr__(key, value)

    # ---------------- tick (extensions-only, monotone) ----------------
    def _now_tick(self) -> int:
        rp = self.extensions.get("runtime_parameters", {})
        if isinstance(rp, dict):
            try:
                return int(rp.get("tick", 0))
            except Exception:
                return 0
        return 0

    def _bump_tick(self) -> int:
        rp = self.extensions.get("runtime_parameters", {})
        if not isinstance(rp, dict):
            self.extensions["runtime_parameters"] = {}
            rp = self.extensions["runtime_parameters"]
        try:
            rp["tick"] = int(rp.get("tick", 0)) + 1
        except Exception:
            rp["tick"] = 1
        return int(rp["tick"])

    # ---------------- invariants (TypeOK-style) ----------------
    def _type_ok(self) -> bool:
        if self.anchor_count != 1:
            return False

        if self.world_state not in {"Stable", "Chaos", "Recovered", "DEAD"}:
            return False

        if self.anchor_connection not in {True, False}:
            return False

        # coupling: state <-> connection
        if self.world_state in {"Stable", "Recovered"} and self.anchor_connection is not True:
            return False
        if self.world_state in {"Chaos", "DEAD"} and self.anchor_connection is not False:
            return False

        if self.time_cycle < 0:
            return False

        if self.claimant_id not in self.claimants:
            return False

        # coupling: state <-> entropy
        if self.world_state in {"Stable", "Recovered"} and self.entropy != 0:
            return False
        if self.world_state == "Chaos" and self.entropy != 100:
            return False
        if self.world_state == "DEAD" and self.entropy != 9999:
            return False

        # recovered claimant invariant
        if self.world_state == "Recovered" and self.claimant_id != self.owner:
            return False

        ext = self.extensions
        must = [
            "protocol_refs",
            "nonce_registry",
            "intent_log",
            "command_queue",
            "effects_log",
            "runtime_objective",
            "objective_spec",
            "task_registry",
            "runtime_parameters",
            "executor_policy",
            "notes",
        ]
        if not isinstance(ext, dict):
            return False
        for k in must:
            if k not in ext:
                return False

        nr = ext["nonce_registry"]
        if not isinstance(nr, dict) or "last_nonce" not in nr or "seen" not in nr:
            return False

        tr = ext["task_registry"]
        if not isinstance(tr, dict) or "required" not in tr or "completed" not in tr or "completed_by_tag" not in tr:
            return False

        os_ = ext["objective_spec"]
        if not isinstance(os_, dict) or "type" not in os_:
            return False

        ep = ext["executor_policy"]
        if not isinstance(ep, dict):
            return False

        return True

    # ---------------- objective semantics ----------------
    def _objective_remaining(
        self,
        objective_spec: Dict[str, Any],
        completed: Set[str],
        completed_by_tag: Dict[str, int],
    ) -> int:
        otype = str(objective_spec.get("type", "NONE"))

        if otype == "NONE":
            return 0

        if otype == "TASK_SET_V1":
            req = objective_spec.get("required_task_ids", [])
            req_list = req if isinstance(req, list) else []
            req_set = {str(x) for x in req_list}
            return max(0, len(req_set - completed))

        if otype == "TAG_TARGET_V1":
            tag = str(objective_spec.get("required_tag", ""))
            need = int(objective_spec.get("required_tag_count", 0))
            have = int(completed_by_tag.get(tag, 0)) if tag != "" else 0
            return max(0, need - have)

        return 0

    def _sync_registry_from_objective(self) -> None:
        """
        Canonical linkage:
        - If objective_spec is TASK_SET_V1, copy required_task_ids into task_registry.required (unique, order-preserving).
        """
        ext = self.extensions
        os_ = ext.get("objective_spec", {})
        tr = ext.get("task_registry", {})
        if not isinstance(os_, dict) or not isinstance(tr, dict):
            return

        if str(os_.get("type", "NONE")) == "TASK_SET_V1":
            req = os_.get("required_task_ids", [])
            if isinstance(req, list):
                tr["required"] = _uniq_preserve_order(req)
            else:
                tr["required"] = []

    def _current_completed_sets(self) -> Tuple[Set[str], Dict[str, int]]:
        tr = self.extensions.get("task_registry", {})
        completed_list = tr.get("completed", []) if isinstance(tr, dict) else []
        completed = {str(x) for x in completed_list} if isinstance(completed_list, list) else set()

        cbt = tr.get("completed_by_tag", {}) if isinstance(tr, dict) else {}
        completed_by_tag: Dict[str, int] = {}
        if isinstance(cbt, dict):
            for k, v in cbt.items():
                try:
                    completed_by_tag[str(k)] = int(v)
                except Exception:
                    completed_by_tag[str(k)] = 0
        return completed, completed_by_tag

    # ---------------- OOP: intent packets -> deterministic logs + queue ----------------
    def apply_intent_packet(self, packet: Dict[str, Any]) -> str:
        if self.is_dead:
            return "STATE=DEAD"
        if not isinstance(packet, dict):
            return "REJECT"

        observer_id = packet.get("observer_id")
        nonce = str(packet.get("nonce", ""))
        signature = str(packet.get("signature", ""))

        if observer_id != self.owner:
            return "REJECT"
        if nonce == "":
            return "REJECT"

        nr = self.extensions["nonce_registry"]
        last = str(nr.get("last_nonce", ""))
        seen: List[str] = list(nr.get("seen", []))

        # deterministic monotone: strict lexical increase + no reuse
        if last != "" and not (nonce > last):
            return "REJECT"
        if nonce in seen:
            return "REJECT"

        intent = packet.get("intent", {})
        if not isinstance(intent, dict):
            return "REJECT"

        raw_verb = str(intent.get("verb", "NOP"))
        verb_for_log = raw_verb if raw_verb in INTENT_VERBS else "NOP"

        payload = intent.get("payload", {})
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            payload = {"value": payload}

        # preserve raw verb if it is outside schema enum
        if raw_verb not in INTENT_VERBS:
            payload = dict(payload)
            payload["_raw_verb"] = raw_verb

        rec = {
            "observer_id": self.owner,
            "nonce": nonce,
            "verb": verb_for_log,
            "payload": payload,
            "signature": signature,
            "t": self._now_tick(),
        }

        # commit nonce registry + log first (replayable)
        seen.append(nonce)
        nr["seen"] = seen
        nr["last_nonce"] = nonce
        self.extensions["intent_log"].append(rec)

        ext = self.extensions
        verb = raw_verb

        if verb == "NOP":
            pass

        elif verb == "NOTE_APPEND":
            text = payload.get("text", "")
            if text == "" and "value" in payload:
                text = str(payload["value"])
            ext["notes"].append(str(text))

        elif verb == "SET_OBJECTIVE":
            # human-readable objective mirror (optional)
            if "objective" in payload:
                ext["runtime_objective"] = str(payload.get("objective", ""))

            # semantic objective_spec (primary)
            spec = payload.get("objective_spec", payload.get("spec", None))
            if isinstance(spec, dict) and "type" in spec:
                otype = str(spec.get("type", "NONE"))
                os2: Dict[str, Any] = {"type": otype}

                if otype == "TASK_SET_V1":
                    req = spec.get("required_task_ids", [])
                    req_list = req if isinstance(req, list) else []
                    os2["required_task_ids"] = _uniq_preserve_order(req_list)
                    os2["required_tag"] = ""
                    os2["required_tag_count"] = 0

                elif otype == "TAG_TARGET_V1":
                    os2["required_task_ids"] = []
                    os2["required_tag"] = str(spec.get("required_tag", ""))
                    os2["required_tag_count"] = int(spec.get("required_tag_count", 0))

                else:
                    os2["required_task_ids"] = []
                    os2["required_tag"] = ""
                    os2["required_tag_count"] = 0

                ext["objective_spec"] = os2
                self._sync_registry_from_objective()

        elif verb == "SET_PARAMETER":
            if "key" in payload:
                k = str(payload.get("key"))
                ext["runtime_parameters"][k] = payload.get("value")
            elif "params" in payload and isinstance(payload["params"], dict):
                ext["runtime_parameters"].update(payload["params"])
            else:
                ext["runtime_parameters"].update(payload)

        elif verb == "QUEUE_TASK":
            # TASK payload MUST include task_id; if missing, deterministically derive from nonce
            task_id = str(payload.get("task_id", ""))
            tag = str(payload.get("tag", ""))
            params = payload.get("params", {})
            if not isinstance(params, dict):
                params = {"value": params}

            if task_id == "":
                task_id = f"task_from_nonce:{nonce}"

            env = {
                "kind": "TASK",
                "nonce": nonce,
                "t": self._now_tick(),
                "payload": {"task_id": task_id, "tag": tag, "params": params},
            }
            ext["command_queue"].append(env)

            # optional: if objective is TASK_SET_V1, allow queueing to also declare requirement (unique)
            os_ = ext.get("objective_spec", {})
            tr = ext.get("task_registry", {})
            if isinstance(os_, dict) and str(os_.get("type", "NONE")) == "TASK_SET_V1" and isinstance(tr, dict):
                req = list(tr.get("required", []))
                if task_id not in req:
                    req.append(task_id)
                    tr["required"] = req
                os_req = list(os_.get("required_task_ids", [])) if isinstance(os_.get("required_task_ids", []), list) else []
                if task_id not in os_req:
                    os_req.append(task_id)
                    os_["required_task_ids"] = os_req

        elif verb == "QUEUE_CORE_ACTION":
            action = str(payload.get("action", ""))
            args = payload.get("args", {})
            if action not in CORE_ACTIONS:
                ext["command_queue"].append(
                    {
                        "kind": "TASK",
                        "nonce": nonce,
                        "t": self._now_tick(),
                        "payload": {
                            "task_id": f"UNKNOWN_CORE_ACTION:{action}",
                            "tag": "system",
                            "params": {"action": action, "args": args},
                        },
                    }
                )
            else:
                ext["command_queue"].append(
                    {
                        "kind": "CORE_ACTION",
                        "nonce": nonce,
                        "t": self._now_tick(),
                        "payload": {"action": action, "args": args if isinstance(args, dict) else {}},
                    }
                )

        elif verb == "EXPORT_STATE":
            ext["notes"].append(self.status(include_extensions=True))

        else:
            # Unknown verb projected as TASK envelope
            ext["command_queue"].append(
                {
                    "kind": "TASK",
                    "nonce": nonce,
                    "t": self._now_tick(),
                    "payload": {
                        "task_id": f"UNKNOWN_VERB:{verb}",
                        "tag": "system",
                        "params": {"verb": verb, "payload": payload},
                    },
                }
            )

        return "OK" if self._type_ok() else "DIVERGENCE"

    # ---------------- 4 canonical actions (core only) ----------------
    def external_disturbance(self) -> str:
        if self.is_dead:
            return "STATE=DEAD"
        if not (self.world_state == "Stable" and self.anchor_connection is True):
            return "NOOP"
        self.anchor_connection = False
        self.world_state = "Chaos"
        self.entropy = 100
        self.time_cycle += 1
        return "OK" if self._type_ok() else "DIVERGENCE"

    def change_claimant_in_chaos(self, claimant_id: str) -> str:
        if self.is_dead:
            return "STATE=DEAD"
        if not (self.world_state == "Chaos" and self.anchor_connection is False):
            return "NOOP"
        if claimant_id not in self.claimants:
            return "REJECT"

        # swap-only
        if claimant_id == self.claimant_id:
            return "NOOP"

        # non-reentry (same as TLA patch)
        if self.claimant_id != self.owner and claimant_id == self.owner:
            return "REJECT"

        self.claimant_id = claimant_id
        self.time_cycle += 1
        return "OK" if self._type_ok() else "DIVERGENCE"

    def anchor_restoration(self) -> str:
        if self.is_dead:
            return "STATE=DEAD"
        if not (self.world_state == "Chaos" and self.anchor_connection is False):
            return "NOOP"
        if self.claimant_id != self.owner:
            return "REJECT"
        self.anchor_connection = True
        self.world_state = "Recovered"
        self.entropy = 0
        self.time_cycle += 1
        return "RECOVERED" if self._type_ok() else "DIVERGENCE"

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
        self.entropy = 9999
        self.time_cycle += 1
        return "DEAD" if self._type_ok() else "DIVERGENCE"

    # ---------------- EntropyProxy (V2, key-sealed) ----------------
    def _policy_weights(self) -> Dict[str, Decimal]:
        ep = self.extensions.get("executor_policy", {})
        w_raw = dict(ep.get("weights", {}))

        # runtime override (optional): runtime_parameters.policy_weights
        rp = self.extensions.get("runtime_parameters", {})
        pw = rp.get("policy_weights")
        if isinstance(pw, dict):
            for k in ["core", "queue", "objective_remaining", "reject"]:
                if k in pw:
                    w_raw[k] = pw[k]

        return {
            "core": _d(w_raw.get("core", 1.0)),
            "queue": _d(w_raw.get("queue", 10.0)),
            "objective_remaining": _d(w_raw.get("objective_remaining", 500.0)),
            "reject": _d(w_raw.get("reject", 500.0)),
        }

    def _tie_break_order(self) -> List[str]:
        ep = self.extensions.get("executor_policy", {})
        tb = ep.get("tie_break", ["EXECUTE_HEAD", "AUTORESOLVE_CHAOS", "IDLE"])
        if isinstance(tb, list) and len(tb) == 3:
            return [str(x) for x in tb]
        return ["EXECUTE_HEAD", "AUTORESOLVE_CHAOS", "IDLE"]

    def _simulate_core_action(self, action: str, args: Dict[str, Any]) -> CoreSimResult:
        ws = self.world_state
        conn = self.anchor_connection
        ent = self.entropy
        claimant = self.claimant_id
        dead = self.is_dead

        if dead:
            return CoreSimResult(ws, conn, ent, claimant, dead, "STATE=DEAD")

        if action == "ExternalDisturbance":
            if ws == "Stable" and conn is True:
                return CoreSimResult("Chaos", False, 100, claimant, dead, "OK")
            return CoreSimResult(ws, conn, ent, claimant, dead, "NOOP")

        if action == "ChangeClaimantInChaos":
            if not (ws == "Chaos" and conn is False):
                return CoreSimResult(ws, conn, ent, claimant, dead, "NOOP")
            cid = str(args.get("claimant_id", "")) if isinstance(args, dict) else ""
            if cid not in self.claimants:
                return CoreSimResult(ws, conn, ent, claimant, dead, "REJECT")
            if cid == claimant:
                return CoreSimResult(ws, conn, ent, claimant, dead, "NOOP")
            if claimant != self.owner and cid == self.owner:
                return CoreSimResult(ws, conn, ent, claimant, dead, "REJECT")
            return CoreSimResult(ws, conn, ent, cid, dead, "OK")

        if action == "AnchorRestoration":
            if not (ws == "Chaos" and conn is False):
                return CoreSimResult(ws, conn, ent, claimant, dead, "NOOP")
            if claimant != self.owner:
                return CoreSimResult(ws, conn, ent, claimant, dead, "REJECT")
            return CoreSimResult("Recovered", True, 0, claimant, dead, "RECOVERED")

        if action == "TotalCollapse":
            if not (ws == "Chaos" and conn is False):
                return CoreSimResult(ws, conn, ent, claimant, dead, "NOOP")
            if claimant == self.owner:
                return CoreSimResult(ws, conn, ent, claimant, dead, "REJECT")
            return CoreSimResult("DEAD", False, 9999, claimant, True, "DEAD")

        return CoreSimResult(ws, conn, ent, claimant, dead, "REJECT")

    def _entropy_proxy(self, core_entropy_after: int, queue_len_after: int, objective_remaining_after: int, status: str) -> Decimal:
        w = self._policy_weights()
        reject_term = Decimal(1) if status == "REJECT" else Decimal(0)
        return (
            w["core"] * _d(core_entropy_after)
            + w["queue"] * _d(queue_len_after)
            + w["objective_remaining"] * _d(objective_remaining_after)
            + w["reject"] * reject_term
        )

    # ---------------- candidate simulation (1-step lookahead) ----------------
    def _simulate_execute_head(self) -> Dict[str, Any]:
        q = self.extensions["command_queue"]
        env = q[0]
        kind = str(env.get("kind", "TASK"))
        payload = env.get("payload", {})
        queue_len_after = max(0, len(q) - 1)

        completed, cbt = self._current_completed_sets()
        os_ = self.extensions.get("objective_spec", {})
        osd = os_ if isinstance(os_, dict) else {}

        # NOTE
        if kind == "NOTE":
            obj_rem = self._objective_remaining(osd, completed, cbt)
            return {
                "type": "EXECUTE_HEAD",
                "kind": "NOTE",
                "status": "OK",
                "core_entropy_after": _core_entropy_for_state(self.world_state),
                "queue_len_after": queue_len_after,
                "objective_remaining_after": obj_rem,
                "detail": {"kind": "NOTE"},
            }

        # TASK
        if kind == "TASK":
            if not isinstance(payload, dict):
                obj_rem = self._objective_remaining(osd, completed, cbt)
                return {
                    "type": "EXECUTE_HEAD",
                    "kind": "TASK",
                    "status": "REJECT",
                    "core_entropy_after": _core_entropy_for_state(self.world_state),
                    "queue_len_after": queue_len_after,
                    "objective_remaining_after": obj_rem,
                    "detail": {"reason": "payload_not_object"},
                }

            task_id = str(payload.get("task_id", ""))
            tag = str(payload.get("tag", ""))

            if task_id == "":
                obj_rem = self._objective_remaining(osd, completed, cbt)
                return {
                    "type": "EXECUTE_HEAD",
                    "kind": "TASK",
                    "status": "REJECT",
                    "core_entropy_after": _core_entropy_for_state(self.world_state),
                    "queue_len_after": queue_len_after,
                    "objective_remaining_after": obj_rem,
                    "detail": {"reason": "missing_task_id"},
                }

            completed2 = set(completed)
            completed2.add(task_id)

            cbt2 = dict(cbt)
            if tag != "":
                cbt2[tag] = int(cbt2.get(tag, 0)) + 1

            obj_rem2 = self._objective_remaining(osd, completed2, cbt2)

            return {
                "type": "EXECUTE_HEAD",
                "kind": "TASK",
                "status": "OK",
                "core_entropy_after": _core_entropy_for_state(self.world_state),
                "queue_len_after": queue_len_after,
                "objective_remaining_after": obj_rem2,
                "detail": {"task_id": task_id, "tag": tag},
            }

        # CORE_ACTION
        if kind == "CORE_ACTION":
            if not isinstance(payload, dict):
                obj_rem = self._objective_remaining(osd, completed, cbt)
                return {
                    "type": "EXECUTE_HEAD",
                    "kind": "CORE_ACTION",
                    "status": "REJECT",
                    "core_entropy_after": _core_entropy_for_state(self.world_state),
                    "queue_len_after": queue_len_after,
                    "objective_remaining_after": obj_rem,
                    "detail": {"reason": "payload_not_object"},
                }

            action = str(payload.get("action", ""))
            args = payload.get("args", {})
            if action not in CORE_ACTIONS:
                obj_rem = self._objective_remaining(osd, completed, cbt)
                return {
                    "type": "EXECUTE_HEAD",
                    "kind": "CORE_ACTION",
                    "status": "REJECT",
                    "core_entropy_after": _core_entropy_for_state(self.world_state),
                    "queue_len_after": queue_len_after,
                    "objective_remaining_after": obj_rem,
                    "detail": {"reason": "unknown_action", "action": action},
                }

            sim = self._simulate_core_action(action, args if isinstance(args, dict) else {})
            status = "OK" if sim.result in {"OK", "RECOVERED", "DEAD"} else ("NOOP" if sim.result == "NOOP" else "REJECT")
            obj_rem = self._objective_remaining(osd, completed, cbt)

            return {
                "type": "EXECUTE_HEAD",
                "kind": "CORE_ACTION",
                "status": status,
                "core_entropy_after": int(sim.entropy),
                "queue_len_after": queue_len_after,
                "objective_remaining_after": obj_rem,
                "detail": {
                    "action": action,
                    "result": sim.result,
                    "core_after": {
                        "STATE": sim.world_state,
                        "anchor_connection": sim.anchor_connection,
                        "entropy": sim.entropy,
                        "claimant": sim.claimant_id,
                        "is_dead": sim.is_dead,
                    },
                },
            }

        # unknown kind
        obj_rem = self._objective_remaining(osd, completed, cbt)
        return {
            "type": "EXECUTE_HEAD",
            "kind": kind,
            "status": "REJECT",
            "core_entropy_after": _core_entropy_for_state(self.world_state),
            "queue_len_after": queue_len_after,
            "objective_remaining_after": obj_rem,
            "detail": {"reason": "unknown_kind", "kind": kind},
        }

    def _simulate_autoresolve_chaos(self) -> Dict[str, Any]:
        completed, cbt = self._current_completed_sets()
        os_ = self.extensions.get("objective_spec", {})
        osd = os_ if isinstance(os_, dict) else {}
        obj_rem = self._objective_remaining(osd, completed, cbt)
        qlen = len(self.extensions["command_queue"])

        # selector guarantees chaos/disconnected when this candidate is included
        if self.claimant_id == self.owner:
            sim = self._simulate_core_action("AnchorRestoration", {})
            status = "OK" if sim.result == "RECOVERED" else ("NOOP" if sim.result == "NOOP" else "REJECT")
            return {
                "type": "AUTORESOLVE_CHAOS",
                "kind": "CORE_ACTION",
                "status": status,
                "core_entropy_after": int(sim.entropy),
                "queue_len_after": qlen,
                "objective_remaining_after": obj_rem,
                "detail": {"action": "AnchorRestoration", "result": sim.result, "core_after": self.core_snapshot()},
            }

        sim = self._simulate_core_action("TotalCollapse", {})
        status = "OK" if sim.result == "DEAD" else ("NOOP" if sim.result == "NOOP" else "REJECT")
        return {
            "type": "AUTORESOLVE_CHAOS",
            "kind": "CORE_ACTION",
            "status": status,
            "core_entropy_after": int(sim.entropy),
            "queue_len_after": qlen,
            "objective_remaining_after": obj_rem,
            "detail": {"action": "TotalCollapse", "result": sim.result, "core_after": self.core_snapshot()},
        }

    def _simulate_idle(self) -> Dict[str, Any]:
        completed, cbt = self._current_completed_sets()
        os_ = self.extensions.get("objective_spec", {})
        osd = os_ if isinstance(os_, dict) else {}
        obj_rem = self._objective_remaining(osd, completed, cbt)

        return {
            "type": "IDLE",
            "kind": "NOTE",
            "status": "NOOP",
            "core_entropy_after": _core_entropy_for_state(self.world_state),
            "queue_len_after": len(self.extensions["command_queue"]),
            "objective_remaining_after": obj_rem,
            "detail": {},
        }

    def _select_candidate(self, autoresolve_chaos: bool) -> Dict[str, Any]:
        cands: List[Dict[str, Any]] = []

        in_chaos = (self.world_state == "Chaos" and self.anchor_connection is False)

        # Queue present => do not include IDLE
        if self.extensions["command_queue"]:
            cands.append(self._simulate_execute_head())
            if autoresolve_chaos and in_chaos:
                cands.append(self._simulate_autoresolve_chaos())
        else:
            if autoresolve_chaos and in_chaos:
                cands.append(self._simulate_autoresolve_chaos())
            cands.append(self._simulate_idle())

        for c in cands:
            c["proxy"] = self._entropy_proxy(
                core_entropy_after=int(c["core_entropy_after"]),
                queue_len_after=int(c["queue_len_after"]),
                objective_remaining_after=int(c["objective_remaining_after"]),
                status=str(c["status"]),
            )

        min_proxy = min(c["proxy"] for c in cands)
        tied = [c for c in cands if c["proxy"] == min_proxy]

        if len(tied) == 1:
            return tied[0]

        order = self._tie_break_order()
        rank = {name: i for i, name in enumerate(order)}
        tied.sort(key=lambda c: rank.get(str(c["type"]), 9999))
        return tied[0]

    # ---------------- executor tick (EntropyProxy argmin V2) ----------------
    def tick(self, autoresolve_chaos: bool = True) -> Dict[str, Any]:
        ext = self.extensions
        t = self._bump_tick()  # monotone tick for effects_log

        if self.is_dead:
            eff = {"nonce": "", "t": t, "kind": "NOTE", "status": "NOOP", "detail": {"selected": "DEAD"}}
            ext["effects_log"].append(eff)
            return eff

        choice = self._select_candidate(autoresolve_chaos=autoresolve_chaos)
        proxy_str = str(choice["proxy"])

        # execute chosen candidate
        if choice["type"] == "EXECUTE_HEAD":
            env = ext["command_queue"].pop(0)
            kind = str(env.get("kind", "TASK"))
            nonce = str(env.get("nonce", ""))
            payload = env.get("payload", {})

            eff = {
                "nonce": nonce,
                "t": t,
                "kind": kind,
                "status": "NOOP",
                "detail": {"proxy": proxy_str, "selected": "EXECUTE_HEAD"},
            }

            if kind == "NOTE":
                text = str(payload.get("text", "")) if isinstance(payload, dict) else ""
                ext["notes"].append(text)
                eff["status"] = "OK"
                eff["detail"].update({"text": text})

            elif kind == "TASK":
                if not isinstance(payload, dict):
                    eff["status"] = "REJECT"
                    eff["detail"].update({"reason": "payload_not_object"})
                else:
                    task_id = str(payload.get("task_id", ""))
                    tag = str(payload.get("tag", ""))
                    if task_id == "":
                        eff["status"] = "REJECT"
                        eff["detail"].update({"reason": "missing_task_id"})
                    else:
                        tr = ext["task_registry"]
                        comp = list(tr.get("completed", []))
                        if task_id not in comp:
                            comp.append(task_id)
                        tr["completed"] = comp

                        if tag != "":
                            cbt = dict(tr.get("completed_by_tag", {}))
                            cbt[tag] = int(cbt.get(tag, 0)) + 1
                            tr["completed_by_tag"] = cbt

                        eff["status"] = "OK"
                        eff["detail"].update({"task_id": task_id, "tag": tag, "objective_remaining": self.objective_remaining()})

            elif kind == "CORE_ACTION":
                if not isinstance(payload, dict):
                    eff["status"] = "REJECT"
                    eff["detail"].update({"reason": "payload_not_object"})
                else:
                    action = str(payload.get("action", ""))
                    args = payload.get("args", {})
                    if action not in CORE_ACTIONS:
                        eff["status"] = "REJECT"
                        eff["detail"].update({"reason": "unknown_action", "action": action})
                    else:
                        if action == "ExternalDisturbance":
                            r = self.external_disturbance()
                        elif action == "ChangeClaimantInChaos":
                            cid = str(args.get("claimant_id", "")) if isinstance(args, dict) else ""
                            r = self.change_claimant_in_chaos(cid)
                        elif action == "AnchorRestoration":
                            r = self.anchor_restoration()
                        else:
                            r = self.total_collapse()

                        eff["status"] = "OK" if r in {"OK", "RECOVERED", "DEAD"} else ("NOOP" if r == "NOOP" else "REJECT")
                        eff["detail"].update({"action": action, "result": r, "core": self.core_snapshot()})

            else:
                eff["status"] = "REJECT"
                eff["detail"].update({"reason": "unknown_kind", "kind": kind})

            ext["effects_log"].append(eff)
            return eff

        if choice["type"] == "AUTORESOLVE_CHAOS":
            if self.claimant_id == self.owner:
                r = self.anchor_restoration()
                eff = {
                    "nonce": "",
                    "t": t,
                    "kind": "CORE_ACTION",
                    "status": "OK" if r == "RECOVERED" else ("NOOP" if r == "NOOP" else "REJECT"),
                    "detail": {"proxy": proxy_str, "selected": "AUTORESOLVE_CHAOS", "action": "AnchorRestoration", "result": r, "core": self.core_snapshot()},
                }
            else:
                r = self.total_collapse()
                eff = {
                    "nonce": "",
                    "t": t,
                    "kind": "CORE_ACTION",
                    "status": "OK" if r == "DEAD" else ("NOOP" if r == "NOOP" else "REJECT"),
                    "detail": {"proxy": proxy_str, "selected": "AUTORESOLVE_CHAOS", "action": "TotalCollapse", "result": r, "core": self.core_snapshot()},
                }

            ext["effects_log"].append(eff)
            return eff

        # IDLE
        eff = {
            "nonce": "",
            "t": t,
            "kind": "NOTE",
            "status": "NOOP",
            "detail": {"proxy": proxy_str, "selected": "IDLE", "objective_remaining": self.objective_remaining()},
        }
        ext["effects_log"].append(eff)
        return eff

    # ---------------- helpers ----------------
    def objective_remaining(self) -> int:
        os_ = self.extensions.get("objective_spec", {})
        completed, cbt = self._current_completed_sets()
        return self._objective_remaining(os_ if isinstance(os_, dict) else {}, completed, cbt)

    def core_snapshot(self) -> Dict[str, Any]:
        return {
            "root": self.root_anchor_id,
            "Anchor_Count": self.anchor_count,
            "STATE": self.world_state,
            "anchor_connection": self.anchor_connection,
            "claimant": self.claimant_id,
            "entropy": self.entropy,
            "t": self.time_cycle,
        }

    def status(self, include_extensions: bool = False) -> str:
        core = (
            f"root={self.root_anchor_id} | "
            f"Anchor_Count={self.anchor_count} | "
            f"STATE={self.world_state} | "
            f"anchor_connection={self.anchor_connection} | "
            f"claimant={self.claimant_id} | "
            f"entropy={self.entropy} | "
            f"t={self.time_cycle}"
        )
        if not include_extensions:
            return core
        ext = self.extensions
        return (
            core
            + " || "
            + f"objective={ext.get('runtime_objective','')} | "
            + f"objective_type={ext.get('objective_spec',{}).get('type','')} | "
            + f"objective_remaining={self.objective_remaining()} | "
            + f"queue={len(ext.get('command_queue',[]))} | "
            + f"effects={len(ext.get('effects_log',[]))} | "
            + f"notes={len(ext.get('notes',[]))} | "
            + f"tick={self._now_tick()}"
        )


if __name__ == "__main__":
    allowed = {"Lee_Yu_Cheol", "Imposter_AI_001"}
    sim = AnchorSystem(claimants=allowed)

    print("[t=0]", sim.status(include_extensions=True))

    # 1) set objective_spec: TASK_SET_V1
    ip_obj = {
        "observer_id": "Lee_Yu_Cheol",
        "nonce": "2025-12-31T22:00:00+09:00#000001",
        "intent": {
            "verb": "SET_OBJECTIVE",
            "payload": {
                "objective": "complete tasks T1,T2",
                "objective_spec": {"type": "TASK_SET_V1", "required_task_ids": ["T1", "T2", "T1"]},
            },
        },
        "signature": "",
    }
    print("[IP_OBJ]", sim.apply_intent_packet(ip_obj), sim.status(include_extensions=True))

    # 2) queue tasks
    ip_t1 = {
        "observer_id": "Lee_Yu_Cheol",
        "nonce": "2025-12-31T22:00:00+09:00#000002",
        "intent": {"verb": "QUEUE_TASK", "payload": {"task_id": "T1", "tag": "work", "params": {"x": 1}}},
        "signature": "",
    }
    ip_t2 = {
        "observer_id": "Lee_Yu_Cheol",
        "nonce": "2025-12-31T22:00:00+09:00#000003",
        "intent": {"verb": "QUEUE_TASK", "payload": {"task_id": "T2", "tag": "work", "params": {"y": 2}}},
        "signature": "",
    }
    print("[IP_T1]", sim.apply_intent_packet(ip_t1), sim.status(include_extensions=True))
    print("[IP_T2]", sim.apply_intent_packet(ip_t2), sim.status(include_extensions=True))

    # 3) ticks
    print("[tick1]", sim.tick(), sim.status(include_extensions=True))
    print("[tick2]", sim.tick(), sim.status(include_extensions=True))
    print("[tick3]", sim.tick(), sim.status(include_extensions=True))
