# 또렷 (ttoryeot)

**한국어 기술 문서 저장소를 위한 시맨틱 린터.** 이름은 '흐리지 않고 분명하다'는 뜻의
'또렷하다'에서 왔다 — 문서의 용어와 참조를 또렷하게 만드는 도구다.

컴파일러 프런트엔드가 코드를 다루듯 문서를 다룬다. 마크다운을 원문 오프셋이 보존된
중간 표현(IR)으로 낮추고, Kiwi 형태소 분석 위에 용어 심벌 테이블과 지시어 해석을 얹어,
문서 하나가 아니라 저장소 전체를 검사한다. 잡는 것은 맞춤법·문법이 아니라 **문서 사이의
의미 일관성**이다: 같은 개념의 표기 혼용, 같은 용어의 정의 충돌, 지시 대상이 불명확한
참조. 모든 진단은 결정적 규칙에서 나오므로 같은 입력에 항상 같은 결과로 재현되고,
파일·줄 위치와 후보·근거가 함께 달린다.

> 기존 한국어 문법 교정 시스템은 문장 수준의 오류 수정에, 최근 AI 스타일 검사기는 LLM 기반의
> 전체 문서 검토에 집중한다. 또렷은 그 사이 — 저장소 수준의 용어·참조 일관성 — 을 겨냥해,
> 용어 정의·참조·문서 간 일관성을 인덱싱하고 재현 가능한 진단으로 제공한다.

참조 모호성 진단(REF101)은 요구공학의 **유해 모호성(nocuous ambiguity)** 패러다임
— 지시 대상을 맞히는 대신 독자 간 해석이 갈릴 위험만 경고한다 — 을 한국어에 적용한 것이다
(Chantree 외 2006, Yang 외 2011, Ezzini 외 2022). 또렷 고유의 기여는 **한국어 적용 ·
비ML 결정론 구현 · 저장소 단위 분석 · 한국어 기술 문서 벤치마크**이며, 근거와 선행 연구
대비 위치는 [검증판 관련 연구](docs/research/2026-07-29-related-work-verified.md)에 정리했다.

**연구 질문:** 한국어 기술 문서의 용어 불일치와 참조 모호성을, LLM 없이 결정적 규칙과 구조
분석만으로 얼마나 정확하게(낮은 오탐으로) 탐지할 수 있는가?

## 예시

```
$ ttoryeot lint docs/ --terms terms.yaml

docs/deploy.md:3 TERM101 '데이터셋'(전체 1회)은(는) 다른 문서의 '데이터세트'(전체 1회) 표기와 불일치합니다.
docs/pipeline.md:3 TERM102 '데이터세트'의 정의가 다른 문서의 정의와 충돌합니다.
docs/pipeline.md:7 REF101 '해당 데이터'의 지시 대상이 불명확합니다.
    후보 0.68  데이터세트
    후보 0.51  주문 테이블
    후보 0.47  사용자 테이블
```

## 구조

```
Markdown 저장소
   ↓ parse_blocks     markdown-it-py, 원문 오프셋 보존
   ↓ lowering         Kiwi 형태소 분석 → Document IR (문장·토큰·명사구·지시어)
   ↓ analysis passes  용어 심벌 테이블(TERM1xx) · 지시어 해석 위험(REF101) · 명사 연쇄(AMB101)
   ↓ diagnostics      파일·줄 위치 + 후보·근거가 달린 재현 가능한 진단
```

- IR·벤치마크·진단 스키마는 Pydantic으로 정의하고 JSON Schema로 export (`schemas/`,
  `benchmark/data/*.schema.json`) — 언어 중립, 추후 타 언어 구현체가 소비 가능
- 평가 우선(evaluation-first): 벤치마크와 채점 하네스(순서 불변 최대 이분 매칭 P/R/F1)가
  엔진과 함께 개발됨. 시드 데이터 기준 엔진 F1 0.750 vs 정규식·치환·나이브 베이스라인
  0.286~0.333. 실제 조사표 기반 278항목 벤치는
  [1차 정량 실험](docs/research/2026-07-28-round1-quantitative.md)(엔진은 표적 밖에서
  오탐 0), 공개 한국어 문서 13.6만 줄 오탐 실측은
  [측정 리포트](docs/research/2026-07-28-external-corpus-fp.md) 참조 — 가중치·임계값은
  `src/ttoryeot/config/default.yaml`에서 튜닝 가능(`lint --config`)

## 오탐 억제

문서 안에서 진단을 끌 수 있다 (규칙 이름을 생략하면 전체 규칙):

```markdown
<!-- ttoryeot:disable TERM104 -->            문서 전체
<!-- ttoryeot:disable-next-line REF101 -->   다음 줄만
```

## 시작하기

```bash
uv sync
uv run pytest -q
uv run ttoryeot lint corpus/fixtures/data-platform --terms corpus/fixtures/data-platform/terms.yaml
uv run ttoryeot lint <문서루트> --terms terms.yaml --explain   # 진단 근거(자질별 점수)까지
uv run ttoryeot bench run --data benchmark/data/sample-sentences.jsonl --engine ttoryeot
uv run ttoryeot bench report
```

사전에 아직 없는 표기 혼용은 자소 거리로 발견할 수 있다 (`terms.suggest_variants: true`,
기본 off — 띄어쓰기 변이는 거의 확정적이고 철자 변이는 제안 수준이다):

```
docs/guide.md:12 TERM105 띄어쓰기 변이 후보입니다: '오픈 소스'(2회) / '오픈소스'(84회) …
docs/intro.md:5  TERM105 철자 변이 후보입니다: '랜더링'(4회) / '렌더링'(205회) …
```

용어 사전(`terms.yaml`)의 별칭은 표기 상태를 가질 수 있다 — ISO 704·TBX의
`preferred / admitted / deprecated` 축에 대응한다:

```yaml
terms:
  - canonical: 데이터세트
    aliases:
      - 데이터셋                                    # 문자열 = deprecated
      - {surface: 데이터 세트, status: admitted}    # 혼용 탐지는 하되 비권장 경고는 안 함
```

## 문서

- **[아키텍처·규칙 레퍼런스 — 어떻게 작동하나](docs/architecture.md)**
- [세션 요약 — 무엇이 구현됐나](docs/handoff/2026-07-28-session-summary.md)
- [진행 상태·백로그 (핸드오프)](docs/handoff/2026-07-28-round2-backlog-status.md)
- [1차 정량 실험 (조사표 벤치마크)](docs/research/2026-07-28-round1-quantitative.md)
- [관련 연구 (검증판) · 선행연구 대비 위치](docs/research/2026-07-29-related-work-verified.md)
- [REF101 평가 프로토콜 (판정 분포·τ 스윕·F2)](docs/research/2026-07-29-ref101-evaluation-protocol.md)
- [REF101 튜닝 챕터](docs/research/2026-07-28-ref101-tuning.md)
- [잔존 발화 재판정·억제 비용·장르 일반화](docs/research/2026-07-28-round3-residual-judgment.md)
- [외부 코퍼스 REF101 발화율 측정](docs/research/2026-07-28-external-corpus-fp.md)
- [설계 스펙](docs/superpowers/specs/2026-07-26-research-core-design.md)
- [구현 플랜](docs/superpowers/plans/2026-07-26-research-core.md)
- [관련 연구 조사](docs/research/2026-07-26-related-work.md)
