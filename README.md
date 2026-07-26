# 또렷 (ttoryeot)

한국어 기술 문서를 코드처럼 정적 분석하는 엔진. 컴파일러 프런트엔드의 파싱·중간 표현·심벌
테이블·참조 해석 구조를 자연어 문서에 적용한다.

> 기존 한국어 문법 교정 시스템은 문장 수준의 오류 수정에, 최근 AI 스타일 검사기는 LLM 기반의
> 전체 문서 검토에 집중한다. 이 프로젝트는 한국어 기술 문서 저장소를 파싱하여 용어 정의·참조·
> 문서 간 일관성을 인덱싱하고, 모호한 참조와 정의 충돌을 재현 가능한 진단으로 제공한다.

**연구 질문:** 한국어 기술 문서의 용어 불일치와 참조 모호성을, LLM 없이 결정적 규칙과 구조
분석만으로 얼마나 정확하게(낮은 오탐으로) 탐지할 수 있는가?

## 예시

```
$ ttoryeot lint docs/ --terms terms.yaml

docs/deploy.md:3 TERM101 '데이터셋'는 다른 문서의 '데이터세트' 표기와 불일치합니다.
docs/pipeline.md:3 TERM102 '데이터세트'의 정의가 다른 문서의 정의와 충돌합니다.
docs/pipeline.md:7 REF101 '해당 데이터'의 지시 대상이 불명확합니다.
    후보 0.75  주문 테이블
    후보 0.57  사용자 테이블
```

## 구조

```
Markdown 저장소
   ↓ parse_blocks     markdown-it-py, 원문 오프셋 보존
   ↓ lowering         Kiwi 형태소 분석 → Document IR (문장·토큰·명사구·지시어)
   ↓ analysis passes  용어 심벌 테이블(TERM1xx) · 지시어 해석 위험(REF101)
   ↓ diagnostics      파일·줄 위치 + 후보·근거가 달린 재현 가능한 진단
```

- IR·벤치마크·진단 스키마는 Pydantic으로 정의하고 JSON Schema로 export (`schemas/`,
  `benchmark/data/*.schema.json`) — 언어 중립, 추후 타 언어 구현체가 소비 가능
- 평가 우선(evaluation-first): 벤치마크와 채점 하네스(순서 불변 최대 이분 매칭 P/R/F1)가
  엔진과 함께 개발됨. 시드 데이터 기준 엔진 F1 0.750 vs 정규식·치환·나이브 베이스라인
  0.286~0.333

## 시작하기

```bash
uv sync
uv run pytest -q
uv run ttoryeot lint corpus/fixtures/data-platform --terms corpus/fixtures/data-platform/terms.yaml
uv run ttoryeot bench run --data benchmark/data/sample-sentences.jsonl --engine ttoryeot
uv run ttoryeot bench report
```

## 문서

- [진행 상태·백로그 (핸드오프)](docs/handoff/2026-07-27-round1-status.md)
- [설계 스펙](docs/superpowers/specs/2026-07-26-research-core-design.md)
- [구현 플랜](docs/superpowers/plans/2026-07-26-research-core.md)
- [관련 연구 조사](docs/research/2026-07-26-related-work.md)
