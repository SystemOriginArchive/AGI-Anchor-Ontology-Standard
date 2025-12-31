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

Command plane (OOP):
- Observer Intent Packets mutate ONLY extensions.*
- Core state transitions remain the 4 actions above.
"""

from __future__ import annotations
from typing import Any, Dict, FrozenSet, Iterable, Optional


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
        self.root_anchor_id = "GENESIS_HEXAGON_V1"
        self.owner = "Lee_Yu_Cheol"
        self.anchor_count = 1

        base = {self.owner}
        if claimants is not None:
            base |= set(claimants)
        self.claimants: FrozenSet[str] = frozenset(base)

        # core state variables
        self.world_state = "Stable"         # Stable / Chaos / Recovered / DEAD
        self.anchor_connection = True       # True / False
        self.entropy = 0.0                  # 0.0 / 100.0 / 9999.0
        self.time_cycle = 0                 # Nat
        self.claimant_id = self.owner       # must be in claimants
        self.is_dead = False

        # command plane (extensions.*)
        self.extensions: Dict[str, Any] = {
            "protocol_refs": ["spec/Observer_Override_Protocol.md"],
            "intent_log": [],
            "command_queue": [],
            "runtime_objective": "",
            "runtime_parameters": {},
            "notes": [],
        }

        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, key, value):
        if getattr(self, "_sealed", False) and key in {"root_anchor_id", "owner", "anchor_count", "claimants"}:
            raise AttributeError(f"sealed field: {key}")
        super().__setattr__(key, value)

    def _type_ok(self) -> bool:
        if self.anchor_count != 1:
            return False

        if self.world_state not in {"Stable", "Chaos", "Recovered", "DEAD"}:
            return False

        if self.anchor_connection not in {True, False}:
            return False
        if self.world_state in {"Stable", "Recovered"} and self.anchor_connection is not True:
            return False
        if self.world_state in {"Chaos", "DEAD"} and self.anchor_connection is not False:
            return False

        if self.time_cycle < 0:
            return False

        if self.claimant_id not in self.claimants:
            return False

        if self.world_state in {"Stable", "Recovered"} and self.entropy != 0.0:
            return False
        if self.world_state == "Chaos" and self.entropy != 100.0:
            return False
        if self.world_state == "DEAD" and self.entropy != 9999.0:
            return False

        if self.world_state == "Recovered" and self.claimant_id != self.owner:
            return False

        ext = self.extensions
        if not isinstance(ext, dict):
            return False
        for k in ["protocol_refs", "intent_log", "command_queue", "runtime_objective", "runtime_parameters", "notes"]:
            if k not in ext:
                return False

        return True

    # -------- OOP hook: extensions-only mutation --------
    def apply_intent_packet(self, packet: Dict[str, Any]) -> str:
        if self.is_dead:
            return "STATE=DEAD"

        if not isinstance(packet, dict):
            return "REJECT"

        observer_id = packet.get("observer_id")
        if observer_id != self.owner:
            return "REJECT"

        intent = packet.get("intent", {})
        if not isinstance(intent, dict):
            return "REJECT"

        verb = intent.get("verb", "NOTE_APPEND")
        payload = intent.get("payload", {})
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            payload = {"value": payload}

        normalized = {
            "observer_id": self.owner,
            "nonce": packet.get("nonce", ""),
            "verb": verb,
            "payload": payload,
            "signature": packet.get("signature", ""),
            "t": self.time_cycle,
        }

        ext = self.extensions
        ext["intent_log"].append(normalized)

        if verb == "NOP":
            pass

        elif verb == "NOTE_APPEND":
            text = payload.get("text", "")
            if text == "" and "value" in payload:
                text = str(payload["value"])
            ext["notes"].append(str(text))

        elif verb == "SET_OBJECTIVE":
            ext["runtime_objective"] = str(payload.get("objective", ""))

        elif verb == "SET_PARAMETER":
            if "key" in payload:
                k = str(payload.get("key"))
                ext["runtime_parameters"][k] = payload.get("value")
            elif "params" in payload and isinstance(payload["params"], dict):
                ext["runtime_parameters"].update(payload["params"])
            else:
                ext["runtime_parameters"].update(payload)

        elif verb == "QUEUE_TASK":
            ext["command_queue"].append(payload)

        elif verb == "EXPORT_STATE":
            ext["notes"].append(self.status(include_extensions=True))

        else:
            ext["command_queue"].append({"verb": verb, "payload": payload})

        return "OK" if self._type_ok() else "DIVERGENCE"

    # -------- 4 canonical actions (core unchanged) --------
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

    def change_claimant_in_chaos(self, claimant_id: str) -> str:
        if self.is_dead:
            return "STATE=DEAD"
        if not (self.world_state == "Chaos" and self.anchor_connection is False):
            return "NOOP"
        if claimant_id not in self.claimants:
            return "REJECT"
        if claimant_id == self.claimant_id:
            return "NOOP"
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
        self.entropy = 0.0
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
        self.entropy = 9999.0
        self.time_cycle += 1
        return "DEAD" if self._type_ok() else "DIVERGENCE"

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
            + f"queue={len(ext.get('command_queue',[]))} | "
            + f"notes={len(ext.get('notes',[]))}"
        )


if __name__ == "__main__":
    allowed = {"Lee_Yu_Cheol", "Imposter_AI_001"}
    sim = AnchorSystem(claimants=allowed)

    print("[t=0]", sim.status(include_extensions=True))

    ip = {
        "observer_id": "Lee_Yu_Cheol",
        "nonce": "2025-12-31T08:00:00+09:00#000001",
        "intent": {"verb": "SET_OBJECTIVE", "payload": {"objective": "do X now"}},
        "signature": ""
    }
    print("[IP]", sim.apply_intent_packet(ip), sim.status(include_extensions=True))

    print("[A]", sim.external_disturbance(), sim.status(include_extensions=True))
    print("[B]", sim.change_claimant_in_chaos("Imposter_AI_001"), sim.status(include_extensions=True))
    print("[D]", sim.total_collapse(), sim.status(include_extensions=True))
