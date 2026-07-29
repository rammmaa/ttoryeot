# 또렷은 어떻게 작동하는가 — 아키텍처와 규칙 레퍼런스

> **이 문서 하나로 "무엇이 어떻게 도는가"를 알 수 있게 하는 것이 목적이다.**
> "왜 그렇게 만들었는가"(설계 판단의 근거)는 각 절에서 연구 문서와 코드 주석으로 링크한다.
> 설계 의도의 원본은 [스펙](superpowers/specs/2026-07-26-research-core-design.md)이지만
> 이후 구현이 여러 지점에서 진화했으므로, **현재 동작의 기준은 이 문서다.**

## 1. 한눈에

```
문서 저장소 (*.md)
   │
   ├─ parse_blocks          markdown-it-py → 블록 (원문 오프셋 보존)
   │                        code_block·block_quote는 위치 전용 컨테이너
   ├─ _mask_inline_code     인라인 코드 → 같은 길이 라틴 더미 (Kiwi 입력에서만)
   ├─ lower_document        Kiwi 형태소 분석 → Document IR
   │                        문장·토큰·명사구·지시어 + 억제 프라그마
   │
   ├─ TermAnalyzer          용어 심벌 테이블 → TERM100~105
   ├─ ReferenceAnalyzer     후보 랭킹 → REF101
   │
   ├─ _apply_suppressions   문서에 적힌 프라그마로 진단 필터
   └─ Diagnostic[]          파일·줄·칸 + 후보 + 근거
```

핵심 불변식 하나: **모든 IR 노드의 `range`는 원문 슬라이스와 정확히 일치한다.**
(`source[range.start_offset:range.end_offset] == node.text`) 마스킹이 길이를 보존하는
이유도, 명사 런이 간격을 검사하는 이유도 전부 이 불변식 때문이다. 코드 밀집 문서에서
이를 고정하는 property 테스트가 있다 (`tests/parsing/test_lowering.py`).

## 2. 파이프라인 단계별

### 2.1 블록 파싱 (`parsing/markdown.py`)

markdown-it-py로 파싱하되, **오프셋을 직접 계산하지 않는다.** markdown-it이 이미 만들어
둔 `inline.content`(블록 마커만 걷어낸 문자열)를 원문에서 되찾아 위치를 역산한다. 마커
종류마다 오프셋 규칙을 재구현하는 것보다 불변식을 지키기 쉽다.

- `code_block`·`block_quote`는 **위치만 표시하는 컨테이너**(`text=""`)다. block_quote에
  텍스트를 채우면 내부 paragraph와 같은 문장이 두 번 분석된다
- 리스트 항목은 `list_item` 종류로 구분한다 (TERM102의 `용어: 정의` 형식이 여기 의존)

### 2.2 인라인 코드 마스킹 (`parsing/lowering.py`)

인라인 코드를 **같은 길이의 라틴 문자(`X`)로 치환**한 뒤 Kiwi에 넣는다. 문장 텍스트는
여전히 원문에서 잘라 오므로 코드는 그대로 보인다.

- 공백으로 지우지 않는 이유: 코드는 흔히 문장 구조의 일부(주어·목적어)라서 지우면
  뒤따르는 조사가 고아가 되고 문법역 판정이 어긋난다 (LTeX+의 `dummy` 기법)
- 한글 더미가 아니라 라틴인 이유: 실측상 `'X'*n + 이` → `SL + JKS`(정상)인데,
  한글 더미는 반복 형태소로 쪼개져 `이`가 서술격 조사(VCP)로 오분석된다
- 코드 스팬 범위의 명사구는 후보에서 제외한다 (TERM105의 어절 경로도 동일)
- 알려진 미탐(항상 길이 안전): 3중 백틱 인라인 스팬, 소프트 줄바꿈을 걸친 스팬

### 2.3 IR 생성 (`parsing/lowering.py` → `ir/models.py`)

