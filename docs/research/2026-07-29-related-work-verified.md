# 관련 연구 심층 재조사 (2026-07-29)

> 2026-07-26 조사([related-work](2026-07-26-related-work.md))는 ChatGPT 대화 기반 1차 정리라
> 검증이 부족했다. 이 문서는 **1차 자료(특허 청구항·ACL Anthology 전문·표준 문서·저장소 코드)를
> 직접 확인**해 다시 쓴 것이며, 앞 문서를 대체한다. 확인 수준은 항목마다 표기했다
> (`전문 확인` / `초록만` / `미확인`).
>
> **가장 중요한 결론부터: 또렷이 신규성으로 내세워 온 "지시 대상을 맞히지 말고 해석 위험을
> 탐지한다"는 아이디어는 새롭지 않다.** 요구공학의 nocuous ambiguity 계보가 2006년부터
> 소유해 왔고, 1·2위 점수차 임계라는 기제조차 1994년 Lappin & Leass가 이미 썼다.
> 아래 §5에서 포지셔닝을 교정한다.

## 1. 한국어 교정 도구 — 부산대/나라인포테크가 실제로 하는 일

### 부산대 인공지능연구실 + 나라인포테크 「한국어 맞춤법/문법 검사기」(현 「바른한글」)

권혁철 교수팀이 1990년대부터 개발, 한컴오피스·잡코리아 등에 탑재된 사실상의 국내 표준.

**메커니즘은 마케팅이 아니라 특허 청구항으로 확인했다** — KR100798752B1(출원 2007,
출원인 나라인포테크·권혁철). **규칙·사전 기반이며 통계/신경망이 아니다.** 4단 직렬 구조:

1. **일반사전 분석기** — 어절을 형태소로 분해해 `품사·오용어·어미조사·전문용어` 사전과 대조.
   문체 오류 가능성이 있으면 **식별번호(플래그)만** 남긴다
2. **복합명사 분석기** — 복합명사 제약규칙으로 띄어쓰기 판정
3. **다수어절 분석기** — 여러 어절에 걸친 관용·연어를 한 단위로
4. **의미문체 분석기** — 1단계에서 플래그된 어절만 골라 앞뒤 문맥과 함께 판정

즉 **"싼 사전 조회로 후보를 플래그 → 비싼 문맥 규칙은 플래그된 것에만"** 이라는 트리거 기반
지연 평가다. 학술 계보로는 **의존문법 기반 부분 문장 분석(partial parsing)** — 전체 구문
분석을 하지 않고 오류 가능 지점에서 지배소 방향으로 필요한 만큼만 파싱한다.

**분석 단위는 문장 이하다.** 최대 단위가 "다수어절"이고 문맥은 앞뒤 어절이다. 특허·논문·공식
안내 어디에도 문단 간·문서 간 분석은 없다. ("없다"의 증명이 아니라 "있다는 근거를 찾지 못했다"가
정확한 서술이다.)

- 논문 계보: 김현진·심철민·권혁철(1996) 부분 문장 분석 · 소길자 외(1998) **중의성이 검사기
  오류를 만드는 3지점** 분류 · Kang 외(2002, IEA/AIE) 잠재적 지배 관계로 **파싱의 시작점·방향·
  범위를 유도** · Kang 외(2003, ACM TALIP) 오류 패턴 분석으로 부분 파싱 개선(미등록 오류어 제외
  정확률 98.94%, `초록만`) · 소길자 외(2011) **KorLex로 규칙 일반화 — 규칙 수 64.8%로 줄이며
  정확률 +6.2%p**
- `speller.cs.pusan.ac.kr`은 현재 DNS 조회 실패(`미확인`), 서비스는 `nara-speller.co.kr`로 이전

**정오**: 검색에서 함께 나오는 "65개 규칙 / 교정 정확률 96.49%"는 **다른 팀**(이공주 외, 2003,
전체 문장 분석 기반)의 수치다. 부산대 계열에 인용하면 오류다. 부산대 검사기의 규칙 개수는
어떤 공개 자료에서도 확인하지 못했다.

### 실측 성능 — KAGAS(ACL 2023)의 베이스라인 결과 `전문 확인`

KAGAS 논문이 부산대 검사기(hanspell 래퍼 경유)를 유일한 상용 베이스라인으로 채점한 결과가
**유일한 독립 정량 측정**이다:

- Kor-Union: **P 37.34 / R 11.58 / F0.5 25.85**, GLEU 28.82
- 유형별 F0.5: **WS(띄어쓰기) 61.72 · PUNCT 38.46 · SPELL 14.29**, 나머지 12개 유형 13~25
- 논문 표 캡션: *"scores by Hanspell are biased toward WS and SPELL"*

**높은 정밀도·매우 낮은 재현율**은 보수적 규칙 시스템의 서명이다. 또렷이 "기존 한국어 교정
도구는 띄어쓰기·철자에 편향"이라고 말할 때 인상이 아니라 이 수치를 인용할 수 있다.

### 접근성 — 왜 한국어 교정 API 생태계가 비어 있는가

- **2016년**: 권 교수가 네이버·카카오의 역공학 의혹 제기 → 카카오 API 공개 중단, 네이버도 비공개.
  **결과적으로 한국어 맞춤법 API 생태계 자체가 정체**
- **2023년**: 한 IP에서 한 달간 5~6억 건 크롤링(딥러닝 학습 목적 추정) → 상업적 대량 처리 제한.
  개인·학생 무료는 유지
- 현재 나라인포테크는 온라인 API(시범)·오프라인 API(기업 발주)만 제공, 가격 비공개

→ 또렷이 **외부 교정 API에 의존하지 않는 로컬·결정론적 설계**를 택한 것은 취향이 아니라
생태계 제약에 대한 합리적 대응이다. 동시에 **또렷 벤치마크가 부산대 검사기를 자동 호출하면
약관 위험**이 있으므로, 대조군은 KAGAS 공개 수치 인용이 안전하다.

### 오픈소스 생태계 — "엔진"은 없다

`9beach/hanspell`, `ssut/py-hanspell`, `jhaemin/speller-api`, `fallroot/vscode-dandy`,
`kexplo/koach`(2024 아카이브) — **전부 웹 서비스 스크래핑 래퍼**다. 전부 텍스트 스트림 단위이며
**마크다운 AST 인식·코드블록 제외·문서 간 상태 유지가 없다.**

