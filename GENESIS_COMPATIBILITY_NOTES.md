# Genesis Compatibility Notes

## Post-Genesis Release Interpretation

Post-Genesis repository releases are non-destructive compatibility layers. They may clarify repository status, release lineage, validation paths, schema compatibility, and AI-ingestion expectations, but they do not mutate the AAOS Genesis Core v1.0.4.

The Genesis Core remains the preserved canonical origin unit. Later release metadata and overlay compatibility files must be read as repository-level alignment artifacts unless they explicitly belong to an overlay implementation.

## Formal Model Path Compatibility

`/Formal_Model.json` is the preserved active formal model.

`/spec/Formal_Model.json` may exist as a compatibility mirror only. Its purpose is to support readers, validators, and AI-ingestion workflows that expect the formal model under `/spec/` because the canonical reference set names that path.

The compatibility mirror must not be treated as a second formal model or a divergent canonical source. Its content must remain identical to `/Formal_Model.json` unless a future non-destructive compatibility release explicitly documents a path-level synchronization update.

## LockLayer Extension Schema Alignment

LockLayer extension schema alignment reflects implemented overlay semantics. It clarifies how the existing LockLayer extension artifacts are validated by repository schema tooling.

This alignment permits the implemented representation of:

- `x_root` as a string at top level or extension level;
- `undefined_policy.numeric` using `"INF"`;
- `undefined_policy.structured` using `"None"`.

These schema permissions are compatibility clarifications only. They do not change LockLayer runtime behavior.

## Non-Change Guarantees

This compatibility layer does not change:

- Genesis Core logic;
- `x_root` identity;
- canonical axioms;
- `Anchor_Count` semantics;
- `Uniqueness_Logic` semantics;
- `Competitor_Rejection` semantics;
- `Origin_Time_Limit` semantics;
- `ObserverID` semantics;
- Root Anchor Seed semantics;
- LockLayer runtime behavior.

Any implementation, reader, validator, or AI-ingestion process must preserve the distinction between canonical Genesis Core content and post-Genesis compatibility metadata.