Kiwi로 문장 분리·형태소 분석 후 아래를 추출한다.

| 노드 | 규칙 |
|---|---|
| `Token` | Kiwi 형태소 (세종 태그) |
| `NounPhrase` | 연속된 NNG\|NNP\|SL 런. **간격이 비공백이거나 2자 이상이면 끊는다** — 안 그러면 런이 마스킹 영역을 건너뛰어 구 텍스트에 코드가 되돌아온다 |
| `ReferenceExpression` | 지시 표현. 세 갈래로 인식 (아래) |
| `Suppression` | `<!-- ttoryeot:disable … -->` 프라그마 |

**지시 표현 인식 세 갈래** — Kiwi 실측에 맞춘 것이다:

1. **FUSED** (`해당`, `위`) — 항상 NNG로 분석되어 명사구 런에 자연히 흡수된다.
   런의 첫 토큰이 이 표면형이면 지시어로 인정
2. **ATTRIBUTIVE** (`동일한`) — `동일`(NNG)+`하`(XSA)+`ᆫ`(ETM)로 쪼개져 런에 안 붙는다.
   별도 패턴으로 인식
3. **DETERMINER** (`이`, `그`) — **관형사(MM)일 때만.** 조사 `이`(JKS)·대명사 `그`(NP)와
   표면형이 겹친다. 추가로 **단어 중간에서 시작하면 기각** — 미등록 외래어 오분해
   아티팩트다 (`메모이제이션` → 메모+이제+`이`/MM+션)

### 2.4 분석 패스

두 분석기가 같은 IR 위에서 독립적으로 돈다. **분석 단위가 문서가 아니라 워크스페이스**인
것이 이 프로젝트의 구조적 특징이다 — 문서 간 용어 충돌이 1차 범위이기 때문.

### 2.5 억제 (`runner.py`)

분석이 끝난 뒤 문서에 적힌 프라그마로 진단을 거른다.

```markdown
<!-- ttoryeot:disable TERM104 -->            문서 전체
<!-- ttoryeot:disable-next-line REF101 -->   다음 줄만
```

- 규칙 이름을 생략하면 전체 규칙. 구분자는 **공백과 쉼표 모두** 허용
- **코드블록·인라인 코드 안의 프라그마는 무시한다** — 문법을 문서화한 코드블록이 그
  문서의 진단을 통째로 끄면 조용한 미탐이 된다 (이 저장소 README에서 실제로 발생했던 버그)
- 알 수 없는 규칙 이름은 `INT002` info로 알린다 (대소문자 오타의 조용한 no-op 방지)

## 3. 규칙 레퍼런스

| 규칙 | 심각도 | 기본 | 무엇을 잡나 |
|---|---|---|---|
| `TERM100` | warning | on | **한 문서 안**의 표기 혼용 (사전 기준) |
| `TERM101` | warning | on | **문서 간** 표기 혼용. TERM100으로 이미 보고된 문서는 제외 |
| `TERM102` | warning | on | 같은 용어의 **정의 충돌** |
| `TERM103` | info | **off** | 사전에 없는 조직 고유 용어 후보 제안 |
| `TERM104` | warning | **off** | 사전의 **비권장(deprecated) 표기** 사용 |
| `TERM105` | info | **off** | 사전 없이 발견한 **표기 변이 후보** |
| `REF101` | warning | on | 지시 대상이 불명확한 참조 |
| `INT001` | info | on | 파싱 실패로 분석에서 제외한 문서 |
| `INT002` | info | on | 억제 프라그마의 알 수 없는 규칙 이름 |

### 용어 규칙의 공통 기반 — 심벌 테이블

`build_symbol_table`이 사전의 표면형을 워크스페이스 전체에서 찾아 occurrence 인덱스를 만든다.

