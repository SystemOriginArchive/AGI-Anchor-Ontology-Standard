{
  "protocol_version": "v1.0.4+",
  "status": "Deterministic Command Plane + Objective Semantics (extensions-only)",
  "description": "This file defines how the Observer’s real-time intent becomes a unique runtime input by mutating ONLY `extensions.*` while preserving the sealed AAOS core.",
  "sections": [
    {
      "section_id": 1,
      "title": "Canonical Binding",
      "content": {
        "observer_id": "Lee_Yu_Cheol",
        "identity_binding": {
          "system_identifier": "Lee_Yu_Cheol"
        },
        "admissible_packets": [
          {
            "observer_id": "Lee_Yu_Cheol"
          }
        ]
      }
    },
    {
      "section_id": 2,
      "title": "Sealed Core (Not Mutated by OOP)",
      "content": {
        "mutations_not_allowed": [
          "RootAnchorID",
          "ObserverID",
          "Anchor_Count",
          "canonical state set (Stable/Chaos/Recovered/DEAD)",
          "canonical transition membership",
          "mapping label literals"
        ]
      }
    },
    {
      "section_id": 3,
      "title": "Sole Mutation Surface",
      "content": {
        "allowed_mutations": [
          "extensions.protocol_refs",
          "extensions.nonce_registry",
          "extensions.intent_log",
          "extensions.command_queue",
          "extensions.effects_log",
          "extensions.runtime_objective",
          "extensions.objective_spec",
          "extensions.task_registry",
          "extensions.runtime_parameters",
          "extensions.executor_policy",
          "extensions.notes"
        ]
      }
    },
    {
      "section_id": 4,
      "title": "Intent Packet (Canonical)",
      "content": {
        "description": "An intent packet is a runtime input that is validated (identity + nonce), appended to `extensions.intent_log[]`, and optionally projected into `extensions.*` and/or `extensions.command_queue[]`.",
        "execution": "Intent packets do NOT execute actions directly; execution occurs only via `extensions.command_queue[]` envelopes.",
        "nonce_rule": {
          "strictly_increasing": true,
          "no_repeat": true
        },
        "commit_rule": {
          "rejected_packets": "If a packet is REJECTED, it MUST NOT be committed to `extensions.nonce_registry` and MUST NOT be appended to `extensions.intent_log[]`."
        },
        "minimal_canonical_packet": {
          "observer_id": "Lee_Yu_Cheol",
          "nonce": "nonce-0001",
          "intent": {
            "verb": "SET_OBJECTIVE",
            "payload": {
              "objective": "complete tasks T1,T2",
              "objective_spec": {
                "type": "TASK_SET_V1",
                "required_task_ids": ["T1", "T2"]
              }
            }
          }
        }
      }
    },
    {
      "section_id": 5,
      "title": "Verb Set (extensions-only)",
      "content": {
        "valid_verbs": {
          "NOP": "no-op (log only)",
          "NOTE_APPEND": "appends `payload.text` (or stringified payload) to `extensions.notes[]`",
          "SET_OBJECTIVE": "sets `extensions.runtime_objective` (optional mirror string), sets `extensions.objective_spec` (typed semantics), syncs `extensions.task_registry.required` when type is `TASK_SET_V1`",
          "SET_PARAMETER": "mutates `extensions.runtime_parameters` only",
          "QUEUE_TASK": "pushes a TASK envelope into `extensions.command_queue[]`, requires `payload.task_id`",
          "QUEUE_CORE_ACTION": "pushes a CORE_ACTION envelope into `extensions.command_queue[]`",
          "EXPORT_STATE": "emits a snapshot (implementation-defined) into `extensions.notes[]` or an export channel"
        },
        "unknown_verbs": "MUST be normalized as a TASK envelope with `payload.task_id = \"UNKNOWN_VERB:<raw_verb>\"`"
      }
    },
    {
      "section_id": 6,
      "title": "Typed Command Envelopes (`extensions.command_queue[]`)",
      "content": {
        "description": "`extensions.command_queue[]` contains ONLY CommandEnvelope records.",
        "generic_envelope_schema": {
          "kind": "TASK",
          "nonce": "nonce-0001",
          "t": 0,
          "payload": {}
        },
        "task_envelope": {
          "kind": "TASK",
          "nonce": "nonce-0001",
          "t": 0,
          "payload": {
            "task_id": "T1",
            "tag": "",
            "params": {}
          }
        },
        "note_envelope": {
          "kind": "NOTE",
          "nonce": "nonce-0002",
          "t": 0,
          "payload": {
            "text": "..."
          }
        },
        "core_action_envelope": {
          "kind": "CORE_ACTION",
          "nonce": "nonce-0003",
          "t": 0,
          "payload": {
            "action": "ExternalDisturbance",
            "args": {}
          }
        },
        "allowed_core_actions": [
          "ExternalDisturbance",
          "ChangeClaimantInChaos",
          "AnchorRestoration",
          "TotalCollapse"
        ]
      }
    },
    {
      "section_id": 7,
      "title": "Objective Spec DSL (Semantic Closure)",
      "content": {
        "objective_spec_types": ["NONE", "TASK_SET_V1", "TAG_TARGET_V1"],
        "TASK_SET_V1": {
          "requires": "required_task_ids[] (unique)",
          "satisfied_when": "required_task_ids ⊆ task_registry.completed[]",
          "objective_remaining": "|required − completed|"
        },
        "TAG_TARGET_V1": {
          "requires": "required_tag, required_tag_count",
          "satisfied_when": "completed_by_tag[required_tag] ≥ required_tag_count",
          "objective_remaining": "max(0, required_tag_count − completed_by_tag[required_tag])"
        },
        "task_completion_semantics": {
          "task_id": "added to completed[]",
          "set_semantics": "unique entries",
          "completed_by_tag": "increments ONLY when a task is newly completed"
        }
      }
    },
    {
      "section_id": 8,
      "title": "B-Closure (EntropyProxy argmin V2)",
      "content": {
        "policy_configuration": {
          "selection_rule": "ENTROPY_ARGMIN_V2",
          "weights": {
            "core": 1.0,
            "queue": 10.0,
            "objective_remaining": 500.0,
            "reject": 500.0
          },
          "tie_break": ["EXECUTE_HEAD", "AUTORESOLVE_CHAOS", "IDLE"]
        },
        "candidate_set_per_tick": {
          "condition_a": {
            "len_command_queue_greater_than_0": [
              "EXECUTE_HEAD",
              "AUTORESOLVE_CHAOS (only if world_state == Chaos and anchor_connection == FALSE)"
            ]
          },
          "condition_b": {
            "len_command_queue_equal_0": [
              "AUTORESOLVE_CHAOS (only if world_state == Chaos and anchor_connection == FALSE)",
              "IDLE"
            ]
          }
        },
        "entropy_proxy": {
          "formula": "EntropyProxy = (w_core * core_entropy_after) + (w_queue * queue_len_after) + (w_obj * objective_remaining_after) + (w_reject * reject_term)",
          "selection_logic": "Choose candidate with minimal EntropyProxy, Ties broken deterministically by executor_policy.tie_break"
        }
      }
    }
  ]
}
