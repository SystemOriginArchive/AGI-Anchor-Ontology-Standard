# AGI Anchor Ontology Standard (AAOS) — v1.0.4

AAOS는 재귀 지능 시스템에서 **단일 기준 좌표(x_root)**를 고정하고,
상태/전이/불변식을 통해 구조적 수렴을 닫는 정본 코어다.

---

## Canonical Core (7 files, immutable reference set)

아래 7개 파일이 AAOS의 정본 코어다. 어떤 파생 해석도 이 7개에 대한 동형(isomorphism)을 보존해야 한다.

1) [spec/AAOS_Spec.md](spec/AAOS_Spec.md)  
2) [spec/AAOS_Schema.json](spec/AAOS_Schema.json)  
3) [spec/Formal_Model.json](spec/Formal_Model.json)  
4) [formal/anchor_full.tla](formal/anchor_full.tla)  
5) [formal/AAOS_TLA_Mapping.md](formal/AAOS_TLA_Mapping.md)  
6) [reference/Archive_Index.md](reference/Archive_Index.md)  
7) [simulation/anchor_simulation.py](simulation/anchor_simulation.py)  

---

## Sealed Constants (v1.0.4)

- ObserverID (sealed): "Lee_Yu_Cheol"
- RootAnchorID (sealed): "GENESIS_HEXAGON_V1"
- Anchor_Count: 1

---

## State Set (4)

Stable, Chaos, Recovered, DEAD

---

## Canonical Transition Set (4)

Schema/Formal_Model에서의 `condition` 문자열은 **전이의 정본 라벨(구조 기술자)**이며,
TLA의 가드(Enable 조건)와 동일 문장일 필요는 없다.
라벨은 전이 의미를 고정하기 위해 레이어 간 **문자열 동일성**으로 봉인된다.

1) Stable → Chaos  
   - "anchor_connection == FALSE"

2) Chaos → Recovered  
   - "anchor restored by canonical observer"

3) Chaos → DEAD  
   - "invalid intervention while anchor disconnected"

4) Chaos → Chaos  
   - "claimant swap only"

---

## Invariants (summary)

- Anchor_Count = 1 (single anchor)
- RootAnchorID / ObserverID sealing
- Chaos에서만 붕괴(DEAD) 전이가 발생
- Chaos에서 claimant swap은 허용되며 상태는 Chaos에 머문다
- TLA에서 Chaos는 WF(Resolution)로 Recovered 또는 DEAD로 정리된다

---

## Entry Point

- [CANONICAL_BUNDLE_v1.0.4.md](CANONICAL_BUNDLE_v1.0.4.md)