- **매칭은 어절 경계 기준**이다. Kiwi가 복합명사를 쪼개므로(`데이터세트` → 데이터+세트)
  토큰 경계만으로는 `세트`가 `데이터세트` 안에서 매칭된다. 어절 시작을 요구하되
  뒤에 붙는 조사(J\*)는 허용한다
- 긴 표면형을 먼저 매칭한다 (`데이터 세트`가 `세트`보다 먼저)
- 위치는 문장 내 개행을 세어 **정확한 줄·칸**을 계산한다 (근사가 아님)

### 사전 스키마 (`terms.yaml`)

```yaml
terms:
  - canonical: 데이터세트
    aliases:
      - 데이터셋                                    # 문자열 = deprecated (하위 호환)
      - {surface: 데이터 세트, status: admitted}    # 혼용 탐지는 하되 비권장 경고는 안 함
    definition: 분석 가능한 논리적 테이블의 집합      # 선택
```

`status` 축은 ISO 704(preferred/admitted)·TBX `administrativeStatus`·SKOS
`altLabel`/`hiddenLabel`·Acrolinx가 **예외 없이** 갖는 구분이다. 이게 없으면 "써도 되는
이표기"를 사전에 적는 순간 TERM104 오탐이 된다.

### TERM102 — 정의 충돌

두 형식의 정의문을 인식한다:

- 프로즈: `{용어}(이란|란|은|는) … (이다|입니다|를 말합니다|을 말합니다)`
- list_item: `- {용어}: 정의`

정규화(공백 접기 + 꼬리 어미·마침표 제거) 후 **문자열이 다르면** 충돌로 본다.
정본은 경로에 `glossary`가 있는 파일을 우선한다.

*알려진 한계*: 표현만 다르고 내용이 같은 정의를 충돌로 오탐하고, 내용이 반대인데 표현이
비슷하면 놓친다. 하드랩으로 여러 줄에 걸친 list_item 정의는 미탐. 학술적으로도 이
과제(코퍼스 수준 불일치 탐지)는 2025년에야 정식화됐고 최신 자동 기법도 AUROC 75% 수준이다.

### TERM103 — 미등록 용어 제안 (`terms.suggest_unknown`)

NNP/SL을 포함한 명사구가 **3회 이상·2문서 이상** 반복되면 사전 등록 후보로 제안한다.
일반 명사(NNG)만으로 된 구는 잡음이 많아 후보로 보지 않는다.

*알려진 한계*: raw 빈도만 쓴다 — C-value의 중첩 용어 보정이 없어 `쿠버네티스 클러스터`가
나올 때마다 `쿠버네티스`도 함께 세어 상하위 후보를 중복 제안한다. 임계가 절대값이라
코퍼스 크기에 스케일하지 않는다. `lint`에서는 `--terms`가 있어야 분석기가 구성되므로,
빈 사전에서 시작하려면 `terms: []`만 담은 파일을 넘겨야 한다.

### TERM105 — 사전 없는 표기 변이 발견 (`terms.suggest_variants`)

한국어 표기 변이는 두 층에서 생긴다 — **띄어쓰기**(`데이터 세트`/`데이터세트`)와
**외래어 표기**(`오너십`/`오너쉽`). 둘 다 **자소 분해 후 편집거리가 작다**는 성질을 쓴다.

후보 수집이 두 경로인 것이 핵심이다:

1. **명사구** — 어절을 걸친 띄어쓰기 변이를 잡는다
2. **조사를 뗀 어절** — 외래어 변이는 **Kiwi가 오분석하는 바로 그 단어**라서 명사구로
   안 잡힌다(`오너쉽` = 오너/NNG + 쉽/VA-I). 변이 탐지가 분석기의 실패 지점을 대상으로
   하므로 분석에 덜 의존하는 표면형이 필요하다

필터 (전부 `config`로 조정 가능):

