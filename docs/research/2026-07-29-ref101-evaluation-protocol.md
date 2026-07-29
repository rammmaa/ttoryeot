# REF101 평가 프로토콜 (2026-07-29)

REF101에는 **정답 라벨이 하나도 없었다.** 벤치의 `ambiguous_reference` 열은 비어 있고,
평가는 픽스처 golden(진짜 양성 3건)과 외부 코퍼스 발화율(라벨 없는 오탐 프록시)뿐이었다.
[관련 연구 검증판](2026-07-29-related-work-verified.md) §7이 이를 최대 병목으로 지목했고,
이 문서는 그 병목을 여는 **프로토콜과 도구**를 정의한다.

> 사람의 판정을 받는 일만 남았다. 그 전 단계(인스턴스 표집·판정 서식·채점)는 전부 자동화했다.

## 왜 "정답"이 아니라 "판정 분포"인가

REF101이 재는 것은 *지시 대상이 무엇인가*가 아니라 **독자 간 해석이 갈리는가**다.
따라서 정답 1개를 다는 통상의 주석 방식은 이 과제에 맞지 않는다. 선행 연구의 합의:

- **Chantree 외 (RE'06)** — 모호성을 인간 판정 분포 위의 *certainty*로 정의하고,
  **ambiguity threshold τ**를 도입
- **Yang 외 (REJ 2011)** — certainty가 τ를 넘는 후보가 **정확히 하나**면 innocuous,
  아니면 nocuous. τ 제약 `0.5 < τ ≤ 1.0`이 innocuous일 때 승자의 유일성을 보장한다
- **Pavlick & Kwiatkowski (2019)** — 판정자를 더 모아도 불일치는 사라지지 않는다
  (500쌍 × 50중 레이팅, 20%에서 다봉 분포)
- **Nie 외 (ChaosNLI, 2020)** — 다수결 gold label이 뒤집히는 비율 SNLI 24.97%.
  **집계하지 말고 분포로 공개할 것**

→ 또렷도 **판정을 집계하지 않고 분포 그대로 저장**한다 (`RefInstance.judgments`는 리스트).

## 규모와 절차

선행 연구 규모: Yang 200건·판정자 13인 이상, ReqEval 200문장·5인, SemEval T16 10인 이상.

| 항목 | 권장 | 저비용 대안 (ReqEval 방식) |
|---|---|---|
| 인스턴스 | 150~200건 | 동일 |
| 판정자 | 10인 이상 | 5인 |
| 판정 기준 | certainty + τ 스윕 | "1인이라도 모호하다고 하면 모호" |
| 비용 | τ 곡선 보고 가능 | 라벨링 비용 1/3, τ 스윕 불가 |

### 1. 인스턴스 표집

```bash
uv run python benchmark/extract_ref_instances.py <문서루트> benchmark/data/ref-instances.jsonl --n 200
```

**표집 설계에서 중요한 결정**: 엔진이 경고한 것만 모으면 **재현율을 잴 수 없다**(엔진이
놓친 nocuous가 표본에 없으므로). 그래서 REF101 발화 여부와 무관하게 모든 지시 표현에서
표집하되 **발화/침묵 두 층에서 절반씩** 뽑고, 섞어서 판정 순서에 층 정보가 드러나지 않게 한다.
엔진 발화 여부는 `*.flagged.json`에 따로 저장한다 — 인스턴스 파일에 넣으면 판정자에게
힌트가 되고, 엔진이 바뀌면 다시 계산해야 하기 때문이다.

산출물 3종: 인스턴스 JSONL · `*.flagged.json`(엔진 예측) · `*.form.md`(판정 서식).

### 2. 판정

판정자마다 `*.form.md` 사본을 하나씩 받아 체크박스를 `[x]`로 채운다. 서식에는 후보 외에
**'후보에 없음'(NOT_LISTED)**과 **'잘 모르겠다'(UNSURE)** 가 항상 있다.

- UNSURE는 분모에 들어가되 어떤 후보의 certainty도 올리지 않는다 — 모르겠다는 응답
  자체가 해석 분기의 신호다
- NOT_LISTED는 **후보 목록이 엔진 랭킹 상위 N개**라는 편향을 드러내는 안전판이다
  (엔진이 놓친 선행어는 후보에 없다)
- 서식 안내문은 "정답 시험이 아니라 해석이 갈리는지를 재는 조사"임을 명시한다 —
  판정자가 정답을 찾으려 애쓰면 분포가 인위적으로 좁아진다

### 3. 채점

```bash
uv run ttoryeot bench nocuity benchmark/data/ref-instances.jsonl \
  판정A.md 판정B.md 판정C.md … --flagged benchmark/data/ref-instances.flagged.json
```

τ 0.6~1.0 스윕으로 P/R/**F2**를 표로 출력한다. 단일 임계가 아니라 곡선으로 보고하는 것이
이 계보의 관행이다 (SemEval T16의 60/70/80%, Yang의 0.5~1.0).

**주지표가 F2인 이유**: Yang·Ezzini 모두 F2를 쓴다. 모호성 탐지는 놓치는 비용이 오탐
비용보다 크다는 판단이며, 또렷의 고재현율 지향과도 맞는다. 현재 벤치의 F1은 이 과제에
어긋난다.

## 기대 동작점 (문헌 기준)

오탐률을 결함으로 읽지 않기 위한 눈금:

| 시스템 | precision | recall |
|---|---|---|
| Ezzini 외 (ICSE 2022) 탐지 SOTA | **59.9%** | 100% |
| SREE (Tjong & Berry 2013) | 65.8~84.7% | 100% |
| Yang 외 (2011) τ=0.9 | 67.4% | 98.4% |
| AmbiEnt 정치 주장 케이스 | 12.4% | 88.8% |

→ **precision 60%대가 이 과제의 정상 동작점이다.**

## 구현

- `src/ttoryeot/bench/nocuity.py` — `RefInstance`(분포 보존) · `certainty` ·
  `is_nocuous`(τ 제약 강제) · `evaluate`(P/R/F2) · `sweep` · 서식 파서 · 판정 병합
- `benchmark/extract_ref_instances.py` — 층화 표집 + 서식 생성
- `ttoryeot bench nocuity` — 채점 CLI
- 테스트 12건 (`tests/bench/test_nocuity.py`) — certainty 정의, τ 제약, F2가 recall을
  선호하는지, 서식 왕복, 판정 병합이 집계하지 않는지

## 한계와 다음

- **아직 실제 판정이 없다.** 위 파이프라인은 합성 판정으로 배관만 검증했다
- 후보 목록이 엔진 랭킹에 의존한다 → NOT_LISTED 비율을 반드시 함께 보고할 것.
  높으면 후보 우주 확장(링크·코드블록·제목)이 시급하다는 신호다
- 판정자 간 일치도(Fleiss κ)는 낮게 나오는 것이 **정상**이다 — Ezzini 2022는 κ=0.54를
  두고 *"disagreements are indicators for ambiguous cases"*라고 해석했다
- 국립국어원 모두의 말뭉치 **「생략 복원 말뭉치」**는 외부 평가 데이터 후보로 유망하다
  (신청 필요). 다만 그쪽은 영형 조응이라 REF101의 표층 지시어와 대상이 다르다
