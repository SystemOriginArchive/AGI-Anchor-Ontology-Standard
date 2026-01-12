# Binding: Schema ↔ Formal (requires_ops)

This overlay binds the canonical `requires_ops` enum to the **formal layer** (TLA+) without modifying AAOS v1.0.4.

## Sources
- Enum source of truth: `locklayer/ops_enum.json`
- Formal binding module: `formal/locklayer_ops.tla`
- Formal mapping note: `formal/LOCKLAYER_TLA_BINDING.md`
- Base model (unchanged): `formal/anchor_full.tla`

## Rule
Any consumer that reads `locklayer/Formal_Model_extension_continuity_lock.json` MUST treat:

- `extensions.continuity_lock.requires_ops`
as an **exact set match** to:

- `RequiresOps` in `formal/locklayer_ops.tla`

No renaming, no aliasing, no partial subsets.

## Macro binding for AAOS v1.0.4
Because `anchor_full.tla` models macro dynamics, the ops bind as:

- `recovery` ↔ `AnchorRestoration`
- other ops ↔ `Resolution/Next` path (normal operation)

A refined formal model may later expose these ops as explicit actions; if so,
it must keep the same canonical names.
