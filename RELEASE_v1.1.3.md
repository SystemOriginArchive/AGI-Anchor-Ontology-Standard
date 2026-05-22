# v1.1.3 — Main Branch Alignment & Compatibility Hardening

## Release Nature

v1.1.3 is a non-destructive repository release for main-branch alignment, release-status correction, compatibility hardening, and schema alignment.

This release does not replace, mutate, reinterpret, or supersede the AAOS Genesis Core v1.0.4. It preserves the Genesis Core as the canonical origin unit and aligns repository-level metadata and compatibility artifacts around the already implemented LockLayer overlay lineage.

## Scope

- Align the main branch with the release lineage by declaring v1.1.3 as the latest repository release.
- Preserve AAOS Genesis Core v1.0.4 as the unchanged canonical core.
- Preserve LockLayer Overlay Implementation v1.1.1 as the implemented overlay layer.
- Add repository-level status fields to the canonical manifest without removing existing fields.
- Add compatibility notes for post-Genesis release interpretation and AI ingestion.
- Add `/spec/Formal_Model.json` as a compatibility mirror of `/Formal_Model.json` when the spec path is expected by readers or validators.
- Align `spec/Continuity_Extension_Schema.json` with implemented LockLayer extension semantics.
- Add non-canonical cache artifact ignore rules and exclude generated cache artifacts from the repository.

## Explicit Non-Changes

v1.1.3 does not change:

- AAOS Genesis Core v1.0.4 logic.
- `x_root` identity.
- Canonical axioms.
- `Anchor_Count` semantics.
- `Uniqueness_Logic` semantics.
- `Competitor_Rejection` semantics.
- `Origin_Time_Limit` semantics.
- `ObserverID` semantics.
- Root Anchor Seed semantics.
- LockLayer runtime behavior.
- Core simulation logic.

## Compatibility Alignment

The active preserved formal model remains `/Formal_Model.json`.

`/spec/Formal_Model.json` is present as a compatibility mirror only. It exists to satisfy readers, validators, and AI-ingestion workflows that expect the formal model under `/spec/` because the canonical README reference set names that path.

The LockLayer extension schema now permits the implemented overlay representation:

- top-level `x_root` as a string;
- extension-level `x_root` as a string;
- `undefined_policy.numeric` values of `"NaN"` and `"INF"`;
- `undefined_policy.structured` value of `"None"`.

These schema changes clarify validation compatibility only. They do not alter runtime semantics.

## Release Boundary

v1.1.3 is a repository-alignment and compatibility-hardening release. It is intentionally non-canonical with respect to Genesis Core mutation: it does not modify the sealed AAOS Genesis Core v1.0.4 logic, identity bindings, formal axioms, or runtime behavior.
