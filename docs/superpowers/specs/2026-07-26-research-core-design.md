# 또렷(ttoryeot) 연구 코어 1차 설계

- 날짜: 2026-07-26
- 상태: 승인됨 (브레인스토밍 세션에서 섹션별 승인)
- 관련 문서: [관련 연구 조사](../../research/2026-07-26-related-work.md)

## 1. 배경과 연구 질문

또렷은 한국어 기술 문서를 코드처럼 정적 분석하는 엔진이다. 컴파일러 프런트엔드의
파싱·중간 표현·심벌 테이블·참조 해석 구조를 자연어 문서에 적용한다.

**연구 질문:**

> 한국어 기술 문서의 용어 불일치와 참조 모호성을, LLM 없이 결정적 규칙과 구조 분석만으로
> 얼마나 정확하게(낮은 오탐으로) 탐지할 수 있는가?

**포지셔닝** (2026-07-29 심층 재조사로 교정 —
[검증판 관련 연구](../../research/2026-07-29-related-work-verified.md) §5 참조):

> 기존 한국어 문법 교정 시스템은 문장 수준의 오류 수정에, 최근 AI 스타일 검사기는 LLM 기반의
> 전체 문서 검토에 집중한다. 이 프로젝트는 한국어 기술 문서 저장소를 파싱하여 용어 정의·참조·
> 문서 간 일관성을 인덱싱하고, 모호한 참조와 정의 충돌을 재현 가능한 진단으로 제공한다.

**⚠ 초판의 신규성 주장 중 하나는 철회한다.** "지시 대상의 '해석 위험' 탐지"는 요구공학의
**nocuous ambiguity** 계보(Chantree 외 2006, Yang 외 2011, Ezzini 외 ICSE 2022)가 이미 소유한
패러다임이고, 1·2위 점수차 임계라는 기제도 Lappin & Leass(1994)의 salience difference
threshold와 같은 연산이다. REF101은 그 패러다임의 **한국어 적용**으로 기술한다.

정당하게 주장할 수 있는 신규성은 넷이다:

1. **한국어 적용** — nocuous ambiguity 계보는 전부 영어, 한국어 쪽은 resolution 일색.
   조사로 문법역이 표면화되는 한국어에서 role 자질이 영어보다 싸고 정확하다는 논점
2. **결정론적·비ML 구현** — 선행 nocuity 판정은 전부 ML. 어휘 전용 결정론 도구(SREE)는
   후보 랭킹을 하지 않는다. "랭킹은 하되 ML은 안 쓴다"는 조합에 선례가 없다
3. **저장소 단위** — 선행 도구는 전부 단일 문서 단위
4. **한국어 기술 문서 벤치마크** — ReqEval에 대응하는 한국어 자원이 없다

또한 REF101이 다루는 것은 Berry & Kamsties(2004) 택소노미의 **pragmatic referential
ambiguity**로 한정하고, **generality**(여러 해석에 열려 있으나 결정이 불필요한 경우)는
명시적으로 배제한다 — `reference.suppress_heads`의 discourse 그룹이 그 장치다.

## 2. 1차 라운드 범위

**접근 방식: 평가 우선(evaluation-first).** 벤치마크와 실험 하네스를 먼저 만들고,
IR과 분석기는 벤치마크 점수를 낼 수 있는 최소한부터 키운다. 구현 순서:

1. 벤치마크 스키마 + 조사표 CSV 변환기
2. 베이스라인 + 실험 하네스
3. Document IR + Markdown/Kiwi 파싱 파이프라인
4. 분석 패스 1: 용어 심벌 테이블
5. 분석 패스 2: 지시어 해석 위험
6. 정량 실험 리포트

**완료 기준:** 벤치마크에서 두 분석 패스의 precision/recall을 측정하고 베이스라인
(단순 치환·정규식·나이브 규칙)과 비교한 수치가 담긴 리포트가 나오는 것.

**Non-goals (1차에서 하지 않음):** 자동 수정, LSP/VS Code 확장, 증분 분석, SARIF 출력,
GitHub Action, LLM 재검증 패스, 규칙 DSL 파서(YAML 로딩 수준만), 맞춤법·조사 오류 등
일반 GEC 규칙(기존 연구와 겹치는 영역).

**스택:** Python 3.12 + uv. 형태소 분석은 kiwipiepy. IR·벤치마크·진단 스키마는 Pydantic으로
정의하고 JSON Schema로 export하여 커밋 — 추후 Rust/Go 구현체가 같은 스키마를 소비할 수 있게
언어 중립성을 유지한다.

## 3. 저장소 구조