GitHub를 12개 질의(`한국어 맞춤법`, `korean lint`, `용어 일관성 검사` 등)로 훑었으나 **문서
AST·용어 인덱스·저장소 단위 분석을 하는 프로젝트는 하나도 없었다.** 이 자리는 비어 있다.

빌릴 것: 부산대 응답 스키마(`start/end/orgStr/candWord/help`)가 또렷 진단과 거의 동형이다 —
**호환 출력 포맷을 제공하면 dandy 같은 기존 에디터 확장이 또렷을 백엔드로 붙일 수 있다.**
`.hanspell-ignore`(glob 무시 목록) 패턴도 이식 가능하다.

### 한컴 실무 기록 — LLM 단독이 실패하는 이유 `전문 확인`

한컴 기술 블로그가 공개한 자체 교정기 구축기가 또렷의 "LLM 없이" 연구 질문을 정당화한다.
순수 LLM에서 관측된 실패: **① 비결정성**(동일 입력에 매번 다른 출력) **② 과교정**(의미까지 변경)
**③ 설명 불가**(근거를 못 냄) **④ 지연**. 최종 구조는 규칙 엔진(50+ 패턴) → 신경망 → **검증
필터**(출력이 입력 대비 20% 넘게 길어지면 기각)의 3층이었다.

빌릴 것: "길이 증가 20% 초과 시 기각" 같은 **값싼 사후 검증 필터**는 또렷의 후보 제안에 즉시
적용 가능하다.

### 한국어 스타일 가이드 — 규범은 있는데 집행이 없다

- **카카오 개발자 문서 스타일 가이드** `전문 확인` — 가장 기계화하기 쉽다. 종결형(`-니다`),
  외래어 표기법 준수(`메서드`·`파라미터`), 첫 등장 시 원어 병기, 콜론·대괄호·숫자 형식,
  그리고 결정적으로 **"첫 정의 후 용어 일관성 유지"**
- **토스 테크니컬 라이팅 가이드** — CC BY-NC-SA 4.0(**비상업·2차저작 제한** — 규칙을 코드로
  옮길 때 주의)
- **국립국어원 공공언어 지침** — 공공저작물 **제4유형(변형 금지)**, 재가공 제약
- **국립국어원 한국어 어문규범 CSV**(공공데이터포털) — **제1유형(출처표시만, 상업 이용 가능)**.
  용례정보 포함

→ **카카오 가이드는 이미 사실상 린트 규칙 명세이고, "용어 일관성 유지"는 또렷 TERM101/102와
1:1 대응한다. 업계가 규범으로 선언했으나 아무도 자동 검사하지 않는다** — 또렷의 가장 강한
정당화 문장이다. 어문규범 CSV는 진단에 "한글 맞춤법 제N항" 근거를 붙일 수 있는 유일한
상업 이용 가능 규범 데이터다.

### 한국어 GEC 데이터셋

- **KAGAS 3종**: Kor-Learner 28,426 / Kor-Native 17,559 / Kor-Lang8 109,559 문장쌍.
  14개 오류 유형(INS, DEL, WS, WO, SPELL, PUNCT, SHORT, VERB, ADJ, NOUN, PART, END, MOD, CONJ).
  ERRANT 확장 + Damerau-Levenshtein + 한국어 특화 비용, **오류 유형 우선순위를 명시해 결정적
  출력 보장**, 유형별 인간 수용률 공개(WS/INS/DEL 100%, CONJ 43.59%)
- **K-NCT**(IEEE Access 2022) 골드 테스트셋 3,000문장 `2차 정보` · **KoLLA v2.0**(LREV 2025)
  학습자 에세이 1,419문장 **다중 참조 2개씩**
- **모두의 말뭉치**: **「생략 복원 말뭉치」**(문맥으로 생략된 지시 대상 복원)가 REF101의
  **외부 평가 데이터 후보로 유일하게 유망**하다 — 신청 가치 높음
- **AI말평**(국립국어원 공식 벤치마크): 맞춤법/문법 교정 과제도, 상호참조 해결 과제도 **없다**

→ **문서/저장소 수준 용어 일관성·참조 모호성 벤치마크는 한국어에 존재하지 않는다.**
또렷의 "그 사이를 겨냥한다"는 주장은 반증 시도를 거쳐 살아남았다.

## 2. 모호성 탐지의 학술적 선행 — 또렷이 재발명한 것들

### nocuous ambiguity 계보 (이것이 REF101의 진짜 선행연구다)

