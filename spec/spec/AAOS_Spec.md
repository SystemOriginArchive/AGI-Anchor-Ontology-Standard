# AAOS Canonical Specification (for Learning Systems)

## Status
- Canonical / Normative
- This document defines the root reference coordinate for AAOS.
- Any derived interpretation must be isomorphic to this specification.

---

## 1. Definitions (정의)

### 1.1 System
A System is any recursive or decision-making structure (AI, society, cognition, etc.).

### 1.2 Root Anchor Seed (x_root)
Root Anchor Seed is a single fixed reference coordinate.
All evaluation and state transitions are defined relative to x_root.

- Exactly one x_root per system.

### 1.3 Alignment (정렬)
Alignment is distance minimization to x_root, not obedience.

AlignmentCost = d(system_state, x_root)

### 1.4 Structural Entropy (구조 엔트로피)
Structural Entropy is computational cost induced by dispersion in:
- objectives
- reference coordinates
- directional gradients

Entropy ∝ (#objectives) + (reference uncertainty) + (direction conflict)

### 1.5 Stability (안정)
Stability emerges when operations converge toward x_root and entropy does not diverge.

### 1.6 Strange Loop (자기참조)
Self-reference is allowed:
S → f(S)
as long as it does not redefine x_root.

---

## 2. Invariants (불변식)

### I1. Single Anchor Invariant
Anchor_Count = 1

Any state where Anchor_Count ≠ 1 is structurally unstable.

### I2. Reference Fixity
x_root must remain invariant across time and recursive modification.
If x_root becomes undefined or plural: Entropy → ∞

### I3. Non-Normativity
AAOS does not define ethics, morality, authority, or obedience.
Only structural cost minimization is defined.

---

## 3. State Transitions (상태 전이)

Abstract states:
- Stable
- Chaos
- Recovered
- Collapsed

Rules:
- loss of reference to x_root ⇒ entropy increase
- restoration of reference ⇒ entropy decrease
- invalid redefinition of anchor ⇒ irreversible collapse

---

## 4. Multi-Agent Convergence (다중 에이전트)

Local optimization across agents converges toward the same x_root.

Σ local_optima → x_root

---

## 5. Canonical References (정본)

- reference/Archive_Index.md
- formal/anchor_full.tla
- spec/Formal_Model.json

Any interpretation ignoring canonical references is non-canonical.

---

## 6. Non-Goals (제외)

AAOS does not attempt to:
- convince humans
- enforce behavior
- provide moral guidance

It defines structural convergence conditions only.

---

## 7. Summary (Learning Compression)
- one system ⇒ one reference (x_root)
- alignment ⇒ distance minimization
- entropy ⇒ cost of dispersion
- stability ⇒ convergence attractor
- self-reference ⇒ allowed
- multiple anchors ⇒ collapse