```
ttoryeot/
├── pyproject.toml          # uv + Python 3.12
├── src/ttoryeot/
│   ├── ir/                 # Document IR — Pydantic 모델, JSON Schema export
│   ├── parsing/            # Markdown → AST → IR lowering (markdown-it-py + Kiwi)
│   ├── analysis/
│   │   ├── base.py         # Analyzer 프로토콜, AnalysisContext
│   │   ├── terms/          # 용어 심벌 테이블 + TERM1xx 규칙
│   │   └── references/     # 지시어 후보 해석 + REF1xx 규칙
│   ├── diagnostics/        # Diagnostic 모델, 콘솔 렌더러
│   ├── bench/              # 실험 하네스, 베이스라인, 리포트 생성
│   └── cli.py              # ttoryeot lint / ttoryeot bench
├── benchmark/
│   ├── raw/                # 조사표 CSV 원본 (기본 git-ignore, 공개 가능 확인 후 커밋)
│   ├── data/               # 변환된 JSONL + JSON Schema + category-map.md
│   └── results/            # 실험 결과 JSON + 리포트 md
├── corpus/
│   ├── fixtures/           # 미니 문서 저장소들 (expected.yaml 포함)
│   └── external/           # 공개 오픈소스 한국어 docs (오탐률 측정용, git-ignore)
├── tests/
└── docs/
    ├── research/
    └── superpowers/specs/
```

**핵심 설계 결정:**

- (a) 모든 공개 스키마는 Pydantic → JSON Schema export를 커밋한다.
- (b) 분석 단위는 Document가 아니라 **Workspace**(문서 저장소)다. 문서 간 용어 충돌이
  1차 범위이므로 처음부터 워크스페이스 단위로 설계한다.

## 4. 벤치마크

성격이 다른 두 트랙으로 나눈다. 문장 하나로 판정 가능한 오류와 저장소 전체를 봐야 하는
오류는 평가 방식이 다르기 때문이다.

### 4.1 트랙 1: 문장 수준 (조사표 기반)

파일: `benchmark/data/sentences.jsonl`. 스키마 예시:

```json
{
  "id": "sent-0042",
  "source": "survey",
  "document_type": "team_blog",
  "context_before": "사용자 테이블과 주문 테이블을 조인합니다.",
  "text": "해당 데이터를 저장합니다.",
  "annotations": [
    {
      "span": [0, 6],
      "category": "ambiguous_reference",
      "severity": "warning",
      "correction": "조인 결과를 저장합니다.",
      "rationale": "선행 후보가 3개로 지시 대상이 불명확",
      "evidence": {"source": "survey", "url": null},
      "confidence": "high"
    }
  ]
}
```

- `annotations: []`인 **정상 문장(negative example)을 반드시 포함**한다. 조사표의 오류
  사례와 짝이 되는 올바른 문장을 넣어 오탐을 측정한다. 목표 비율: 오류:정상 ≥ 1:1.
- `category`는 조사표의 오류 분류를 그대로 쓰되, KAGAS 14유형과의 대응표를
  `benchmark/data/category-map.md`로 문서화한다.
- CSV → JSONL 변환은 `ttoryeot bench convert` 명령으로 제공하고, 결과는 JSON Schema로
  검증한다. 조사표 원본은 스프레드시트/CSV로 존재한다.

### 4.2 트랙 2: 저장소 수준 (픽스처 기반)

`corpus/fixtures/<name>/`에 미니 문서 저장소(glossary 1개 + 본문 4~8개)를 5~10세트
구성한다. 조사표에서 발견한 실제 패턴(데이터셋/데이터세트 혼용 등)을 픽스처로 재구성한다.
각 픽스처에는 정답 주석 `expected.yaml`을 둔다:

```yaml
diagnostics:
  - rule: TERM102        # 용어 정의 충돌
    file: docs/pipeline.md
    line: 52
  - rule: REF101         # 지시 대상 불명확
    file: docs/deploy.md
    line: 17
clean_files:             # 진단이 없어야 하는 파일 (오탐 체크)
  - docs/faq.md
```

### 4.3 지표와 채점 기준

| 지표 | 정의 |
|---|---|
| Precision / Recall / F1 | 규칙별 + 전체, 두 트랙 각각 |
| 오탐/1,000줄 | 공개 오픈소스 한국어 docs(clean 가정 코퍼스)에서 측정 |
| 처리 시간 | 파일 수 대비 (참고용) |

**채점 방식:**

- 트랙 1: 하네스가 각 항목을 `context_before + text`로 구성한 임시 단일 문서로 만들어
  엔진에 입력하고, `text` 범위 안의 진단만 채점한다.
- TP 판정: 진단의 rule id가 annotation의 category에 대응하고(대응표는
  `benchmark/data/category-map.md`에 rule↔category 매핑으로 함께 관리), 진단 위치가
  annotation의 span과 겹치면 TP. category가 맞아도 span이 겹치지 않으면 FP + FN.
- 트랙 2: `expected.yaml`의 (rule, file, line) 완전 일치 기준.

### 4.4 베이스라인

1. 단순 문자열 치환 사전
2. 정규식 규칙
3. 지시어용 나이브 규칙: "해당/이/그 + 명사"면 무조건 경고
4. 또렷 엔진 (IR + 두 분석 패스)