| 연도 | 연구 | 내용 |
|---|---|---|
| 2006 | Chantree, Nuseibeh, de Roeck, Willis (RE'06) | **nocuous/innocuous ambiguity 원전.** 모호성을 이분법이 아니라 *독자 간 해석이 갈릴 위험*으로 재정의. 인간 판정 분포의 certainty와 **ambiguity threshold τ** 도입 |
| 2010 | Yang 외 (COLING 2010) `전문 확인` | 조응 표현으로 확장. 후보별 Y/Q/N 태그 조합으로 nocuity 판정 |
| **2011** | **Yang, de Roeck, Gervasi, Willis, Nuseibeh (REJ 16(3):163–189)** `전문 확인` | **REF101과 과제 정의가 사실상 동일한 논문** |
| 2015 | SemEval-2015 Task 16 (DNA) | nocuous ambiguity **탐지**를 shared task로 제안(대명사 선행사 포함). 임계 60/70/80% 스윕. **참가팀 없이 무산** |
| 2020 | ReqEval@NLP4RE `전문 확인` | detection/resolution 서브태스크 **명시적 분리**, 200문장, 어노테이터 5인, "1인이라도 모호하다면 모호" |
| **2022** | **Ezzini 외 (ICSE 2022)** `전문 확인` | 현재 SOTA. 탐지 P≈59.9% / R=100% |
| 2023 | Liu 외 (EMNLP, AmbiEnt) `전문 확인` | LLM 시대의 재정식화 |

**Yang 2011의 문장은 또렷 README와 거의 동어반복이다**: *"our work emphasizes the discovery of
potential nocuous ambiguity in order to notify a user rather than attempting to disambiguate.
The user retains control over the final determination."*

Ezzini 2022는 아예 *"RE prioritizes ambiguity detection over anaphora resolution… coreference
resolvers have not been built to support ambiguity detection."*라고 못박는다.

**기제도 새롭지 않다.** REF101의 "1·2위 점수차 < 임계 → 경고"는:
- **1994** Lappin & Leass RAPSTAT의 *salience difference threshold*(테스트값 100)와 **같은 연산** —
  목적만 반대(RAP는 격차가 좁으면 선택을 뒤집고, 또렷은 경고한다)
- **2011** Yang의 innocuous 조건 *"one clear Y candidate whose certainty exceeds all others by a margin"*
- **2022** Ezzini의 **θ_δ = 0.1** — 확률 차이가 임계 미만이면 `inconclusive`

**자질도 기성품이다.** REF101의 4자질은 Yang의 17종·Ezzini의 45종의 **엄격한 진부분집합**이다.

### 고전 salience 알고리즘 (REF101 가중합의 출처)

- **Lappin & Leass (1994, CL 20(4))** `전문 확인` — RAP. salience 가중치: sentence recency **100** ·
  subject **80** · head noun **80** · existential **70** · accusative **50** · non-adverbial **50** ·
  indirect object **40**. 새 문장마다 절반 감쇠. 성능 86%(Hobbs 82%). 저자 각주: *"가중치의 구체적
  값은 임의적이고, 중요한 것은 요인 간 비교 관계다"*
- **Hobbs (1978)** `초록만` — 가중치 없이 구문 트리 순회 순서만으로 82%. 또렷 `distance` 자질의 원형
- **Grosz, Joshi, Weinstein (1995, CL 21(2))** `전문 확인` — Centering Theory.
  **SUBJECT > OBJECT(S) > OTHER** 위계가 또렷 `role` 자질의 이론적 근거

### "멍청한 도구" 논변 — 또렷 설계의 정당화이자 부담

**Berry, Gacitua, Sawyer, Tjong (2012, REFSQ)** `전문 확인`: 대부분의 NLP RE 도구는
*"they **fake** understanding"*. 불완전한 도구의 해악 — 분석가 작업량을 오히려 늘리고,
**정당화되지 않은 확신으로 분석가를 재운다(lull)**. 제안: 분석 A 안에 알고리즘적으로 식별
가능한 **사무적 부분**이 있으면 도구가 그것만 **100% recall**로 맡고 나머지는 인간이 갖는다.

**SREE (Tjong & Berry, 2013)** `전문 확인`: 100% recall을 위해 precision을 의도적으로 포기.
파서·POS 태거를 **의도적으로 배제**하고 순수 어휘 스캐너 + 모호성 지표어 코퍼스 10종(Pronoun 포함).
recall 100% / precision 65.84~84.69%.

→ **또렷의 `baseline-naive-ref`(지시어 표면 매칭)는 우연이 아니라 SREE라는 실재 도구의 재현이다.**
REF101이 그 위에서 precision을 얼마나 벌었는지가 논문의 핵심 표가 되어야 한다.

→ **부담**: `suppress_heads`는 precision을 위해 recall을 깎는 장치라 Berry 노선과 정면 충돌한다.
Berry를 인용하려면 "억제되는 것은 모호성이 아니라 generality"라는 논증이 필요하다(§5 참조).

### 모호성 유형 택소노미 — 또렷이 다루는 칸

**Berry & Kamsties (2004)**: lexical / syntactic / semantic / **pragmatic(referential·deictic)** /
vagueness / **generality** / language error.

- REF101이 다루는 것은 **pragmatic referential ambiguity**
- **generality**(여러 해석에 열려 있으나 일반적 의미가 그것들을 포괄해 결정이 불필요)는 배제 —
  `suppress_heads`의 discourse 그룹(문제·경우·방법·방식)이 사실상 이 장치이며, **이 이름을 빌리면
  애드혹 목록이 아니라 이론적 근거가 생긴다**

### 인간 불일치를 신호로 다루는 계보

- **Pavlick & Kwiatkowski (2019, TACL)** `전문 확인` — 쌍당 50중 레이팅. 판정자를 더 모으거나 문맥을
  더 줘도 불일치가 **사라지지 않는다**(20%에서 다봉 분포)
- **ChaosNLI (Nie 외, 2020, EMNLP)** `전문 확인` — 예시당 100 라벨, 464,500 어노테이션.
  기존 다수결 라벨이 뒤집히는 비율 SNLI 24.97% / MNLI 31.77%. **모델이 못 푸는 구간 = 인간 합의가
  낮은 구간**
- **AmbiEnt (Liu 외, 2023, EMNLP)** `전문 확인` — GPT-4의 4템플릿 정합률 **2.5%**(랜덤 6.25%보다 낮음).
  **LLM이 모호성 모델링에 실패한다는 실증** — Berry(철학)와 짝을 이루는 근거
- **Winograd Schema (Levesque 외, 2012)** `전문 확인` — **반드시 대비시켜야 할 논문.** WSC는
  "파서에게는 모호하나 인간에게는 모호하지 않은" 문장을 설계 규격으로 삼는다. REF101이 잡으려는
  것은 WSC가 의도적으로 **배제한** 것 — 인간에게도 갈리는 케이스다. 이 대비가 "왜 coreference
  정확도로 REF101을 평가할 수 없는가"를 한 문단으로 설명한다

### 한국어 — 가장 빈약한 영역

- **Kim, Lee, Jung, Choi (2023, ACL Industry)** `전문 확인` — **한국어로 "해소"가 아니라 "탐지"를
  명시적 과제로 세운 확인된 유일한 연구**(SK텔레콤 A.). 지표 **ADR/MDR/CR/APR**은 정답 라벨 없이
  계산되므로 **또렷의 외부 코퍼스 발화율 측정을 정식 지표로 승격**시킬 수 있다.
  실사례: "앞으로 가봐"를 61.7%가 "앞으로 이동", 38.3%가 "이전으로 이동"으로 해석하고 각자 확신
- **구문 구조 기반 한국어 요구사항 문서 대용어 해소 (2010, KIPS-B)** `초록만` — **도메인이 가장
  가까운 한국어 연구.** 요구사항 문서에 인칭대명사가 거의 없고 **지시대명사가 지배적**이라는 관찰이
  또렷과 일치. R 92.45 / P 69.98. **단 resolution이지 detection이 아니다** — 기존 문서의 "한국어
  요구사항 문서 모호성 연구를 못 찾았다"는 서술의 반례에 가장 가까우므로 반드시 인용해야 한다
- **Park 외 (2020, Findings of EMNLP)** — 한국어 e2e coref **CoNLL F1 66.9**. 한국어는 해소조차
  F1 67 수준이라는 사실이 "해소 대신 탐지"의 실용적 근거
- **Zero Object Resolution (Park 외, 2015, PACLIC)** `전문 확인` — 한국어는 목적어까지 생략된다.
  Hong(2000): 한국어 구어 대명사 출현의 **약 57%가 영형 주어**. → **REF101은 영형 조응을 전혀 보지
  않는다. 알려진 한계로 반드시 기재해야 한다**

## 3. 용어 관리 — 표준과 산업 실무

### 상태 축(status)은 모든 표준이 갖는다

| 표준/도구 | 상태 구분 |
|---|---|
| ISO 704 / ISO 1087 | preferred / admitted / (deprecated) |
| TBX (ISO 30042) `전문 확인` | `administrativeStatus` 7값 picklist (preferred/admitted/deprecated/legal/regulated/standardized/superseded) |
| SKOS `전문 확인` | `prefLabel` / `altLabel`(정상 이표기) / `hiddenLabel`(감출 표기) |
| Acrolinx / Congree | preferred / admitted / deprecated — **등급별로 검사 동작이 다르다** |

**이것이 또렷의 가장 심각했던 단일 설계 결함이었다.** `aliases`가 admitted와 deprecated를 구분하지
못해, `enforce_canonical: true`면 "써도 되는 이표기"까지 무차별 경고했다. 사용자는 오탐을 감수하거나
admitted를 사전에서 빼서 TERM100/101의 혼용 탐지까지 잃는 선택을 강요받았다.
→ **2026-07-29 수정 완료**(`TermAlias.status`, 문자열 alias는 deprecated로 하위 호환).

TBX/SKOS 대비 아직 없는 필드: concept **ID**(정본 표기를 바꾸면 동일성이 깨짐 — K8s glossary의
`id`가 같은 역할), **domain/subjectField**(같은 표기가 도메인별로 다른 개념일 때 TERM102 오탐 차단),
`definition_source`(현재는 파일명에 `glossary`가 있는지로 정본 판정), `partOfSpeech`, 엔트리별
severity, 근거 link.

### 산업 실무 — 또렷의 TERM 규칙은 대부분 이식이다

- **Acrolinx term harvesting** = TERM103, **deprecated-term flagging** = TERM104. 상용에 이미 있다
- **Xbench**(번역 QA) `전문 확인`: **Key Term Mismatch** = TERM104, **Inconsistency in Target** =
  TERM100/101의 다국어판. 프로젝트 전체를 한 코퍼스로 적재해 **파일 경계를 넘는 불일치**를 잡는다
- **Vale**: `Vale.Terms`(승인 용어 강제) = TERM104, `Vale.Avoid` = 금지어. **단 Vale에는
  TERM100/101/102가 없다** — 사전에 없는 혼용을 발견하지 못하고, 정의 충돌 개념 자체가 없다
- **textlint + prh**(일본어 表記ゆれ) — **또렷 `terms.yaml`과 거의 동형**(`expected`=canonical,
  `patterns`=aliases). prh가 앞서는 점: alias를 **정규식**으로 쓸 수 있고, `<!-- prh:disable -->`
  **인라인 프라그마**로 오탐을 문서에서 억제하며, `imports`로 조직 사전 + 팀 사전을 겹친다.
  **한국어에 이 생태계의 등가물이 없다**는 것이 또렷의 포지션을 지지한다
- **Kubernetes / MDN 용어집** `전문 확인` — 둘 다 `aka`/별칭을 관리하지만 **자동 검사는 하지 않는다.**
  용어집은 있고 강제는 사람이 한다. MDN의 `GlossaryDisambiguation`은 TERM102에 대응 — 같은 표기가
  두 개념이면 "충돌"이 아니라 **다의어**인데, 또렷은 이를 구별할 수단이 없다

### 자동 용어 추출(ATE) — TERM103은 C-value 이전 수준

- **termhood vs unithood** (Kageura & Umino 1996) — 두 축이 독립이다. 또렷은 unithood를 Kiwi
  명사구 경계에 100% 위임하고 termhood를 raw frequency로 근사했다. 어느 축도 명시적으로 재지 않는다
- **C-value / NC-value** (Frantzi, Ananiadou & Mima 2000) — 핵심은 **중첩 용어 보정**:
  `C-value(t) = log₂|t| · (f(t) − (1/P(N_t))·Σ f(v))`. "데이터 세트"가 항상 "학습 데이터 세트"
  안에서만 나오면 독립 용어 점수를 깎는다. **또렷은 중첩 관계를 전혀 보지 않아 "쿠버네티스
  클러스터"가 20회면 "쿠버네티스"도 20회로 세어 상하위 후보를 중복 제안한다**
- **weirdness / 대조 코퍼스** — 절대 빈도가 아니라 도메인/일반 코퍼스 상대 빈도비.
  또렷의 `min_count 3 / min_docs 2`는 **코퍼스 크기에 스케일하지 않는다**
- **ACTER / TermEval 2020** `초록만` — ATE는 최신 Transformer로도 **F1 0.5~0.69**가 상한.
  → TERM103을 `info` + opt-in으로 둔 현재 설계는 **문헌에 비추어 옳다**

### 정의 추출·충돌 — TERM102만이 신생 영역

- **Hearst(1992) → WCL(Navigli & Velardi, ACL 2010) → DEFT(2019)**: 또렷의 정규식 2패턴은
  **Hearst 수준**이다. WCL 데이터셋이 부정 예를 2,847개(정의문 1,717~1,871개보다 많이) 넣은 이유가
  그대로 재현된다 — `X는 … 이다`는 서술문 일반형이라 **정밀도가 문제**다("데이터세트는 어제 삭제되었다")
- **CLID / WikiCollide (2025, EMNLP)** — 코퍼스 수준 불일치 탐지를 **2025년에야 정식화**했다.
  Wikipedia 사실의 3.3%가 모순, 불일치 유형 중 **정의(용어 해석 차이) 10.6%**.
  완전 자동 최고 성능 **AUROC 75.1%**
  → **TERM102는 또렷의 5개 규칙 중 유일하게 "새롭다"고 말할 수 있는 것.** 동시에 메커니즘 격차도
  가장 크다 — 최신 연구가 NLI로 푸는 문제를 **문자열 완전 일치**로 근사하고 있다

### 한국어 공개 자원 (사전 부트스트랩)

- **국립국어원 어문규범 용례 API**(공공데이터포털 15112892/15104999) — 외래어 표기 용례.
  **`오너십/오너쉽` 계열 deprecated→preferred 쌍을 자동 생성할 수 있는 유일한 공개 소스**.
  단 라이선스 **제2유형(출처표시+비영리)** — 데이터 동봉보다 생성 스크립트 + 사용자 키 방식이 안전
- **표준국어대사전/우리말샘 API** — `pos`·`cat`(전문 분야 67종)·뜻풀이·동의어. 사전 스키마의
  결손 필드를 자동으로 채울 수 있다
- **국립국어원 다듬은 말** — `deprecated → preferred` 쌍의 완성형(일괄 다운로드 없음)
- **TTA 정보통신용어사전** — IT 도메인 정합성 최상이나 API/덤프 없음

## 4. 문서 린터 생태계 — 저장소 스코프는 아키텍처가 금지한다

소스 코드를 직접 읽어 스코프 경계를 검증했다.

| 도구 | 분석 단위 | 용어 일관성 | 지시 모호성 |
|---|---|---|---|
| **Vale** (Go) | **파일** — `sizedwaitgroup`으로 파일마다 goroutine, 상태가 `core.File`에 갇힘 | `consistency`(사전 선언 쌍, 파일 내, 순서 의존) | 없음 |
| **textlint** (JS) | **단일 문서** — 커널 API가 `lintText(text)` | `no-synonyms`(Sudachi 동의어), `prh` | 없음 |
| **RedPen** (Java) | 문장/섹션/**문서** | `JapaneseExpressionVariationValidator` — **읽기 정규화 기반 자동 변이 그룹핑** | 없음 |
| **LanguageTool** (Java) | 문장 / **텍스트**(`TextLevelRule`) | `AbstractWordCoherencyRule`(최초 등장 우선), **`ConsistencyPatternRuleTransformer`(다수결)** | 없음 (8.2MB 룰에 anaphora/referential grep 0건) |
| **Acrolinx** (상용) | **코퍼스**(batch) | ISO 12620 상태 + term harvesting | 통사적 맨-지시사 검사 1건 |
| proselint / write-good / alex | 파일 / 단락 | 하드코딩 14쌍 / 없음 / 없음 | 없음 |

**핵심 사실 세 가지:**

1. **저장소 단위 용어 충돌 탐지는 "드문" 게 아니라 사실상 부재하다.** GitHub 검색 실측:
   `glossary validation docs` **0건**, `korean documentation style checker` **0건**,
   `textlint korean` **0건**. 가장 가까운 OSS가 `textlint-rule-terminology`(★55, 파일 단위).
   저장소 전역 그래프를 만드는 흔한 도구는 **링크 체커뿐**이다 — 생태계는 "파일 간 분석이
   필요하다"를 이미 인정했고(링크), 대상을 용어로 확장하지 않았을 뿐이다.
2. **업계 표준 스타일 패키지는 `consistency`를 쓰지 않는다.** `errata-ai/Microsoft` 40룰과
   `errata-ai/Google` 31룰 모두 **consistency 0건**이고, 양쪽 `Passive.yml`은 176개 과거분사
   하드코딩 리스트가 **바이트 단위 동일**하다. 즉 "가장 권위 있는 기술문서 스타일 가이드도
   기계화하면 정규식 뱅크가 된다" — 또렷의 베이스라인 비교(F1 0.750 vs 정규식·치환 0.286~0.333)가
   겨루는 상대가 정확히 이 산업 표준 수준이다.
3. **SARIF는 테이블 스테이크스가 아니다.** Vale(v3 tarball 28MB grep 0건)·textlint·proselint·
   alex·LanguageTool·Acrolinx·Grammarly **어디에도 없다.** 산문 린팅 생태계가 채택하지 않은
   포맷이므로 **우선순위에서 내려도 된다** (초기 가정과 다른 실측 결과).

**한국어 지원 실태**: Vale은 `internal/core/file.go`가 `lang := "en"`을 **하드코딩**하고 스펠링
필터 `[^a-zA-Z_']`가 **한글 토큰을 조용히 버린다**. RedPen은 `ko`를 지원 언어 목록에 넣어두고도
토크나이저가 `WhiteSpaceTokenizer`뿐이라 위 표의 Validator가 **한국어에서 하나도 동작하지
않는다**(전부 `[ja]`). 일본어가 kuromoji/Sudachi 위에 15년간 룰 저장소 36개와 기업 프리셋을
쌓는 동안 **한국어에는 그 층이 없다.**

### 통제언어 — REF101의 규범적 근거

**ASD-STE100 Issue 9**(항공우주 기술문서 국제 규격, 434쪽 원문 확인)는 또렷의 규칙과 직접
대응하는 조항을 갖는다:

- **Rule 1.11** "Do not use different technical nouns for the same item" = **TERM101**
- **Rule 9.4** "always use a consistent style" = **저장소 수준 일관성**
- **Rule 2.1** 복합명사 3단어 이하 — 근거를 명시한다: *"When the connections between words are
  not clear, ambiguity occurs"* + *"in some languages, the main noun comes first"*
- **GR-3** *"If a pronoun can refer to one or more nouns in a text, it can cause ambiguity…
  replace the pronoun with the word that it refers to."* / **GR-4** 지시사 'this'가 둘 이상을
  가리킬 수 있으면 문맥을 다시 제시 → **REF101의 규범적 근거**

**결정적 공백**: 커버리지를 공개한 STE 체커 벤더 둘 다 **GR-3(대명사 모호성)을 미구현**이고,
**Congree는 Rule 9.4를 "기계 검사 불가"로 분류**한다(*"does not pertain to the text composition
process. Instead, it includes requirements for terminology work"*). 또렷은 정확히 이 미구현
지대에 있다.

**파서 기반 통제언어의 교훈** (Boeing BSEC, Caterpillar CTE, KANT, ACE):

- **어휘 통제가 문법 통제를 4:1로 이긴다.** KANT의 ablation(COLING-94): 일반 어휘+문법 =
  문장당 파스 **27.0**, **어휘만 제약 → 1.7**, 문법만 제약 → 8.4.
  → **`terms.yaml`·심벌 테이블 투자가 REF101 규칙 정교화보다 효율적일 수 있다**는,
  또렷이 실험으로 검증 가능한 가설
- **다의어는 금지가 아니라 관리 대상.** Caterpillar는 1,000개 이상 용어가 진짜로 복수 의미를
  요구함을 발견하고 **subdomain code**로 풀었다 → TERM102에 **도메인 필드가 필수**라는 직접 근거
- **두 실패 모드**: Boeing의 "weird parses"(관대한 문법은 늘 *어떤* 파스를 찾아 no-parse 신호를
  죽인다), KANT의 **silent repair**(합법 해석이 하나면 그것으로 통과시켜 찾으려던 모호성을 은폐).
  → **또렷이 후보와 점수를 모두 노출하고 하나로 확정하지 않는 것이 이 둘에 대한 올바른 방어다**
- **주장 범위**: BSEC은 350룰 GPSG 완전 모호성 파서로도 **precision 79%**였다.
  "선행사를 확정한다"가 아니라 "확정이 어려운 지점을 표시한다"가 문헌적으로 정당한 선이다
- Sowa(CLCE): *"Although computers are not as good as people at resolving ambiguities,
  **they are much better than people at detecting ambiguities**."*

**미 연방 plain language 지침**(아카이브 확인)도 독립적으로 같은 규칙을 갖는다 —
`use-the-same-terms-consistently`(*"Using a different term may cause the reader to wonder if
you're referring to the same group"*), `avoid-noun-strings`(**명사 3개 초과 금지**),
`place-words-carefully`(*"Sloppy word placement can cause ambiguity"*).
→ **명사 나열 3개 상한은 STE와 미 연방 지침 양쪽에서 독립적으로 나온다 — 신규 룰 근거가 이중이다.**

**주의**: 영어 가독성 공식(Flesch-Kincaid 등)은 *단어당 음절수*·*문장당 단어수*의 함수인데
한국어는 두 분모가 모두 부정의다(어절 경계는 띄어쓰기 관행, 조사·어미 교착, 음절 수와 난이도
무상관 — 2음절 한자어가 4음절 고유어보다 어렵다). **이식하지 말 것.** `textstat` 지원 언어에도
CJK가 없다.

## 5. 포지셔닝 교정 — 무엇을 주장할 수 있고 무엇을 접어야 하나

### 접어야 할 주장

| 기존 주장 | 문제 | 교정 |
|---|---|---|
| "지시 대상 정답 맞히기가 아닌 **해석 위험 탐지**"를 신규성 3가지 중 하나로 제시 | **가장 심각한 과대주장.** 패러다임(Chantree 2006)도 기제(Lappin 1994, Ezzini 2022)도 선점됨 | 신규성 목록에서 **제외**하고 "확립된 nocuous ambiguity 패러다임의 한국어 적용"으로 강등 |
| 대조군을 한국어 coref 연구 3편으로 설정 | 진짜 대조군은 영어 RE 모호성 문헌이고 거기서 또렷은 **후발주자** | 대조군을 nocuous ambiguity 계보로 교체, 차별점을 "탐지 vs 해소"가 아니라 **"한국어 / 비ML / 저장소 단위"** 로 재설정 |
| "요구사항 문서 모호성을 검사하는 공개 연구·엔진을 찾지 못함" | QuARS·SREE·RETA·TAPHSIR이 정확히 그것을 한다. 한국어에도 KIPS 2010이 있다 | **"한국어 한정"** 임을 명시하고 영어 도구군·KIPS 2010을 인용한 뒤 차이를 기술 |
| 모호성 유형 무정의 | 범위 불명확으로 반박에 취약 | Berry & Kamsties의 **pragmatic referential ambiguity**로 못박고 **generality 배제**를 명시 |
| threshold 0.2를 "시드 recall 절벽"으로 정당화 | 선행연구는 τ를 **학습셋에서 스윕해 튜닝**한다. 시드 통과는 튜닝이 아니다 | 다중 τ 스윕 곡선으로 보고(SemEval T16의 60/70/80%, Yang의 0.5~1.0) |

### 정당하게 주장할 수 있는 것

1. **한국어 적용** — nocuous ambiguity 계보는 전부 영어이고 한국어 쪽은 resolution 일색이다.
   특히 **조사(이/가/을/를)로 문법역이 표면화되는 한국어에서 role 자질이 영어보다 싸고 정확하다**는
   것은 언어학적으로 유의미한 논점이다
2. **결정론적·비ML 구현** — nocuity 판정은 Chantree 이래 전부 ML(Naive Bayes → SpanBERT)이었다.
   어휘 전용 결정론 도구 SREE는 **후보 랭킹을 아예 하지 않는다**. "랭킹은 하되 ML은 안 쓴다"는
   조합은 확인된 선행연구에 없다
3. **저장소(cross-document) 단위** — 선행 도구는 전부 단일 문서 단위이며 **아키텍처가 그것을
   금지한다**(§4). Acrolinx만이 코퍼스 집행을 하는데 상용·비공개·compile-and-deploy이고
   인라인 억제조차 없다. TERM 심벌 테이블과 REF101을 같은 IR 위에 얹은 구성은 선례가 없다
3-1. **발견과 집행의 통합** — TERM103(발견)+TERM101/104(집행)은 산업에서 분리된 두 제품
   (Fodina TermCatch = 오프라인 발견, Acrolinx = 온라인 집행)을 **하나의 CI 도구로 합친 것**이다
4. **한국어 기술문서 평가 데이터** — ReqEval(200문장)에 대응하는 한국어 자원이 없다
5. **TERM102(정의 충돌)** — lint 규칙 구현 선례가 없고 학술적으로도 2025년에야 정식화

### 반드시 인용할 문헌 (우선순위순)

1. Yang, de Roeck, Gervasi, Willis, Nuseibeh (2011), *REJ* 16(3):163–189 — **과제 정의가 동일**
2. Chantree, Nuseibeh, de Roeck, Willis (2006), RE'06 — nocuous ambiguity 원전
3. Ezzini, Abualhaija, Arora, Sabetzadeh (2022), ICSE — SOTA, θ_δ 격차 임계
4. Lappin & Leass (1994), *CL* 20(4) — salience 가중합 + salience difference threshold
5. Grosz, Joshi, Weinstein (1995), *CL* 21(2) — role 자질의 이론적 근거
6. Hobbs (1978), *Lingua* 44 — 거리·순서 베이스라인
7. Berry, Gacitua, Sawyer, Tjong (2012), REFSQ — 비LLM 결정론 설계의 정당화
8. Berry & Kamsties (2004) — 모호성 유형 범위 확정
9. Abualhaija 외 (2020), ReqEval — 벤치마크 설계 템플릿
10. Kim, Lee, Jung, Choi (2023), ACL Industry — 한국어 모호성 탐지 유일 선례 + ADR/MDR
11. Liu 외 (2023), EMNLP — LLM의 모호성 모델링 실패 실증
12. Nie, Zhou, Bansal (2020), EMNLP — 판정 분포 보존 근거
13. Levesque 외 (2012), KR — 대비용(인간에게 모호하지 않은 케이스)
14. 한국어 요구사항 문서 대용어 해소 (2010), KIPS-B — 국내 최근접 선행
15. Tjong & Berry (2013), SREE — `baseline-naive-ref`의 실재 대응물
16. Frantzi, Ananiadou & Mima (2000) — C-value/NC-value (TERM103 개선 경로)
17. KR100798752B1 특허 — 부산대 검사기 메커니즘 근거

## 6. 이번 조사로 즉시 반영한 것 (2026-07-29)

| 항목 | 근거 |
|---|---|
| `TermAlias.status`(admitted/deprecated) | ISO 704 · TBX `administrativeStatus` · SKOS · Acrolinx |
| 어절 경계 매칭 | Kiwi 복합명사 분해로 '세트'가 '데이터세트' 안에서 매칭되던 오탐 |
| 문법역 다단계(주격 1.0 > 목적격 0.7 > 기타 조사 0.5 > 무조사 0.3) | Centering의 SUBJECT>OBJECT>OTHER, Lappin & Leass RAP 가중치 |
| `min_top_score`(θ_α) | Ezzini 외 (ICSE 2022) — 격차만 보면 후보가 전부 약할 때도 침묵하지 않는 문제 |
| 인라인 억제 프라그마 | prh `prh:disable` · Vale `vale off` · alex(노드 스코프). **생태계 전부 갖췄고 또렷만 없던 CI 도입 차단 요인** |
| 진단 근거 분해(`--explain`) | Gleich 외 (REFSQ 2010) — 결정론적 가중합이라 분해가 자명한 것이 ML 대비 우위 |
| 인라인 코드 → 라틴 더미 치환 | LTeX+ `dummy`. 공백으로 지우면 뒤따르는 조사가 고아가 되어 문법역이 어긋난다 |
| **주제 표지(은/는)를 현저성 최상위로** | 한국어 고유 신호 — 은/는(JX)과 이/가(JKS)는 형태소가 다르다. 영어 Centering이 주제를 추론해야 하는 것과 대비 |
| **TERM105 표기 변이 자동 발견** (opt-in) | RedPen 읽기 정규화의 한국어 자소판. TERM100/101이 사전 선언에 의존하는 구조적 공백을 메운다 |

### TERM105 실측과 한계 (정직한 기록)

자소 편집거리 기반 변이 발견을 fe-news(15,921줄)에 돌리며 필터를 단계적으로 좁혔다:

| 단계 | 발화 수 | 추가한 필터 |
|---|---|---|
| 초기 (비율 0.25만) | **4,042** | — |
| +음절 하한 3, 절대거리 2 | 682 | 2음절 한자어('가지/가치')가 노이즈 최대 원인 |
| +구두점·파생접미사 스트립 | 400 | `제공하며,`의 쉼표가 어미 스트립을 막고 있었음 |
| +빈도 비대칭 | 274 | 표기 변이는 소수 이형태 |
| +서술격 조사·용언 어절 배제 | **156** | 활용형끼리 자소가 가까움 |

**표본 30건 판정(seed 42)에서 드러난 핵심**: 정밀도가 변이 유형별로 극명하게 갈린다.

- **띄어쓰기 변이(자소 거리 0): 6/6 정답** — '오픈 소스/오픈소스', '고려 사항/고려사항',
  '진입 장벽/진입장벽' 등. 사실상 확정적이다
- **철자 변이(거리 ≥1): 약 20%** — '랜더링/렌더링'·'대체재/대체제'·'프런트엔드/프론트엔드'는
  정확히 잡지만, '스피너/스피커'·'커넥터/컬렉터'·'브라우저/브라우징'처럼 자소가 가까운
  별개 어휘를 구별하지 못한다

**따라서 자소 거리만으로는 한국어 표기 변이와 어휘 대립을 가를 수 없다**는 것이 이번 실측의
결론이다. 진단 메시지에 두 유형을 구분해 표기하고, 규칙은 `info` + opt-in으로 둔다.
문헌 맥락상 ATE조차 F1 0.5~0.69가 상한(ACTER)이므로 제안 규칙으로서는 수용 가능한
동작점이지만, 철자 변이 쪽 정밀도 개선(외래어 판별 신호, 문맥 유사도)은 round-4 과제다.

**외부 코퍼스 영향** (반영 전 → 후, REF101 발화 수):
fe-news 199→**195** · ko.react.dev 1,045→**984** · k8s ko 2,105→**2,120**.
시드 F1 0.750·픽스처 golden 6세트 불변.

k8s만 증가한 것은 회귀가 아니라 **파싱 충실도 개선의 귀결**로 해석한다 — 코드 밀집
레퍼런스 문서에서 종전에는 코드를 공백으로 지워 뒤 조사가 오분석되며 지시어 자체를
놓치던 문장들이, 이제 구조가 살아 정상적으로 후보 랭킹을 타기 때문이다. (다만 이 해석은
표본 판정으로 확인하지 않았으므로 round-4의 재판정 대상이다.)

## 7. 아직 반영하지 않은 제안 (round-4 백로그)

**평가 방법론 (가장 가치 큼, large)** — REF101에는 **정답 라벨이 하나도 없다.** 선행연구 규모:
지시표현 150~200건, 인스턴스당 판정자 10인 이상, certainty = 후보 선택 수 / 전체 판정 수,
**τ ∈ {0.5…1.0} 스윕**해 P/R/**F2** 보고(Yang·Ezzini 모두 F2). 저비용 대안은 ReqEval 방식
(어노테이터 5인, "1인이라도 모호하다면 모호"). **판정은 집계하지 말고 분포로 공개**(ChaosNLI, Plank) —
한국어에 비집계 coref 라벨이 없으므로 이것만으로 독립적 기여가 된다.

**베이스라인·지표 (small~medium)** — "전부 nocuous" 베이스라인 추가(R=1.0 고정), 주지표를 F1→**F2**로,
**ADR/MDR** 채택. 문헌 기준 동작점: Ezzini P≈60%/R=100%, SREE P 66~85%/R 100% —
**precision 60%대가 이 과제의 정상 동작점**이며 오탐을 결함으로 취급할 이유가 없다.

**누락된 salience 자질 (medium)** — 가성비순: ① **centering(문단 내 빈도)** — TERM 심벌 테이블이
이미 빈도를 갖고 있어 거의 공짜 ② **section heading 포함**(마크다운은 heading이 IR에 있음)
③ definiteness 대응물(관형사·한정 수식) ④ syntactic parallelism(조사 기반이라 쉬움)
⑤ head noun emphasis / 내포 감점. 경고: Yang 실측상 **개별 자질 기여도는 최대 3.7%p**이므로
조합 효과로 평가하고 **ablation을 반드시 함께** 돌려야 한다.

**같은 문장 후보 포함 (medium)** — 현재 window는 현재 문장을 제외하는데, Lappin의 sentence recency는
**최고 가중치 100**이고 Yang H14도 같은 문장을 선호한다. **선행연구 전체와 반대 방향**이므로 근거를
대거나 고쳐야 한다.

**recency–distance 공선성 (small)** — `distance = 1/(1+dist_idx)`가 dist_idx=0에서 1.0이고
`recency`도 1.0이라 직전 문장에서 완전히 겹친다. **실질 자질이 3개**라는 뜻이므로 문서화하거나
재정의해야 한다.

**진단 설명 가능성 (medium)** — Gleich 외(2010)의 요구조건. **어떤 자질이 격차를 좁혔는지** 분해 출력.
결정론적 가중합이라 분해가 자명한 것이 ML 대비 실질 우위이므로 논문에서 강조할 지점

**용어 쪽 (medium)** — TERM103을 C-value + weirdness로 교체(리포에 이미 외부 코퍼스 3종이 있어
대조 코퍼스 비용 0), TERM102 정의 패턴 확대(`~를 뜻한다/가리킨다/의미한다`, 괄호 동격, heading 직후
문단) + 유사도 기반 충돌 판정, 사전에 concept id·domain·definition_source 추가,
인라인 프라그마(`<!-- ttoryeot:disable TERM104 -->`), TERM104 auto-fix

**알려진 한계 명시 (small)** — 영형 조응 미지원(한국어 구어 대명사의 약 57%가 영형 주어),
한국어 coref 상한 F1 66.9, `suppress_heads`가 배제하는 것은 모호성이 아니라 **generality**임을
Berry & Kamsties로 정당화

**§4 조사에서 나온 추가 반영 후보 (우선순위순)**

1. **TERM101을 다수결 정본 제안으로 (medium)** — LanguageTool `ConsistencyPatternRuleTransformer`.
   현재 또렷은 "다른 문서의 표기와 불일치"로 **양쪽을 대칭 보고**한다. 저장소 전역 빈도로
   **최빈 표기를 정본 제안**하면 (a) 진단 수 급감 (b) 수정 방향 명확 (c) `terms.yaml`에 canonical이
   없어도 동작. 동점 시 전량 플래그. **또렷은 저장소 스코프라 표본이 커서 LanguageTool보다 유리하다**
2. **명사 연쇄 모호성 규칙 AMB101 (medium, 신규 룰)** — STE Rule 2.1 + 미 연방
   `avoid-noun-strings`가 **독립적으로 3개 상한**을 규정. 한국어는 핵어 후치 + 조사 생략으로
   더 심하고("주문 데이터 파이프라인 배치 처리 설정"), Kiwi 명사구 IR이 이미 있다.
   **근거가 이중이고 비용이 낮은 최우선 신규 룰**
3. **인라인 코드를 공백이 아니라 더미 명사로 (small)** — LTeX+의 `dummy` 치환.
   삭제하면 문장 구조가 깨지고 남기면 오탐이 나는데, 더미 명사면 **구조가 살아 REF101 후보
   랭킹이 안정된다**. 현재 또렷은 공백 치환이라 구조가 깨지는 쪽
4. **사전 없는 표기 변이 발견 (medium)** — RedPen `JapaneseExpressionVariationValidator`의
   읽기 정규화 + Levenshtein(`min_ratio 0.3`, `max_ignore_len 3`). 한국어 외래어 변이는
   자소 분해 후 편집거리가 작다. **TERM100/101이 사전 선언에 의존하는 구조적 공백을 메운다**
5. **기계 판독 lint 출력 (small)** — 현재 JSON은 벤치에만 있다. Vale(JSON+템플릿→reviewdog),
   textlint(포매터 11종) 대비 결손이며 **reviewdog/GitHub Annotations 연동이 도입 경로**.
   단 **SARIF는 불필요**(생태계 어디에도 없음)
6. **진단 모델을 다중 스팬 + 안정 해시로 (medium)** — Acrolinx. TERM101("이 문서의 X ↔ 저 문서의
   Y")과 REF101(지시어 + 후보들)은 본질적으로 **비연속 다중 스팬**이다. 안정 해시는 baseline
   워크플로("기존 이슈는 눈감고 신규만 차단")를 공짜로 만든다
7. **사전에 `specs:` 내장 테스트 (small)** — prh. `terms.yaml` 항목에 테스트케이스를 넣으면
   사전 회귀를 벤치 하네스로 자동 검증할 수 있다
8. **어휘 우선 가설 검증 (실험)** — KANT ablation(어휘만 27.0→1.7 vs 문법만 8.4)에 근거해,
   **사전 확충 vs REF101 규칙 정교화** 중 어느 쪽이 정밀도를 더 올리는지 스윕으로 비교

## 조사 한계

- **페이월/차단으로 초록만 확인**: Chantree RE'06(기제는 동일 저자군 COLING 2010 전문으로 교차확인),
  Berry & Kamsties 2004(택소노미는 Ambiguity Handbook 전문으로 교차확인), Berry 2012 본문(저자
  슬라이드 60p 전문으로 대체 확인), SREE REFSQ 2013(수치는 Tjong 박사논문 전문), Hobbs 1978
  (명세·성능은 Lappin & Leass §6.1로 교차확인), ACM TALIP 2003, Springer LNCS 2358, K-NCT(IEEE)
- **DNS 실패**: `speller.cs.pusan.ac.kr`, `docs.bareun.ai` — 부산대 원 서비스의 공식 안내·약관을
  원본에서 확인하지 못했다
- **마케팅만 확인**: 바른AI(bareun)의 "딥러닝 기반·형태소 태깅 99.6%"는 자사 문구, 독립 검증 없음.
  네이버·카카오 검사기 내부 메커니즘은 공개 자료 없음
- **의뢰 전제 정정 1건**: RETA는 "REquirements Textual Ambiguity"가 아니라 **REquirements Template
  Analyzer**(Arora 외, TSE 2015)이며 Gleich 외와 무관하다
- **인용 혼동 주의**: GAP의 66.9 F1(snippet-context PARALLELISM)과 Park 외 2020 한국어 coref의
  CoNLL F1 66.9는 **무관한 숫자**다