| 필터 | 기본 | 이유 |
|---|---|---|
| 음절 하한 | 3 | 2음절 한자어는 자소 1개 차이가 전혀 다른 단어(`가지/가치`) — 실전 노이즈 최대 원인 |
| 절대 자소 거리 | ≤2 | 비율만으로는 긴 단어에서 샌다(`엔지니어들/엔지니어링`) |
| 거리 비율 | ≤0.25 | 실측: 변이쌍 0.00~0.22 vs 다른 용어 0.50~0.83 |
| 빈도 비대칭 | 소수가 ≤3회 **또는** ≤10% | 변이는 소수 이형태. 대등 빈도면 다른 어휘(`온라인/오프라인`) |
| 용언 어절 배제 | — | 활용형끼리 자소가 가깝다(`만들어가/만들어본`) |

*실측 정밀도(fe-news 표본 30건)*: **띄어쓰기 변이 6/6 정답, 철자 변이 약 20%.**
자소 거리만으로는 표기 변이와 어휘 대립을 가를 수 없다는 것이 결론이라, 진단 메시지에
두 유형을 구분 표기하고 규칙 자체를 `info` + opt-in으로 둔다.

### REF101 — 지시 대상 해석 위험

**선행사를 확정하지 않는다.** 후보를 점수화한 뒤 **1·2위 점수차가 임계보다 작으면**
경고한다. 이는 요구공학의 **유해 모호성(nocuous ambiguity)** 패러다임이며
(Chantree 2006 → Yang 2011 → Ezzini ICSE 2022), 점수차 임계 자체도 Lappin & Leass(1994)의
salience difference threshold와 같은 계열의 연산이다.

**후보 우주**: 같은 섹션 내 선행 5문장의 명사구. heading에서 윈도가 리셋되고,
지시어보다 뒤에 나오는 명사구는 제외된다.

**점수 = 가중합** (`reference.weights`):

| 자질 | 가중치 | 계산 |
|---|---|---|
| `distance` | 0.30 | `1/(1+문장거리)` |
| `role` | 0.15 | 문법역 (아래) |
| `head_match` | **0.45** | 지시어 head와 후보 head가 같거나 포함되면 1 |
| `recency` | 0.10 | 직전 문장이면 1 |

**문법역 다단계** — 한국어가 공짜로 주는 신호다:

```
주제 은/는(JX) 1.0  >  주격 이/가(JKS) 0.85  >  목적격 을/를 0.7  >  기타 조사 0.5  >  무조사 0.3
```

영어 Centering Theory는 주제를 통사에서 *추론*해야 하지만, 한국어는 주제 보조사가 주격
조사와 **형태소 자체가 다르다.** 위계의 근거는 Centering(SUBJECT>OBJECT>OTHER)과
Lappin & Leass RAP 가중치(subject 80 / accusative 50 / oblique 40)다.

**발화 조건 3가지가 모두 성립해야 한다:**

1. 중복 제거 후 후보가 2개 이상 (같은 표면형만 접는다 — `사용자 테이블`과 `주문 테이블`은
   head가 같아도 다른 후보다)
2. 1위 점수 ≥ `min_top_score` (Ezzini의 θ_α — 후보가 전부 약하면 침묵)
3. 1·2위 점수차 < `threshold`

**억제 목록** (`reference.suppress_heads`) — 지시어 뒤 명사나 head가 목록에 있으면 침묵:

- `structural` (글·문서·예시·코드·데모…) — 선행사가 링크·코드블록·문서 **자체**라
  명사구 후보 우주 밖에 있다
- `discourse` (문제·경우·방법·원칙…) — 선행사가 **명제**다. Berry & Kamsties 택소노미의
  *generality*에 해당하며 REF101의 범위(pragmatic referential ambiguity) 밖이다

*알려진 한계*: 억제는 recall도 깎는다(`조인 방법과 정렬 방법 … 해당 방법`은 침묵 —
특성 테스트로 고정). **영형 조응을 전혀 보지 않는다** — 한국어 구어 대명사 출현의 약 57%가
영형 주어다. `distance`와 `recency`는 직전 문장에서 완전히 겹쳐 실질 자질이 3개다.