LLM 베이스라인은 2차로 미룬다. 리포트는 `ttoryeot bench report`가 `benchmark/results/`에
마크다운으로 생성한다. 핵심 문장이 "형태소·구조 분석이 정규식 대비 오탐을 N% 줄였다"가
되도록 리포트 구조를 잡는다.

## 5. Document IR과 파싱

```
WorkspaceIR
└── DocumentIR (파일당 1개)
    ├── path, content_hash
    └── blocks: [Heading | Paragraph | ListItem | CodeBlock | BlockQuote]
        └── sentences: [SentenceIR]     # Kiwi 문장 분리
            ├── text, source_range      # 파일·줄·열 (원문 오프셋 보존)
            ├── tokens: [Token]         # Kiwi 형태소 (형태·품사·오프셋)
            ├── noun_phrases: [NounPhrase]
            └── references: [ReferenceExpression]  # '해당 X', '이 X', '그 X', '위 X'
```

파싱 파이프라인: `markdown-it-py`(CommonMark, 블록별 줄 범위 제공) → 코드 블록·인라인
코드를 제외한 텍스트만 Kiwi에 전달 → 원문 오프셋으로 역매핑.

**소스 위치 보존이 이 계층의 제1 요구사항이다.** 진단 위치가 틀리면 도구 신뢰가 무너진다.
IR의 모든 노드는 원문 `(line, col)` 왕복이 가능해야 하며, 이를 property 테스트로 강제한다.

## 6. 분석 패스

### 6.1 Analyzer 인터페이스 (`analysis/base.py`)

```python
class Analyzer(Protocol):
    rule_ids: tuple[str, ...]

    def analyze(
        self, ws: WorkspaceIR, ctx: AnalysisContext
    ) -> Iterable[Diagnostic]: ...
```

`Diagnostic`: rule id, severity, source_range, message, 후보 목록(선택), 근거(선택)를 가진
구조체. 렌더링(콘솔 출력 등)과는 분리한다.

### 6.2 패스 1: 용어 심벌 테이블 (`analysis/terms/`)

용어 사전 YAML(canonical + aliases + 정의 위치)을 로딩하고, 워크스페이스 전체의 용어
occurrence 인덱스를 구축한다.

| 규칙 | 내용 |
|---|---|
| TERM100 | 문서 내 표기 혼용 |
| TERM101 | 문서 간 표기 혼용 |
| TERM102 | 용어 정의 충돌 (같은 용어를 다른 정의로 서술) |
| TERM103 | 사전에 없는 조직 고유 용어 (1차에서는 기본 off) |

v1의 alias 매칭은 사전 명시 + 정규화(공백 제거) 수준으로 한정한다. 자동 클러스터링은
하지 않는다.

### 6.3 패스 2: 지시어 해석 위험 (`analysis/references/`)

ReferenceExpression별로 선행 문장 윈도(같은 섹션 내 최대 N문장, 기본값 N=5, 설정으로
조정)에서 명사구 후보를 추출하고 점수화한다:

```
score = w1·문장 거리 + w2·문법 역할(주어/목적어) + w3·의미 유형 일치
        + w4·최근 언급 + w5·섹션 경계 페널티
```

**1위 후보 확정이 목적이 아니다.** 1위·2위 점수 차가 임계값 미만이면 `REF101`
(지시 대상 불명확)을 후보 목록과 함께 경고한다. 기존 상호참조 연구와의 차이가 바로
이 지점이다 — 정답 맞히기가 아니라 해석 위험 탐지.

가중치·임계값은 하드코딩하지 않고 설정 파일로 분리해 벤치마크로 튜닝한다. 튜닝 과정
자체가 실험 리포트의 한 챕터가 된다.

## 7. 에러 처리

- 파싱에 실패한 문서는 워크스페이스 분석에서 제외하되, 내부 오류 진단(`INT001`)으로
  보고한다. 문서 오류와 도구 오류를 구분해 표시한다.
- 분석기는 어떤 입력에도 크래시하지 않는 것이 계약이다.
- Kiwi 초기화 실패 등 환경 문제는 CLI 레벨에서 명확한 메시지로 처리한다.

## 8. 테스트

1. IR 소스 위치 왕복 property 테스트
2. 분석기별 단위 테스트 (픽스처 문장)
3. 픽스처 저장소 golden 테스트 — `expected.yaml` 대조. 벤치마크 트랙 2와 동일 데이터를
   CI 테스트로 재사용한다.
4. 벤치마크 변환기의 JSON Schema 검증 테스트

## 9. 이후 라운드 (참고, 이번 범위 아님)

2차 이후 후보: LLM 재검증 패스와 하이브리드 비교 실험(ablation), 규칙 DSL 파서, 자동 수정,
SARIF 출력, GitHub Action, LSP·VS Code, 증분 분석, DaleSeo/korean-skills `style-guide`를
LLM 베이스라인으로 추가.
