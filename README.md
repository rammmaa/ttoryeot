# ttoryeot (또렷)

> Compiler-inspired static analysis for Korean technical documentation.

ttoryeot은 한국어 기술 문서의 용어 불일치와 모호한 지시 관계를 검출하는 정적 분석 도구입니다.

## Motivation

LLM을 활용하면 기술 문서를 쉽게 작성할 수 있지만, 생성된 문장이 항상 읽기 좋은 것은 아닙니다. 직역투의 표현이나 불명확한 지시 관계, 일관되지 않은 용어 사용은 문법적으로 올바른 문장에서도 독자의 이해를 방해할 수 있습니다.

이 프로젝트는 이러한 문제를 단순한 맞춤법 검사가 아닌 정적 분석의 관점에서 접근합니다.

컴파일러처럼 문서를 파싱하고 중간 표현(IR)을 구성한 뒤, 명시적인 분석 규칙을 적용하여 검토할 만한 문제를 진단합니다.

AI가 작성한 글인지 판별하는 도구는 아닙니다. 자연어 문서의 어떤 품질 문제를 정적 분석으로 검출할 수 있는지 탐색하는 실험적 프로젝트입니다.

## Features

| Rule | Description |
| --- | --- |
| TERM100 | 동일 문서 내 용어 표기 혼용 |
| TERM101 | 문서 간 용어 표기 불일치 |
| TERM102 | 동일 용어의 정의 불일치 후보 |
| REF101 | 지시 대상이 모호할 가능성이 있는 표현 |

일부 규칙은 휴리스틱 기반이며, 진단 결과가 반드시 실제 오류를 의미하지는 않습니다.

## Architecture

```text
Markdown Documents
       |
       v
Parsing & Morphological Analysis (Kiwi)
       |
       v
Intermediate Representation (WorkspaceIR)
       |
       +-- Terminology Analysis
       |
       +-- Reference Analysis
       |
       v
Diagnostics (location, rule, candidates)
```

문서 파싱, 중간 표현, 분석기, 진단 출력을 분리하여 새로운 분석 규칙을 독립적으로 구현하고 테스트할 수 있도록 구성했습니다.

## Getting Started

Python 3.12 이상이 필요합니다.

```bash
python -m pip install -e .
ttoryeot --help
```

Markdown 문서 디렉터리를 검사합니다.

```bash
ttoryeot lint ./docs --terms ./terms.yaml
```

용어 사전은 다음 형식을 사용합니다.

```yaml
terms:
  - canonical: 데이터세트
    aliases:
      - 데이터셋
      - 데이터 세트
```

진단 결과에는 파일 경로, 줄 번호, 규칙 ID 및 설명이 포함됩니다. 진단이 발견되면 lint 명령은 종료 코드 1을 반환합니다.

## Evaluation & Testing

```bash
python -m pip install pytest
python -m pytest -q
```

단위 테스트 외에도 예상 진단과 오탐을 함께 확인하는 Golden Test를 포함합니다.

벤치마크 모듈에서는 규칙별 Precision, Recall, F1을 계산하며, 예측과 정답 span의 매칭에는 최대 이분 매칭을 사용합니다.

평가용 데이터셋과 정량 결과는 별도의 검증이 필요하며, 현재 공개 저장소에 포함되어 있지 않습니다.

## Limitations

- 한국어 전반의 문법 오류를 검출하지 않습니다.
- 지시 관계 분석은 휴리스틱에 의존하므로 오탐이 발생할 수 있습니다.
- 정의 문구의 불일치가 반드시 의미적 모순을 뜻하지는 않습니다.
- LLM 생성 여부나 문서의 사실성을 판별하지 않습니다.

## Status

Experimental project.