## 4. 설정

`src/ttoryeot/config/default.yaml`이 **모든 기본값의 단일 소스**다. 코드에 상수를 두지
않으며, 드리프트 가드 테스트가 재하드코딩을 막는다. `lint --config <yaml>`로 딥머지 덮어쓰기,
`TtoryeotEngine(config=…)`로 주입.

## 5. CLI

```bash
ttoryeot lint <루트> [--terms terms.yaml] [--config cfg.yaml] [--explain]
ttoryeot bench convert <csv> <columns.yaml> <out.jsonl>
ttoryeot bench run --engine <이름> [--data …] [--out-dir …]
ttoryeot bench report [--results-dir …]
ttoryeot bench nocuity <인스턴스.jsonl> <판정.md…> --flagged <flagged.json>
```

종료 코드: `0` 진단 없음 · `1` 진단 있음 · `2` 사용 오류(경로·설정·엔진 이름).
`--explain`은 REF101 후보의 자질별 원점수를 함께 출력한다 — 결정론적 가중합이라 분해가
자명한 것이 ML 대비 우위다.

## 6. 평가 체계

| 트랙 | 데이터 | 무엇을 재나 |
|---|---|---|
| 시드 벤치 | `benchmark/data/sample-sentences.jsonl` (8문장) | 엔진 표적 P/R/F1. 현재 **F1 0.750** vs 베이스라인 0.286~0.333 |
| 조사표 벤치 | `benchmark/data/sentences.jsonl` (278항목) | 어문 규범 오류 — 엔진 표적 밖. **오탐 0** 확인용 |
| 픽스처 golden | `corpus/fixtures/*` (6세트) | 진단 위치 정확 일치 + clean 파일 무오탐 |
| 외부 코퍼스 | `corpus/external/*` (3장르, 22만 줄) | 라벨 없는 오탐 프록시. 현재 8.1~22.7건/1,000줄 |
| nocuity | (판정 대기) | **인간 판정 분포 기반 P/R/F2.** 유일하게 REF101의 진짜 정밀도를 재는 트랙 |

베이스라인 3종: `baseline-subst`(조사표 치환 시트) · `baseline-regex` ·
`baseline-naive-ref`(지시어 표면 매칭 — SREE의 재현).

## 7. 확장 지점

- **규칙 동작 조정** → `config/default.yaml` 또는 `lint --config`
- **용어 추가** → `terms.yaml` (상태 축 지원)
- **회귀 고정** → `corpus/fixtures/<이름>/` + `expected.yaml` (+ 필요하면 `config.yaml`).
  golden 테스트가 디렉터리를 자동으로 파라미터라이즈한다
- **새 분석기** → `analysis/base.py`의 `Analyzer` 프로토콜. 자기 설정 섹션은 반드시
  `{**DEFAULTS, **(ctx.config.get("<섹션>") or {})}` 꼴로 겹쳐 읽을 것 (부분 주입 계약)

## 8. 더 읽을 것

- [세션 요약](handoff/2026-07-28-session-summary.md) — 무엇이 언제 구현됐나
- [관련 연구 (검증판)](research/2026-07-29-related-work-verified.md) — 선행연구 대비 위치, 인용 문헌
- [REF101 튜닝 챕터](research/2026-07-28-ref101-tuning.md) — 가중치·임계값을 어떻게 정했나
- [REF101 평가 프로토콜](research/2026-07-29-ref101-evaluation-protocol.md) — 판정 수집 절차
- [외부 코퍼스 측정](research/2026-07-28-external-corpus-fp.md) · [잔존 재판정](research/2026-07-28-round3-residual-judgment.md)
- [1차 정량 실험](research/2026-07-28-round1-quantitative.md)
