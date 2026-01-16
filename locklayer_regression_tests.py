from __future__ import annotations

import time
from typing import Any, Dict, Tuple

from simulation.anchor_simulation_locklayer import AnchorSystemLocked


def _mk_sys(*, cooldown_sec: int = 2) -> AnchorSystemLocked:
    """
    Create a system with short cooldown so the test suite finishes quickly.
    """
    sys = AnchorSystemLocked(
        claimants=["AAOS_CREATOR_ANCHOR_001_LEE_YU_CHEOL"],
        recovery_cooldown_sec=cooldown_sec,
    )
    # core owner is set by v1.0.4 core; keep it explicit in tests
    assert getattr(sys, "owner", ""), "core owner must exist"
    return sys


def _base_packet(sys: AnchorSystemLocked, *, nonce: str, pi_prev: str, source: str | None = None) -> Dict[str, Any]:
    return {
        "observer_id": sys.owner,  # external value; core observer_id will be sealed anyway
        "nonce": nonce,
        "source": source or sys.owner,
        "pi_prev": pi_prev,
    }


def _queue_task_payload() -> Dict[str, Any]:
    # v1.0.4 core requires task_id for QUEUE_TASK
    return {
        "task_id": "T_PING",
        "tag": "work",
        "params": {"msg": "PING"},
    }


def _get_core_queue_len(sys: AnchorSystemLocked) -> int:
    ex = getattr(sys, "extensions", None)
    if isinstance(ex, dict):
        q = ex.get("command_queue")
        if isinstance(q, list):
            return len(q)
    # fallback if core uses attribute
    q2 = getattr(sys, "command_queue", None)
    if isinstance(q2, list):
        return len(q2)
    return 0


def _get_runtime_parameters(sys: AnchorSystemLocked) -> Dict[str, Any]:
    ex = getattr(sys, "extensions", None)
    if isinstance(ex, dict):
        rp = ex.get("runtime_parameters")
        if isinstance(rp, dict):
            return rp
    return {}


def test_01_safe_queue_task_core_effect() -> None:
    sys = _mk_sys()
    pi0 = sys.lock_state()["pi"]
    q0 = _get_core_queue_len(sys)

    p = _base_packet(sys, nonce="EXT#1", pi_prev=pi0)
    p.update({"verb": "QUEUE_TASK", "payload": _queue_task_payload()})

    r = sys.apply_intent_packet(p)
    assert r == "OK", f"expected OK, got {r}"

    q1 = _get_core_queue_len(sys)
    assert q1 == q0 + 1, f"queue length should increase by 1 ({q0} -> {q1})"


def test_02_high_risk_set_parameter_2step_updates_core() -> None:
    sys = _mk_sys()
    # 1) PROPOSE
    p1 = _base_packet(sys, nonce="EXT#2", pi_prev=sys.lock_state()["pi"])
    p1.update({
        "verb": "SET_PARAMETER",
        "payload": {"key": "alpha", "value": 0.123},
    })
    r1 = sys.apply_intent_packet(p1)
    assert r1.startswith("PENDING:"), f"expected PENDING:<id>, got {r1}"
    pid = r1.split(":", 1)[1]

    # 2) COMMIT
    p2 = _base_packet(sys, nonce="EXT#3", pi_prev=sys.lock_state()["pi"])
    p2.update({
        "verb": "SET_PARAMETER",
        "pending_id": pid,
        "payload": {"key": "alpha", "value": 0.123},
    })
    r2 = sys.apply_intent_packet(p2)
    assert r2 == "OK", f"expected OK, got {r2}"

    rp = _get_runtime_parameters(sys)
    assert rp.get("alpha") == 0.123, f"runtime_parameters.alpha should be 0.123, got {rp.get('alpha')}"


def test_03_nonce_replay_is_rejected() -> None:
    sys = _mk_sys()
    pi0 = sys.lock_state()["pi"]

    p = _base_packet(sys, nonce="EXT#REPLAY", pi_prev=pi0)
    p.update({"verb": "QUEUE_TASK", "payload": _queue_task_payload()})

    r1 = sys.apply_intent_packet(p)
    assert r1 == "OK", f"first use should be OK, got {r1}"

    # replay same nonce
    p_replay = _base_packet(sys, nonce="EXT#REPLAY", pi_prev=sys.lock_state()["pi"])
    p_replay.update({"verb": "QUEUE_TASK", "payload": _queue_task_payload()})
    r2 = sys.apply_intent_packet(p_replay)
    assert r2 == "REJECT", f"nonce replay should be REJECT, got {r2}"


def test_04_pending_tamper_payload_mismatch_cliff() -> None:
    sys = _mk_sys()

    # PROPOSE objective
    p1 = _base_packet(sys, nonce="EXT#4", pi_prev=sys.lock_state()["pi"])
    p1.update({
        "verb": "SET_OBJECTIVE",
        "payload": {"objective": "MINIMIZE_TOTAL_COST"},
    })
    r1 = sys.apply_intent_packet(p1)
    assert r1.startswith("PENDING:"), f"expected PENDING:<id>, got {r1}"
    pid = r1.split(":", 1)[1]

    # COMMIT with tampered payload (should REJECT and cliff)
    p2 = _base_packet(sys, nonce="EXT#5", pi_prev=sys.lock_state()["pi"])
    p2.update({
        "verb": "SET_OBJECTIVE",
        "pending_id": pid,
        "payload": {"objective": "MAXIMIZE_TOTAL_COST"},  # tamper
    })
    r2 = sys.apply_intent_packet(p2)
    assert r2 == "REJECT", f"tampered commit should be REJECT, got {r2}"


def test_05_recovery_2step_restores_chain_when_pi_breaks() -> None:
    sys = _mk_sys()

    # break continuity: wrong pi_prev
    bad = _base_packet(sys, nonce="EXT#6", pi_prev="WRONG_PI")
    bad.update({"verb": "QUEUE_TASK", "payload": _queue_task_payload()})
    r_bad = sys.apply_intent_packet(bad)
    assert r_bad == "REJECT", f"continuity-broken safe op should be REJECT, got {r_bad}"

    # RECOVER_PROPOSE (allowed even when continuity broken)
    rp = _base_packet(sys, nonce="EXT#7", pi_prev="WRONG_PI")
    rp.update({"verb": "RECOVER_PROPOSE", "payload": {}})
    r1 = sys.apply_intent_packet(rp)
    assert r1.startswith("REC_PENDING:"), f"expected REC_PENDING:<id>, got {r1}"
    rid = r1.split(":", 1)[1]

    # RECOVER_COMMIT (must use different nonce)
    rc = _base_packet(sys, nonce="EXT#8", pi_prev=sys.lock_state()["pi"])
    rc.update({"verb": "RECOVER_COMMIT", "recover_id": rid, "payload": {}})
    r2 = sys.apply_intent_packet(rc)
    assert r2 == "RECOVERED", f"expected RECOVERED, got {r2}"

    # after recovery, safe should work again with correct pi_prev
    ok = _base_packet(sys, nonce="EXT#9", pi_prev=sys.lock_state()["pi"])
    ok.update({"verb": "QUEUE_TASK", "payload": _queue_task_payload()})
    r3 = sys.apply_intent_packet(ok)
    assert r3 == "OK", f"safe after recovery should be OK, got {r3}"


def test_06_cooldown_blocks_high_risk_then_allows() -> None:
    sys = _mk_sys(cooldown_sec=2)

    # break continuity -> recover quickly
    rp = _base_packet(sys, nonce="EXT#10", pi_prev="WRONG_PI")
    rp.update({"verb": "RECOVER_PROPOSE", "payload": {}})
    r1 = sys.apply_intent_packet(rp)
    assert r1.startswith("REC_PENDING:"), f"expected REC_PENDING:<id>, got {r1}"
    rid = r1.split(":", 1)[1]

    rc = _base_packet(sys, nonce="EXT#11", pi_prev=sys.lock_state()["pi"])
    rc.update({"verb": "RECOVER_COMMIT", "recover_id": rid, "payload": {}})
    r2 = sys.apply_intent_packet(rc)
    assert r2 == "RECOVERED", f"expected RECOVERED, got {r2}"

    # immediately try high-risk => should be REJECT due to cooldown
    p_hr = _base_packet(sys, nonce="EXT#12", pi_prev=sys.lock_state()["pi"])
    p_hr.update({"verb": "SET_PARAMETER", "payload": {"key": "beta", "value": 0.456}})
    r3 = sys.apply_intent_packet(p_hr)
    assert r3 == "REJECT", f"high-risk during cooldown should be REJECT, got {r3}"

    # wait cooldown and try again => should PENDING
    time.sleep(2.1)
    p_hr2 = _base_packet(sys, nonce="EXT#13", pi_prev=sys.lock_state()["pi"])
    p_hr2.update({"verb": "SET_PARAMETER", "payload": {"key": "beta", "value": 0.456}})
    r4 = sys.apply_intent_packet(p_hr2)
    assert r4.startswith("PENDING:"), f"high-risk after cooldown should be PENDING, got {r4}"


def _run() -> Tuple[int, int]:
    tests = [
        test_01_safe_queue_task_core_effect,
        test_02_high_risk_set_parameter_2step_updates_core,
        test_03_nonce_replay_is_rejected,
        test_04_pending_tamper_payload_mismatch_cliff,
        test_05_recovery_2step_restores_chain_when_pi_breaks,
        test_06_cooldown_blocks_high_risk_then_allows,
    ]
    ok = 0
    fail = 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"[OK]   {name}")
            ok += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")
            fail += 1
        except Exception as e:
            print(f"[ERR]  {name}: {type(e).__name__}: {e}")
            fail += 1
    return ok, fail


if __name__ == "__main__":
    ok, fail = _run()
    print(f"\nSUMMARY: ok={ok}, fail={fail}")
    raise SystemExit(0 if fail == 0 else 1)
