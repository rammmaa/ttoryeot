# 또렷(ttoryeot) 연구 코어 1차 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 한국어 기술 문서 벤치마크 + 언어 중립 Document IR + 용어 심벌 테이블·지시어 해석 위험 두 분석 패스 + 베이스라인 대비 정량 실험 하네스를 구축한다.

**Architecture:** 평가 우선(evaluation-first). 벤치마크 스키마·변환기·베이스라인·채점 하네스를 먼저 만들고, 그 위에 markdown-it-py + Kiwi 기반 Document IR과 두 분석 패스를 얹어 같은 하네스로 측정한다. 모든 공개 스키마는 Pydantic으로 정의하고 JSON Schema를 커밋한다.

**Tech Stack:** Python 3.12, uv, pydantic v2, markdown-it-py, kiwipiepy, typer, PyYAML, pytest

**Spec:** `docs/superpowers/specs/2026-07-26-research-core-design.md`

## Global Constraints

- Python 3.12, 패키지 관리는 uv (`uv run`, `uv add`)
- src 레이아웃: 모든 엔진 코드는 `src/ttoryeot/` 아래
- 공개 스키마(벤치마크·IR·진단)는 Pydantic 모델 + JSON Schema export를 `benchmark/data/` 또는 `schemas/`에 커밋
- 분석 단위는 Workspace(문서 저장소). Document 단위 API를 만들지 않는다
- 분석기는 어떤 입력에도 크래시하지 않는다 — 파싱 실패 문서는 `INT001` 진단으로 보고하고 제외
- IR의 모든 노드는 원문 `(line, col)` 왕복 가능해야 함 (스펙 §5)
- 지시어 윈도 기본값 N=5, REF101 임계값·가중치는 설정 파일로 분리 (스펙 §6.3)
- 진단 rule id 체계: `TERM1xx`, `REF1xx`, `INT0xx`
- 커밋 메시지는 conventional commits (`feat:`, `test:`, `docs:`, `chore:`)
- `benchmark/raw/`, `corpus/external/`, `benchmark/results/*.json`은 git-ignore

---

### Task 1: 프로젝트 스캐폴딩

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `src/ttoryeot/__init__.py`, `tests/test_smoke.py`

**Interfaces:**
- Produces: 패키지 `ttoryeot` (버전 `0.1.0`), 이후 모든 태스크가 `uv run pytest`로 테스트 실행

- [ ] **Step 1: pyproject.toml 작성**

```toml
[project]
name = "ttoryeot"
version = "0.1.0"
description = "Semantic static analyzer for Korean technical documentation"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.7",
    "markdown-it-py>=3.0",
    "kiwipiepy>=0.18",
    "typer>=0.12",
    "pyyaml>=6.0",
]

[dependency-groups]
dev = ["pytest>=8.0"]

[project.scripts]
ttoryeot = "ttoryeot.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: .gitignore 작성**

```gitignore
__pycache__/
*.egg-info/
.venv/
uv.lock
benchmark/raw/
benchmark/results/*.json
corpus/external/
```

- [ ] **Step 3: 패키지 스켈레톤 + 스모크 테스트 작성**

`src/ttoryeot/__init__.py`:
```python
__version__ = "0.1.0"
```

`tests/test_smoke.py`:
```python
import ttoryeot


def test_version():
    assert ttoryeot.__version__ == "0.1.0"
```

- [ ] **Step 4: 의존성 설치 및 테스트 실행**

Run: `cd /Users/rami.lee/ttoryeot && uv sync && uv run pytest -q`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore src tests
git commit -m "chore: uv 기반 프로젝트 스캐폴딩"
```

---

### Task 2: 벤치마크 스키마 (트랙 1 문장 수준)

**Files:**
- Create: `src/ttoryeot/bench/__init__.py`, `src/ttoryeot/bench/schema.py`
- Test: `tests/bench/test_schema.py`

**Interfaces:**
- Produces:
  - `Annotation(span: tuple[int, int], category: str, severity: Literal["error","warning","info"], correction: str | None, rationale: str | None, evidence: Evidence | None, confidence: Literal["high","medium","low"])`
  - `SentenceItem(id: str, source: str, document_type: str, context_before: str = "", text: str, context_after: str = "", annotations: list[Annotation] = [])`
  - `load_items(path: Path) -> list[SentenceItem]` (JSONL 로딩 + 검증)
  - `export_json_schema(out_dir: Path) -> None` → `benchmark/data/sentence-item.schema.json`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/bench/test_schema.py`

```python
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ttoryeot.bench.schema import SentenceItem, load_items, export_json_schema


def make_raw(**over):
    raw = {
        "id": "sent-0001",
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
                "rationale": "선행 후보가 3개",
                "evidence": {"source": "survey", "url": None},
                "confidence": "high",
            }
        ],
    }
    raw.update(over)
    return raw


def test_parses_valid_item():
    item = SentenceItem.model_validate(make_raw())
    assert item.annotations[0].span == (0, 6)


def test_negative_example_has_empty_annotations():
    item = SentenceItem.model_validate(make_raw(annotations=[]))
    assert item.annotations == []


def test_span_must_be_within_text():
    with pytest.raises(ValidationError):
        SentenceItem.model_validate(
            make_raw(annotations=[make_raw()["annotations"][0] | {"span": [0, 999]}])
        )


def test_load_items_roundtrip(tmp_path: Path):
    p = tmp_path / "sentences.jsonl"
    p.write_text(json.dumps(make_raw(), ensure_ascii=False) + "\n", encoding="utf-8")
    items = load_items(p)
    assert len(items) == 1 and items[0].id == "sent-0001"


def test_export_json_schema(tmp_path: Path):
    export_json_schema(tmp_path)
    schema = json.loads((tmp_path / "sentence-item.schema.json").read_text())
    assert schema["title"] == "SentenceItem"
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/bench/test_schema.py -q`
Expected: FAIL (`ModuleNotFoundError: ttoryeot.bench`)

- [ ] **Step 3: 구현** — `src/ttoryeot/bench/schema.py` (+ 빈 `__init__.py`)

```python
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, model_validator


class Evidence(BaseModel):
    source: str
    url: str | None = None


class Annotation(BaseModel):
    span: tuple[int, int]
    category: str
    severity: Literal["error", "warning", "info"]
    correction: str | None = None
    rationale: str | None = None
    evidence: Evidence | None = None
    confidence: Literal["high", "medium", "low"]


class SentenceItem(BaseModel):
    id: str
    source: str
    document_type: str
    context_before: str = ""
    text: str
    context_after: str = ""
    annotations: list[Annotation] = []

    @model_validator(mode="after")
    def _spans_within_text(self) -> "SentenceItem":
        for ann in self.annotations:
            start, end = ann.span
            if not (0 <= start < end <= len(self.text)):
                raise ValueError(f"span {ann.span} out of range for text len {len(self.text)}")
        return self


def load_items(path: Path) -> list[SentenceItem]:
    items = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(SentenceItem.model_validate_json(line))
    return items


def export_json_schema(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    schema = SentenceItem.model_json_schema()
    (out_dir / "sentence-item.schema.json").write_text(
        json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8"
    )
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/bench/test_schema.py -q`
Expected: `5 passed`

- [ ] **Step 5: 스키마 파일 생성 및 커밋**

```bash
uv run python -c "from pathlib import Path; from ttoryeot.bench.schema import export_json_schema; export_json_schema(Path('benchmark/data'))"
git add src/ttoryeot/bench tests/bench benchmark/data/sentence-item.schema.json
git commit -m "feat: 문장 수준 벤치마크 스키마 + JSON Schema export"
```

---

### Task 3: 조사표 CSV → JSONL 변환기

**Files:**
- Create: `src/ttoryeot/bench/convert.py`, `benchmark/raw/columns.example.yaml`
- Test: `tests/bench/test_convert.py`

**Interfaces:**
- Consumes: `SentenceItem`, `Annotation`, `Evidence` (Task 2)
- Produces: `convert_csv(csv_path: Path, mapping_path: Path, out_path: Path) -> int` (변환된 항목 수 반환). 컬럼 매핑 YAML로 실제 조사표 헤더를 canonical 필드에 연결 — 실제 CSV가 도착하면 `columns.yaml`만 작성하면 된다.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/bench/test_convert.py`

```python
from pathlib import Path

from ttoryeot.bench.convert import convert_csv
from ttoryeot.bench.schema import load_items

CSV = """원문,수정안,오류 분류,판정 이유,근거 URL,확신도,출처,문서 장르
리쿠르팅 존을 준비중입니다.,리크루팅 존을 준비 중입니다.,loanword_spelling,외래어 표기법,https://korean.go.kr/x,high,blog-a,team_blog
정상 문장입니다.,,,,,high,blog-a,team_blog
"""

MAPPING = """text: 원문
correction: 수정안
category: 오류 분류
rationale: 판정 이유
evidence_url: 근거 URL
confidence: 확신도
source: 출처
document_type: 문서 장르
default_severity: warning
"""


def test_convert_csv(tmp_path: Path):
    csv_p = tmp_path / "survey.csv"
    csv_p.write_text(CSV, encoding="utf-8")
    map_p = tmp_path / "columns.yaml"
    map_p.write_text(MAPPING, encoding="utf-8")
    out_p = tmp_path / "sentences.jsonl"

    n = convert_csv(csv_p, map_p, out_p)

    assert n == 2
    items = load_items(out_p)
    # 오류 행: 전체 문장 span의 annotation 1개
    assert items[0].annotations[0].category == "loanword_spelling"
    assert items[0].annotations[0].span == (0, len(items[0].text))
    # category가 비면 negative example
    assert items[1].annotations == []
    # id는 순번으로 부여
    assert items[0].id == "sent-0001" and items[1].id == "sent-0002"
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/bench/test_convert.py -q`
Expected: FAIL (`ModuleNotFoundError` 또는 `ImportError: convert_csv`)

- [ ] **Step 3: 구현** — `src/ttoryeot/bench/convert.py`

```python
import csv
from pathlib import Path

import yaml

from ttoryeot.bench.schema import Annotation, Evidence, SentenceItem


def convert_csv(csv_path: Path, mapping_path: Path, out_path: Path) -> int:
    m = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
    severity = m.get("default_severity", "warning")
    items: list[SentenceItem] = []
    with csv_path.open(encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            text = row[m["text"]].strip()
            if not text:
                continue
            category = (row.get(m["category"]) or "").strip()
            annotations = []
            if category:
                annotations.append(
                    Annotation(
                        span=(0, len(text)),
                        category=category,
                        severity=severity,
                        correction=(row.get(m["correction"]) or "").strip() or None,
                        rationale=(row.get(m["rationale"]) or "").strip() or None,
                        evidence=Evidence(
                            source=(row.get(m["source"]) or "survey").strip(),
                            url=(row.get(m["evidence_url"]) or "").strip() or None,
                        ),
                        confidence=(row.get(m["confidence"]) or "medium").strip(),
                    )
                )
            items.append(
                SentenceItem(
                    id=f"sent-{i:04d}",
                    source=(row.get(m["source"]) or "survey").strip(),
                    document_type=(row.get(m["document_type"]) or "unknown").strip(),
                    text=text,
                    annotations=annotations,
                )
            )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(item.model_dump_json() + "\n")
    return len(items)
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/bench/test_convert.py -q`
Expected: `1 passed`

- [ ] **Step 5: 매핑 예시 파일 작성 후 커밋** — `benchmark/raw/columns.example.yaml` (테스트의 `MAPPING`과 동일 내용, 실제 조사표 도착 시 `columns.yaml`로 복사해 헤더만 조정). `.gitignore`가 `benchmark/raw/`를 제외하므로 example 파일은 `git add -f`로 추가.

```bash
git add src/ttoryeot/bench/convert.py tests/bench/test_convert.py
git add -f benchmark/raw/columns.example.yaml
git commit -m "feat: 조사표 CSV → JSONL 변환기 (컬럼 매핑 YAML 방식)"
```

---

### Task 4: 진단 모델 + Analyzer / BenchEngine 프로토콜

**Files:**
- Create: `src/ttoryeot/ir/__init__.py`, `src/ttoryeot/ir/source.py`, `src/ttoryeot/diagnostics/__init__.py`, `src/ttoryeot/diagnostics/models.py`, `src/ttoryeot/analysis/__init__.py`, `src/ttoryeot/analysis/base.py`, `src/ttoryeot/bench/engine.py`
- Test: `tests/test_diagnostics.py`

**Interfaces:**
- Produces:
  - `SourceRange(file: str, start_line: int, start_col: int, end_line: int, end_col: int, start_offset: int, end_offset: int)` — line/col은 1-based, offset은 파일 내 0-based 문자 오프셋
  - `Candidate(text: str, score: float)` / `Diagnostic(rule: str, severity: Literal["error","warning","info"], message: str, range: SourceRange, candidates: list[Candidate] = [], evidence: str | None = None)`
  - `Analyzer` Protocol: `rule_ids: tuple[str, ...]`, `analyze(ws: WorkspaceIR, ctx: AnalysisContext) -> Iterable[Diagnostic]` (WorkspaceIR은 Task 7에서 정의 — base.py는 `TYPE_CHECKING` 임포트로 전방 참조)
  - `AnalysisContext(config: dict)` — `config`는 규칙별 설정 dict
  - `Prediction(span: tuple[int, int], category: str)` / `BenchEngine` Protocol: `name: str`, `predict(item: SentenceItem) -> list[Prediction]`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_diagnostics.py`

```python
from ttoryeot.diagnostics.models import Candidate, Diagnostic
from ttoryeot.ir.source import SourceRange


def rng(**over):
    d = dict(file="a.md", start_line=1, start_col=1, end_line=1, end_col=7,
             start_offset=0, end_offset=6)
    d.update(over)
    return SourceRange(**d)


def test_diagnostic_construction():
    diag = Diagnostic(
        rule="REF101", severity="warning",
        message="'해당 데이터'의 지시 대상이 불명확합니다.",
        range=rng(),
        candidates=[Candidate(text="조인 결과", score=0.48)],
    )
    assert diag.rule == "REF101"
    assert diag.candidates[0].score == 0.48


def test_source_range_ordering_validated():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        rng(end_offset=-1)
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_diagnostics.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: 구현**

`src/ttoryeot/ir/source.py`:
```python
from pydantic import BaseModel, model_validator


class SourceRange(BaseModel):
    file: str
    start_line: int  # 1-based
    start_col: int   # 1-based
    end_line: int
    end_col: int
    start_offset: int  # 파일 내 0-based 문자 오프셋
    end_offset: int

    @model_validator(mode="after")
    def _ordered(self) -> "SourceRange":
        if self.start_offset < 0 or self.end_offset < self.start_offset:
            raise ValueError("invalid offset range")
        return self
```

`src/ttoryeot/diagnostics/models.py`:
```python
from typing import Literal

from pydantic import BaseModel

from ttoryeot.ir.source import SourceRange


class Candidate(BaseModel):
    text: str
    score: float


class Diagnostic(BaseModel):
    rule: str
    severity: Literal["error", "warning", "info"]
    message: str
    range: SourceRange
    candidates: list[Candidate] = []
    evidence: str | None = None
```

`src/ttoryeot/analysis/base.py`:
```python
from typing import TYPE_CHECKING, Any, Iterable, Protocol, runtime_checkable

from pydantic import BaseModel

from ttoryeot.diagnostics.models import Diagnostic

if TYPE_CHECKING:
    from ttoryeot.ir.models import WorkspaceIR


class AnalysisContext(BaseModel):
    config: dict[str, Any] = {}


@runtime_checkable
class Analyzer(Protocol):
    rule_ids: tuple[str, ...]

    def analyze(self, ws: "WorkspaceIR", ctx: AnalysisContext) -> Iterable[Diagnostic]: ...
```

`src/ttoryeot/bench/engine.py`:
```python
from typing import Protocol

from pydantic import BaseModel

from ttoryeot.bench.schema import SentenceItem


class Prediction(BaseModel):
    span: tuple[int, int]  # item.text 기준 문자 오프셋
    category: str


class BenchEngine(Protocol):
    name: str

    def predict(self, item: SentenceItem) -> list[Prediction]: ...
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/test_diagnostics.py -q`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/ttoryeot/ir src/ttoryeot/diagnostics src/ttoryeot/analysis src/ttoryeot/bench/engine.py tests/test_diagnostics.py
git commit -m "feat: SourceRange·Diagnostic 모델 + Analyzer/BenchEngine 프로토콜"
```

---

### Task 5: 베이스라인 3종

**Files:**
- Create: `src/ttoryeot/bench/baselines.py`, `src/ttoryeot/bench/rules_data.py`
- Test: `tests/bench/test_baselines.py`

**Interfaces:**
- Consumes: `SentenceItem` (Task 2), `Prediction`/`BenchEngine` (Task 4)
- Produces:
  - `SubstitutionBaseline(name="baseline-subst")` — 문자열 치환 사전 기반
  - `RegexBaseline(name="baseline-regex")` — 정규식 규칙 기반
  - `NaiveReferenceBaseline(name="baseline-naive-ref")` — "해당/이/그/위 + 명사"면 무조건 `ambiguous_reference` 경고
  - `rules_data.SUBSTITUTIONS: dict[str, tuple[str, str]]` — `{잘못된 표기: (교정, category)}`, `rules_data.REGEX_RULES: list[tuple[str, str]]` — `(pattern, category)`. 조사표 도착 전까지는 스펙·대화에 등장한 대표 사례로 시드.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/bench/test_baselines.py`

```python
from ttoryeot.bench.baselines import (
    NaiveReferenceBaseline,
    RegexBaseline,
    SubstitutionBaseline,
)
from ttoryeot.bench.schema import SentenceItem


def item(text: str, ctx: str = "") -> SentenceItem:
    return SentenceItem(
        id="t", source="test", document_type="fixture",
        context_before=ctx, text=text,
    )


def test_substitution_finds_loanword():
    preds = SubstitutionBaseline().predict(item("리쿠르팅 존을 준비합니다."))
    assert len(preds) == 1
    assert preds[0].category == "loanword_spelling"
    assert preds[0].span == (0, 4)  # '리쿠르팅'


def test_substitution_clean_text_no_prediction():
    assert SubstitutionBaseline().predict(item("리크루팅 존을 준비합니다.")) == []


def test_regex_finds_spacing():
    preds = RegexBaseline().predict(item("배포를 준비중입니다."))
    assert preds and preds[0].category == "spacing"


def test_naive_ref_fires_on_any_demonstrative():
    preds = NaiveReferenceBaseline().predict(item("해당 데이터를 저장합니다."))
    assert preds and preds[0].category == "ambiguous_reference"
    assert preds[0].span == (0, 6)  # '해당 데이터'


def test_naive_ref_silent_without_demonstrative():
    assert NaiveReferenceBaseline().predict(item("조인 결과를 저장합니다.")) == []
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/bench/test_baselines.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: 구현**

`src/ttoryeot/bench/rules_data.py`:
```python
# 조사표 기반 시드 규칙. 실제 조사표 도착 시 이 파일을 확장한다.
SUBSTITUTIONS: dict[str, tuple[str, str]] = {
    "리쿠르팅": ("리크루팅", "loanword_spelling"),
    "타입스트립트": ("타입스크립트", "loanword_spelling"),
    "데이타": ("데이터", "loanword_spelling"),
}

REGEX_RULES: list[tuple[str, str]] = [
    (r"[가-힣]+중입니다", "spacing"),      # '준비중입니다' — 명사+중 붙여쓰기
    (r"열려있", "spacing"),                # '열려있는' → '열려 있는'
]

DEMONSTRATIVES = ("해당", "이", "그", "위")
```

`src/ttoryeot/bench/baselines.py`:
```python
import re

from ttoryeot.bench.engine import Prediction
from ttoryeot.bench.rules_data import DEMONSTRATIVES, REGEX_RULES, SUBSTITUTIONS
from ttoryeot.bench.schema import SentenceItem


class SubstitutionBaseline:
    name = "baseline-subst"

    def predict(self, item: SentenceItem) -> list[Prediction]:
        preds = []
        for wrong, (_fix, category) in SUBSTITUTIONS.items():
            start = 0
            while (idx := item.text.find(wrong, start)) != -1:
                preds.append(Prediction(span=(idx, idx + len(wrong)), category=category))
                start = idx + len(wrong)
        return preds


class RegexBaseline:
    name = "baseline-regex"

    def predict(self, item: SentenceItem) -> list[Prediction]:
        preds = []
        for pattern, category in REGEX_RULES:
            for m in re.finditer(pattern, item.text):
                preds.append(Prediction(span=(m.start(), m.end()), category=category))
        return preds


_REF_PATTERN = re.compile(
    rf"(?:{'|'.join(DEMONSTRATIVES)})\s+[가-힣A-Za-z]+"
)


class NaiveReferenceBaseline:
    name = "baseline-naive-ref"

    def predict(self, item: SentenceItem) -> list[Prediction]:
        return [
            Prediction(span=(m.start(), m.end()), category="ambiguous_reference")
            for m in _REF_PATTERN.finditer(item.text)
        ]
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/bench/test_baselines.py -q`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/ttoryeot/bench/baselines.py src/ttoryeot/bench/rules_data.py tests/bench/test_baselines.py
git commit -m "feat: 벤치마크 베이스라인 3종 (치환·정규식·나이브 지시어)"
```

---

### Task 6: 채점기 + 실험 하네스 + `ttoryeot bench` CLI

**Files:**
- Create: `src/ttoryeot/bench/scoring.py`, `src/ttoryeot/bench/harness.py`, `src/ttoryeot/cli.py`
- Test: `tests/bench/test_scoring.py`

**Interfaces:**
- Consumes: `SentenceItem`, `load_items` (Task 2), `convert_csv` (Task 3), `Prediction`/`BenchEngine` (Task 4), 베이스라인 3종 (Task 5)
- Produces:
  - `spans_overlap(a: tuple[int,int], b: tuple[int,int]) -> bool`
  - `RuleScore(tp: int, fp: int, fn: int)` + `precision/recall/f1` computed property
  - `score_items(items: list[SentenceItem], predictions: dict[str, list[Prediction]]) -> dict[str, RuleScore]` — key는 category, `"__total__"` 키에 전체 합산. TP 판정: category 일치 + span 겹침 (스펙 §4.3). category 일치·span 불일치는 FP+FN.
  - `run_engine(engine: BenchEngine, items) -> BenchResult` / `BenchResult(engine: str, scores: dict[str, RuleScore])` → `benchmark/results/{engine}.json` 저장
  - CLI: `ttoryeot bench convert <csv> <mapping> <out>`, `ttoryeot bench run --data <jsonl> --engine <name>` (엔진 레지스트리: 베이스라인 3종, Task 13에서 `ttoryeot` 추가)

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/bench/test_scoring.py`

```python
from ttoryeot.bench.engine import Prediction
from ttoryeot.bench.schema import Annotation, SentenceItem
from ttoryeot.bench.scoring import RuleScore, score_items, spans_overlap


def ann(span, category="loanword_spelling"):
    return Annotation(span=span, category=category, severity="warning", confidence="high")


def item(id, text, anns):
    return SentenceItem(id=id, source="t", document_type="f", text=text, annotations=anns)


def test_spans_overlap():
    assert spans_overlap((0, 5), (4, 9))
    assert not spans_overlap((0, 5), (5, 9))


def test_exact_match_is_tp():
    items = [item("a", "리쿠르팅 존", [ann((0, 4))])]
    preds = {"a": [Prediction(span=(0, 4), category="loanword_spelling")]}
    s = score_items(items, preds)["loanword_spelling"]
    assert (s.tp, s.fp, s.fn) == (1, 0, 0)
    assert s.precision == 1.0 and s.recall == 1.0


def test_wrong_span_is_fp_and_fn():
    items = [item("a", "리쿠르팅 존을 봅니다", [ann((0, 4))])]
    preds = {"a": [Prediction(span=(8, 10), category="loanword_spelling")]}
    s = score_items(items, preds)["loanword_spelling"]
    assert (s.tp, s.fp, s.fn) == (0, 1, 1)


def test_prediction_on_negative_example_is_fp():
    items = [item("a", "정상 문장입니다.", [])]
    preds = {"a": [Prediction(span=(0, 2), category="spacing")]}
    s = score_items(items, preds)["spacing"]
    assert (s.tp, s.fp, s.fn) == (0, 1, 0)


def test_missed_annotation_is_fn():
    items = [item("a", "리쿠르팅 존", [ann((0, 4))])]
    s = score_items(items, {"a": []})["loanword_spelling"]
    assert (s.tp, s.fp, s.fn) == (0, 0, 1)


def test_total_aggregates():
    items = [
        item("a", "리쿠르팅 존", [ann((0, 4))]),
        item("b", "정상 문장입니다.", []),
    ]
    preds = {
        "a": [Prediction(span=(0, 4), category="loanword_spelling")],
        "b": [Prediction(span=(0, 2), category="spacing")],
    }
    total = score_items(items, preds)["__total__"]
    assert (total.tp, total.fp, total.fn) == (1, 1, 0)


def test_zero_division_guard():
    s = RuleScore(tp=0, fp=0, fn=0)
    assert s.precision == 0.0 and s.recall == 0.0 and s.f1 == 0.0
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/bench/test_scoring.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: 채점기 구현** — `src/ttoryeot/bench/scoring.py`

```python
from collections import defaultdict

from pydantic import BaseModel, computed_field

from ttoryeot.bench.engine import Prediction
from ttoryeot.bench.schema import SentenceItem


def spans_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


class RuleScore(BaseModel):
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @computed_field
    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @computed_field
    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @computed_field
    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def score_items(
    items: list[SentenceItem], predictions: dict[str, list[Prediction]]
) -> dict[str, RuleScore]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    for item in items:
        preds = list(predictions.get(item.id, []))
        matched_preds: set[int] = set()
        for ann in item.annotations:
            hit = None
            for i, p in enumerate(preds):
                if i in matched_preds:
                    continue
                if p.category == ann.category and spans_overlap(p.span, ann.span):
                    hit = i
                    break
            if hit is not None:
                matched_preds.add(hit)
                counts[ann.category]["tp"] += 1
            else:
                counts[ann.category]["fn"] += 1
        for i, p in enumerate(preds):
            if i not in matched_preds:
                counts[p.category]["fp"] += 1
    scores = {cat: RuleScore(**c) for cat, c in counts.items()}
    scores["__total__"] = RuleScore(
        tp=sum(s.tp for s in scores.values()),
        fp=sum(s.fp for s in scores.values()),
        fn=sum(s.fn for s in scores.values()),
    )
    return scores
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/bench/test_scoring.py -q`
Expected: `7 passed`

- [ ] **Step 5: 하네스 + CLI 구현**

`src/ttoryeot/bench/harness.py`:
```python
import json
from pathlib import Path

from pydantic import BaseModel

from typing import Callable

from ttoryeot.bench.baselines import (
    NaiveReferenceBaseline,
    RegexBaseline,
    SubstitutionBaseline,
)
from ttoryeot.bench.engine import BenchEngine
from ttoryeot.bench.schema import SentenceItem, load_items
from ttoryeot.bench.scoring import RuleScore, score_items

# 값은 인자 없는 팩토리 — 클래스도, Task 13의 지연 임포트 함수도 등록 가능
ENGINES: dict[str, Callable[[], BenchEngine]] = {
    "baseline-subst": SubstitutionBaseline,
    "baseline-regex": RegexBaseline,
    "baseline-naive-ref": NaiveReferenceBaseline,
}


class BenchResult(BaseModel):
    engine: str
    n_items: int
    scores: dict[str, RuleScore]


def run_engine(engine: BenchEngine, items: list[SentenceItem]) -> BenchResult:
    predictions = {item.id: engine.predict(item) for item in items}
    return BenchResult(
        engine=engine.name, n_items=len(items), scores=score_items(items, predictions)
    )


def run_and_save(engine_name: str, data_path: Path, out_dir: Path) -> BenchResult:
    engine = ENGINES[engine_name]()
    result = run_engine(engine, load_items(data_path))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{engine_name}.json").write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result
```

`src/ttoryeot/cli.py`:
```python
from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True)
bench_app = typer.Typer(no_args_is_help=True)
app.add_typer(bench_app, name="bench")


@bench_app.command()
def convert(csv_path: Path, mapping: Path, out: Path) -> None:
    from ttoryeot.bench.convert import convert_csv

    n = convert_csv(csv_path, mapping, out)
    typer.echo(f"{n}개 항목 변환 완료 → {out}")


@bench_app.command()
def run(
    data: Path = typer.Option(Path("benchmark/data/sentences.jsonl")),
    engine: str = typer.Option(...),
    out_dir: Path = typer.Option(Path("benchmark/results")),
) -> None:
    from ttoryeot.bench.harness import run_and_save

    result = run_and_save(engine, data, out_dir)
    total = result.scores["__total__"]
    typer.echo(
        f"{engine}: P={total.precision:.3f} R={total.recall:.3f} F1={total.f1:.3f}"
    )
```

- [ ] **Step 6: 전체 테스트 + CLI 스모크 확인**

Run: `uv run pytest -q && uv run ttoryeot bench --help`
Expected: 전체 통과 + `convert`/`run` 서브커맨드 표시

- [ ] **Step 7: Commit**

```bash
git add src/ttoryeot/bench/scoring.py src/ttoryeot/bench/harness.py src/ttoryeot/cli.py tests/bench/test_scoring.py
git commit -m "feat: 채점기(P/R/F1)·실험 하네스·bench CLI"
```

---

### Task 7: Document IR 모델

**Files:**
- Create: `src/ttoryeot/ir/models.py`
- Test: `tests/ir/test_models.py`

**Interfaces:**
- Consumes: `SourceRange` (Task 4)
- Produces (모두 pydantic BaseModel):
  - `Token(form: str, tag: str, range: SourceRange)` — tag는 세종 품사(Kiwi)
  - `NounPhrase(text: str, head: str, range: SourceRange)` — head는 핵어 명사
  - `ReferenceExpression(text: str, demonstrative: str, head: str, range: SourceRange)` — 예: text='해당 데이터', demonstrative='해당', head='데이터'
  - `SentenceIR(text: str, range: SourceRange, tokens: list[Token] = [], noun_phrases: list[NounPhrase] = [], references: list[ReferenceExpression] = [])`
  - `Block(kind: Literal["heading","paragraph","list_item","code_block","block_quote"], level: int | None = None, range: SourceRange, sentences: list[SentenceIR] = [])` — code_block은 sentences 항상 빈 리스트
  - `DocumentIR(path: str, content_hash: str, blocks: list[Block] = [], parse_error: str | None = None)`
  - `WorkspaceIR(root: str, documents: list[DocumentIR] = [])` + `iter_sentences() -> Iterable[tuple[DocumentIR, Block, SentenceIR]]`
  - `export_ir_schema(out_dir: Path)` → `schemas/workspace-ir.schema.json`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/ir/test_models.py`

```python
import json
from pathlib import Path

from ttoryeot.ir.models import (
    Block, DocumentIR, SentenceIR, WorkspaceIR, export_ir_schema,
)
from ttoryeot.ir.source import SourceRange


def rng(f="a.md"):
    return SourceRange(file=f, start_line=1, start_col=1, end_line=1, end_col=10,
                       start_offset=0, end_offset=9)


def test_workspace_iter_sentences():
    sent = SentenceIR(text="문장입니다.", range=rng())
    block = Block(kind="paragraph", range=rng(), sentences=[sent])
    doc = DocumentIR(path="a.md", content_hash="x", blocks=[block])
    ws = WorkspaceIR(root=".", documents=[doc])
    triples = list(ws.iter_sentences())
    assert len(triples) == 1
    assert triples[0][2].text == "문장입니다."


def test_code_block_carries_no_sentences():
    block = Block(kind="code_block", range=rng())
    assert block.sentences == []


def test_export_ir_schema(tmp_path: Path):
    export_ir_schema(tmp_path)
    schema = json.loads((tmp_path / "workspace-ir.schema.json").read_text())
    assert schema["title"] == "WorkspaceIR"
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/ir/test_models.py -q`
Expected: FAIL (`ImportError`)

- [ ] **Step 3: 구현** — `src/ttoryeot/ir/models.py`

```python
import json
from pathlib import Path
from typing import Iterable, Literal

from pydantic import BaseModel

from ttoryeot.ir.source import SourceRange


class Token(BaseModel):
    form: str
    tag: str
    range: SourceRange


class NounPhrase(BaseModel):
    text: str
    head: str
    range: SourceRange


class ReferenceExpression(BaseModel):
    text: str
    demonstrative: str
    head: str
    range: SourceRange


class SentenceIR(BaseModel):
    text: str
    range: SourceRange
    tokens: list[Token] = []
    noun_phrases: list[NounPhrase] = []
    references: list[ReferenceExpression] = []


class Block(BaseModel):
    kind: Literal["heading", "paragraph", "list_item", "code_block", "block_quote"]
    level: int | None = None
    range: SourceRange
    sentences: list[SentenceIR] = []


class DocumentIR(BaseModel):
    path: str
    content_hash: str
    blocks: list[Block] = []
    parse_error: str | None = None


class WorkspaceIR(BaseModel):
    root: str
    documents: list[DocumentIR] = []

    def iter_sentences(self) -> Iterable[tuple[DocumentIR, Block, SentenceIR]]:
        for doc in self.documents:
            for block in doc.blocks:
                for sent in block.sentences:
                    yield doc, block, sent


def export_ir_schema(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "workspace-ir.schema.json").write_text(
        json.dumps(WorkspaceIR.model_json_schema(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

- [ ] **Step 4: 통과 확인 + 스키마 커밋**

Run: `uv run pytest tests/ir/test_models.py -q`
Expected: `3 passed`

```bash
uv run python -c "from pathlib import Path; from ttoryeot.ir.models import export_ir_schema; export_ir_schema(Path('schemas'))"
git add src/ttoryeot/ir/models.py tests/ir schemas/workspace-ir.schema.json
git commit -m "feat: Document IR 모델 + JSON Schema export"
```

---

### Task 8: Markdown 블록 파싱

**Files:**
- Create: `src/ttoryeot/parsing/__init__.py`, `src/ttoryeot/parsing/markdown.py`
- Test: `tests/parsing/test_markdown.py`

**Interfaces:**
- Consumes: 없음 (markdown-it-py만)
- Produces: `RawBlock(kind: str, level: int | None, text: str, start_line: int, end_line: int, start_offset: int)` (dataclass)와 `parse_blocks(source: str) -> list[RawBlock]`. `text`는 인라인 마크업 제거 없이 **원문 그대로의 슬라이스**여야 함 — 이후 Kiwi 오프셋을 원문에 역매핑하기 위한 불변식. `kind`는 IR의 Block.kind와 동일 문자열. code_block은 text를 비우고 위치만 유지.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/parsing/test_markdown.py`

```python
from ttoryeot.parsing.markdown import parse_blocks

SOURCE = """# 제목입니다

첫 문단입니다. 두 번째 문장입니다.

```python
code = "무시해야 합니다"
```

- 목록 항목입니다
"""


def test_parses_block_kinds():
    kinds = [b.kind for b in parse_blocks(SOURCE)]
    assert kinds == ["heading", "paragraph", "code_block", "list_item"]


def test_heading_level_and_text():
    heading = parse_blocks(SOURCE)[0]
    assert heading.level == 1
    assert heading.text == "제목입니다"


def test_paragraph_text_is_source_slice():
    para = parse_blocks(SOURCE)[1]
    assert para.text == "첫 문단입니다. 두 번째 문장입니다."
    # 원문 슬라이스 불변식: start_offset부터 text가 원문과 일치
    assert SOURCE[para.start_offset : para.start_offset + len(para.text)] == para.text


def test_code_block_text_empty():
    code = parse_blocks(SOURCE)[2]
    assert code.text == ""
```

(주의: 테스트 파일 안의 SOURCE 코드펜스는 실제 파일에서 `"""` 문자열 안에 그대로 들어간다.)

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/parsing/test_markdown.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: 구현** — `src/ttoryeot/parsing/markdown.py`

```python
from dataclasses import dataclass

from markdown_it import MarkdownIt

_KIND_BY_TOKEN = {
    "heading_open": "heading",
    "paragraph_open": "paragraph",
    "blockquote_open": "block_quote",
}


@dataclass
class RawBlock:
    kind: str
    level: int | None
    text: str
    start_line: int  # 1-based
    end_line: int
    start_offset: int  # source 기준 0-based


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    for i, ch in enumerate(source):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def parse_blocks(source: str) -> list[RawBlock]:
    md = MarkdownIt("commonmark")
    tokens = md.parse(source)
    line_offsets = _line_offsets(source)
    lines = source.split("\n")
    blocks: list[RawBlock] = []
    in_list_item = False

    for i, tok in enumerate(tokens):
        if tok.type == "list_item_open":
            in_list_item = True
            continue
        if tok.type == "list_item_close":
            in_list_item = False
            continue
        if tok.type == "fence" and tok.map:
            start, end = tok.map
            blocks.append(RawBlock(
                kind="code_block", level=None, text="",
                start_line=start + 1, end_line=end,
                start_offset=line_offsets[start],
            ))
            continue
        kind = _KIND_BY_TOKEN.get(tok.type)
        if kind is None or not tok.map:
            continue
        if kind == "paragraph" and in_list_item:
            kind = "list_item"
        start, end = tok.map
        # inline 토큰(다음 토큰)의 content 대신 원문 슬라이스를 사용해 오프셋 보존
        raw_lines = lines[start:end]
        text = "\n".join(raw_lines)
        start_offset = line_offsets[start]
        # heading의 '# ' / list의 '- ' 마커를 걷어내되 오프셋을 함께 전진
        stripped = text.lstrip("#>- ")
        start_offset += len(text) - len(stripped)
        level = tok.markup.count("#") if kind == "heading" else None
        blocks.append(RawBlock(
            kind=kind, level=level, text=stripped.strip(),
            start_line=start + 1, end_line=end,
            start_offset=start_offset,
        ))
    return blocks
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/parsing/test_markdown.py -q`
Expected: `4 passed` — 오프셋 불변식 테스트가 실패하면 마커 스트립 로직의 오프셋 계산을 원문 기준으로 재조정한다 (불변식이 정답, 구현을 맞출 것).

- [ ] **Step 5: Commit**

```bash
git add src/ttoryeot/parsing tests/parsing
git commit -m "feat: markdown-it-py 기반 블록 파싱 (원문 오프셋 보존)"
```

---

### Task 9: Kiwi lowering — 문장·형태소·명사구·지시어 추출

**Files:**
- Create: `src/ttoryeot/parsing/lowering.py`, `src/ttoryeot/parsing/workspace.py`
- Test: `tests/parsing/test_lowering.py`

**Interfaces:**
- Consumes: `RawBlock`, `parse_blocks` (Task 8), IR 모델 (Task 7)
- Produces:
  - `lower_document(path: str, source: str, kiwi: Kiwi) -> DocumentIR` — 블록별로 Kiwi `split_into_sents(text, return_tokens=True)` 실행, 토큰 오프셋을 블록 `start_offset` 기준으로 원문에 역매핑해 SourceRange 생성
  - `load_workspace(root: Path) -> WorkspaceIR` — `**/*.md` glob, 파일별 lower_document, 실패 시 `parse_error` 기록
  - 명사구 규칙: 연속된 `NNG|NNP|SL` 토큰을 병합, head는 마지막 명사
  - 지시어 규칙: `해당|동일한` (MM/XR 등 태그 무관, 표면형 기준) 또는 관형사 `이|그|위` 뒤에 명사구가 오면 ReferenceExpression. 단 `이|그`는 바로 뒤 토큰이 명사일 때만 (조사 '이'와 구분)
  - offset→(line, col) 변환 헬퍼 `to_range(file, source, start, end) -> SourceRange`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/parsing/test_lowering.py`

```python
from pathlib import Path

from kiwipiepy import Kiwi

from ttoryeot.parsing.lowering import lower_document
from ttoryeot.parsing.workspace import load_workspace

KIWI = Kiwi()

SOURCE = """# 파이프라인

사용자 테이블과 주문 테이블을 조인합니다. 해당 데이터를 저장합니다.
"""


def test_sentences_split():
    doc = lower_document("a.md", SOURCE, KIWI)
    para = doc.blocks[1]
    assert len(para.sentences) == 2


def test_sentence_offsets_roundtrip():
    doc = lower_document("a.md", SOURCE, KIWI)
    for block in doc.blocks:
        for sent in block.sentences:
            sliced = SOURCE[sent.range.start_offset : sent.range.end_offset]
            assert sliced == sent.text


def test_noun_phrases_extracted():
    doc = lower_document("a.md", SOURCE, KIWI)
    first = doc.blocks[1].sentences[0]
    heads = [np.head for np in first.noun_phrases]
    assert "테이블" in heads


def test_reference_expression_extracted():
    doc = lower_document("a.md", SOURCE, KIWI)
    second = doc.blocks[1].sentences[1]
    assert len(second.references) == 1
    ref = second.references[0]
    assert ref.demonstrative == "해당" and ref.head == "데이터"
    assert SOURCE[ref.range.start_offset : ref.range.end_offset] == ref.text


def test_load_workspace_records_parse_error(tmp_path: Path):
    good = tmp_path / "good.md"
    good.write_text("정상 문서입니다.\n", encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe invalid utf8 \xff")
    ws = load_workspace(tmp_path)
    by_path = {d.path: d for d in ws.documents}
    assert by_path["good.md"].parse_error is None
    assert by_path["bad.md"].parse_error is not None
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/parsing/test_lowering.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: lowering 구현** — `src/ttoryeot/parsing/lowering.py`

```python
from kiwipiepy import Kiwi

from ttoryeot.ir.models import (
    Block, DocumentIR, NounPhrase, ReferenceExpression, SentenceIR, Token,
)
from ttoryeot.ir.source import SourceRange
from ttoryeot.parsing.markdown import parse_blocks

NOUN_TAGS = {"NNG", "NNP", "SL"}
DEMONSTRATIVES = {"해당", "동일한", "이", "그", "위"}
_STRICT_NEXT_NOUN = {"이", "그", "위"}  # 조사·대명사와 구분: 바로 뒤가 명사일 때만


def to_range(file: str, source: str, start: int, end: int) -> SourceRange:
    def linecol(off: int) -> tuple[int, int]:
        line = source.count("\n", 0, off) + 1
        last_nl = source.rfind("\n", 0, off)
        return line, off - (last_nl + 1) + 1

    sl, sc = linecol(start)
    el, ec = linecol(end)
    return SourceRange(file=file, start_line=sl, start_col=sc, end_line=el,
                       end_col=ec, start_offset=start, end_offset=end)


def _noun_phrases(file: str, source: str, tokens: list[Token]) -> list[NounPhrase]:
    phrases, run = [], []
    for tok in tokens + [None]:
        if tok is not None and tok.tag in NOUN_TAGS:
            run.append(tok)
            continue
        if run:
            start = run[0].range.start_offset
            end = run[-1].range.end_offset
            phrases.append(NounPhrase(
                text=source[start:end], head=run[-1].form,
                range=to_range(file, source, start, end),
            ))
            run = []
    return phrases


def _references(
    file: str, source: str, tokens: list[Token], phrases: list[NounPhrase]
) -> list[ReferenceExpression]:
    refs = []
    for i, tok in enumerate(tokens):
        if tok.form not in DEMONSTRATIVES:
            continue
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if tok.form in _STRICT_NEXT_NOUN:
            if nxt is None or nxt.tag not in NOUN_TAGS or tok.tag not in {"MM", "MMD"}:
                continue
        # 지시어 바로 뒤에서 시작하는 명사구를 찾는다
        for np in phrases:
            if np.range.start_offset >= tok.range.end_offset:
                gap = source[tok.range.end_offset : np.range.start_offset]
                if gap.strip() == "" and len(gap) <= 2:
                    start = tok.range.start_offset
                    end = np.range.end_offset
                    refs.append(ReferenceExpression(
                        text=source[start:end], demonstrative=tok.form,
                        head=np.head, range=to_range(file, source, start, end),
                    ))
                break
    return refs


def lower_document(path: str, source: str, kiwi: Kiwi) -> DocumentIR:
    import hashlib

    blocks_ir: list[Block] = []
    for raw in parse_blocks(source):
        block_range = to_range(path, source, raw.start_offset,
                               raw.start_offset + len(raw.text))
        if raw.kind == "code_block" or not raw.text:
            blocks_ir.append(Block(kind=raw.kind, level=raw.level,
                                   range=block_range, sentences=[]))
            continue
        sentences = []
        for sent in kiwi.split_into_sents(raw.text, return_tokens=True):
            s_start = raw.start_offset + sent.start
            s_end = raw.start_offset + sent.end
            tokens = [
                Token(form=t.form, tag=t.tag,
                      range=to_range(path, source,
                                     raw.start_offset + t.start,
                                     raw.start_offset + t.start + t.len))
                for t in sent.tokens
            ]
            phrases = _noun_phrases(path, source, tokens)
            sentences.append(SentenceIR(
                text=source[s_start:s_end],
                range=to_range(path, source, s_start, s_end),
                tokens=tokens,
                noun_phrases=phrases,
                references=_references(path, source, tokens, phrases),
            ))
        blocks_ir.append(Block(kind=raw.kind, level=raw.level,
                               range=block_range, sentences=sentences))
    return DocumentIR(
        path=path,
        content_hash=hashlib.sha256(source.encode()).hexdigest()[:16],
        blocks=blocks_ir,
    )
```

- [ ] **Step 4: workspace 로더 구현** — `src/ttoryeot/parsing/workspace.py`

```python
from pathlib import Path

from kiwipiepy import Kiwi

from ttoryeot.ir.models import DocumentIR, WorkspaceIR
from ttoryeot.parsing.lowering import lower_document

_kiwi: Kiwi | None = None


def get_kiwi() -> Kiwi:
    global _kiwi
    if _kiwi is None:
        _kiwi = Kiwi()
    return _kiwi


def load_workspace(root: Path) -> WorkspaceIR:
    kiwi = get_kiwi()
    documents = []
    for md_path in sorted(root.rglob("*.md")):
        rel = str(md_path.relative_to(root))
        try:
            source = md_path.read_text(encoding="utf-8")
            documents.append(lower_document(rel, source, kiwi))
        except Exception as exc:  # 분석기는 크래시하지 않는다 (스펙 §7)
            documents.append(DocumentIR(path=rel, content_hash="", parse_error=str(exc)))
    return WorkspaceIR(root=str(root), documents=documents)
```

- [ ] **Step 5: 통과 확인**

Run: `uv run pytest tests/parsing/test_lowering.py -q`
Expected: `5 passed` — Kiwi 토큰 오프셋이 어긋나 왕복 테스트가 실패하면 `sent.start`/`t.start`가 블록 텍스트 기준인지 확인하고 역매핑 기준을 수정한다 (왕복 불변식이 정답).

- [ ] **Step 6: Commit**

```bash
git add src/ttoryeot/parsing/lowering.py src/ttoryeot/parsing/workspace.py tests/parsing/test_lowering.py
git commit -m "feat: Kiwi lowering — 문장·형태소·명사구·지시어 추출 + 워크스페이스 로더"
```

---

### Task 10: 용어 심벌 테이블 패스 (TERM100·101·102)

**Files:**
- Create: `src/ttoryeot/analysis/terms/__init__.py`, `src/ttoryeot/analysis/terms/dictionary.py`, `src/ttoryeot/analysis/terms/analyzer.py`
- Test: `tests/analysis/test_terms.py`

**Interfaces:**
- Consumes: `WorkspaceIR`·IR 모델 (Task 7, 9), `Diagnostic`·`Analyzer`·`AnalysisContext` (Task 4)
- Produces:
  - `TermEntry(canonical: str, aliases: list[str] = [], definition: str | None = None)` / `load_term_dictionary(path: Path) -> list[TermEntry]` (YAML: `terms: [{canonical, aliases, definition}]`)
  - `TermOccurrence(canonical: str, surface: str, doc_path: str, range: SourceRange)`
  - `build_symbol_table(ws: WorkspaceIR, entries: list[TermEntry]) -> dict[str, list[TermOccurrence]]` — 문장 텍스트에서 canonical과 모든 alias의 표면형 검색 (공백 정규화 매칭 포함)
  - `TermAnalyzer(entries).analyze(ws, ctx)` — `rule_ids = ("TERM100", "TERM101", "TERM102")`
  - 정의 문장 판정: `{surface}(이)란/은/는 ... (이다|입니다|를 말합니다|을 말합니다)` 패턴 또는 list_item 블록의 `{surface}: ...` 형식. 정의 텍스트를 공백 정규화해 비교, 서로 다르면 TERM102.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/analysis/test_terms.py`

```python
from pathlib import Path

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.terms.analyzer import TermAnalyzer
from ttoryeot.analysis.terms.dictionary import TermEntry, load_term_dictionary
from ttoryeot.parsing.workspace import load_workspace

ENTRIES = [TermEntry(canonical="데이터세트", aliases=["데이터셋", "데이터 세트"])]


def make_ws(tmp_path: Path, files: dict[str, str]):
    for name, content in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return load_workspace(tmp_path)


def run(ws):
    return list(TermAnalyzer(ENTRIES).analyze(ws, AnalysisContext()))


def test_term100_mixed_in_one_document(tmp_path):
    ws = make_ws(tmp_path, {"a.md": "데이터세트를 만듭니다.\n\n데이터셋을 저장합니다.\n"})
    rules = [d.rule for d in run(ws)]
    assert "TERM100" in rules


def test_term101_mixed_across_documents(tmp_path):
    ws = make_ws(tmp_path, {
        "a.md": "데이터세트를 만듭니다.\n",
        "b.md": "데이터셋을 저장합니다.\n",
    })
    diags = run(ws)
    assert [d.rule for d in diags] == ["TERM101"]
    # 비정본 표기 위치에 진단이 달린다
    assert diags[0].range.file == "b.md"


def test_term102_conflicting_definitions(tmp_path):
    ws = make_ws(tmp_path, {
        "glossary.md": "데이터세트란 분석 가능한 논리적 테이블의 집합이다.\n",
        "pipeline.md": "데이터세트란 단일 BigQuery 테이블이다.\n",
    })
    rules = [d.rule for d in run(ws)]
    assert "TERM102" in rules


def test_consistent_usage_is_clean(tmp_path):
    ws = make_ws(tmp_path, {
        "a.md": "데이터세트를 만듭니다.\n",
        "b.md": "데이터세트를 저장합니다.\n",
    })
    assert run(ws) == []


def test_load_dictionary(tmp_path):
    p = tmp_path / "terms.yaml"
    p.write_text(
        "terms:\n  - canonical: 데이터세트\n    aliases: [데이터셋]\n", encoding="utf-8"
    )
    entries = load_term_dictionary(p)
    assert entries[0].canonical == "데이터세트"
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/analysis/test_terms.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: 사전·심벌 테이블 구현** — `src/ttoryeot/analysis/terms/dictionary.py`

```python
from pathlib import Path

import yaml
from pydantic import BaseModel

from ttoryeot.ir.models import WorkspaceIR
from ttoryeot.ir.source import SourceRange


class TermEntry(BaseModel):
    canonical: str
    aliases: list[str] = []
    definition: str | None = None


class TermOccurrence(BaseModel):
    canonical: str
    surface: str
    doc_path: str
    range: SourceRange


def load_term_dictionary(path: Path) -> list[TermEntry]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [TermEntry.model_validate(t) for t in data.get("terms", [])]


def build_symbol_table(
    ws: WorkspaceIR, entries: list[TermEntry]
) -> dict[str, list[TermOccurrence]]:
    table: dict[str, list[TermOccurrence]] = {e.canonical: [] for e in entries}
    surfaces = [
        (e.canonical, s) for e in entries for s in [e.canonical, *e.aliases]
    ]
    # 긴 표면형 우선 매칭 ('데이터 세트'가 '세트'보다 먼저)
    surfaces.sort(key=lambda cs: -len(cs[1]))
    for doc in ws.documents:
        for _doc, _block, sent in WorkspaceIR(root=ws.root, documents=[doc]).iter_sentences():
            taken: list[tuple[int, int]] = []
            for canonical, surface in surfaces:
                start = 0
                while (idx := sent.text.find(surface, start)) != -1:
                    abs_start = sent.range.start_offset + idx
                    abs_end = abs_start + len(surface)
                    start = idx + len(surface)
                    if any(a < abs_end and abs_start < b for a, b in taken):
                        continue
                    taken.append((abs_start, abs_end))
                    table[canonical].append(TermOccurrence(
                        canonical=canonical, surface=surface, doc_path=doc.path,
                        range=SourceRange(
                            file=doc.path,
                            start_line=sent.range.start_line, start_col=1,
                            end_line=sent.range.start_line, end_col=1,
                            start_offset=abs_start, end_offset=abs_end,
                        ),
                    ))
    return table
```

(참고: 심벌 테이블의 line/col은 문장 범위 기반 근사치로 시작한다. 정밀 col은 리포트 품질에 영향이 생기면 `to_range`로 원문 재계산하는 후속 개선으로 미룬다 — 오프셋은 정확하다.)

- [ ] **Step 4: 분석기 구현** — `src/ttoryeot/analysis/terms/analyzer.py`

```python
import re
from collections import defaultdict
from typing import Iterable

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.terms.dictionary import TermEntry, TermOccurrence, build_symbol_table
from ttoryeot.diagnostics.models import Diagnostic
from ttoryeot.ir.models import WorkspaceIR


def _definition_pattern(surface: str) -> re.Pattern:
    esc = re.escape(surface)
    return re.compile(
        rf"{esc}(?:이란|란|은|는)\s+(.+?)(?:이다|입니다|를 말합니다|을 말합니다)"
    )


class TermAnalyzer:
    rule_ids = ("TERM100", "TERM101", "TERM102")

    def __init__(self, entries: list[TermEntry]):
        self.entries = entries

    def analyze(self, ws: WorkspaceIR, ctx: AnalysisContext) -> Iterable[Diagnostic]:
        table = build_symbol_table(ws, self.entries)
        for entry in self.entries:
            occs = table[entry.canonical]
            yield from self._mixed_usage(entry, occs)
            yield from self._conflicting_definitions(ws, entry)

    def _mixed_usage(
        self, entry: TermEntry, occs: list[TermOccurrence]
    ) -> Iterable[Diagnostic]:
        by_doc: dict[str, set[str]] = defaultdict(set)
        for o in occs:
            by_doc[o.doc_path].add(o.surface)
        all_surfaces = {o.surface for o in occs}
        # TERM100: 한 문서 안에 두 표기
        for doc_path, surfaces in by_doc.items():
            if len(surfaces) > 1:
                for o in occs:
                    if o.doc_path == doc_path and o.surface != entry.canonical:
                        yield Diagnostic(
                            rule="TERM100", severity="warning",
                            message=f"'{o.surface}'와 '{entry.canonical}' 표기가 같은 문서에서 혼용됩니다.",
                            range=o.range,
                        )
                return  # TERM100이 있으면 TERM101 중복 보고 안 함
        # TERM101: 문서 간 혼용
        if len(all_surfaces) > 1:
            for o in occs:
                if o.surface != entry.canonical:
                    yield Diagnostic(
                        rule="TERM101", severity="warning",
                        message=f"'{o.surface}'는 다른 문서의 '{entry.canonical}' 표기와 불일치합니다.",
                        range=o.range,
                    )

    def _conflicting_definitions(
        self, ws: WorkspaceIR, entry: TermEntry
    ) -> Iterable[Diagnostic]:
        pattern = _definition_pattern(entry.canonical)
        found: list[tuple[str, str, object]] = []  # (normalized_def, doc, range)
        for doc, _block, sent in ws.iter_sentences():
            m = pattern.search(sent.text)
            if m:
                normalized = " ".join(m.group(1).split())
                found.append((normalized, doc.path, sent.range))
        # glossary 파일의 정의를 정본으로 우선 — 충돌 진단은 나머지 정의 위치에 단다
        found.sort(key=lambda f: (0 if "glossary" in f[1] else 1, f[1]))
        definitions = {d for d, _, _ in found}
        if len(definitions) > 1:
            for _defn, _doc, rng in found[1:]:
                yield Diagnostic(
                    rule="TERM102", severity="warning",
                    message=f"'{entry.canonical}'의 정의가 다른 문서의 정의와 충돌합니다.",
                    range=rng,
                    evidence=f"기존 정의: {found[0][0]} ({found[0][1]})",
                )
```

- [ ] **Step 5: 통과 확인**

Run: `uv run pytest tests/analysis/test_terms.py -q`
Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add src/ttoryeot/analysis/terms tests/analysis/test_terms.py
git commit -m "feat: 용어 심벌 테이블 패스 (TERM100 문서 내 혼용·TERM101 문서 간 혼용·TERM102 정의 충돌)"
```

---

### Task 11: 지시어 해석 위험 패스 (REF101)

**Files:**
- Create: `src/ttoryeot/analysis/references/__init__.py`, `src/ttoryeot/analysis/references/candidates.py`, `src/ttoryeot/analysis/references/analyzer.py`, `src/ttoryeot/config/default.yaml`
- Test: `tests/analysis/test_references.py`

**Interfaces:**
- Consumes: IR 모델·`iter_sentences` (Task 7), `ReferenceExpression`·`NounPhrase` (Task 9), `Diagnostic`·`Candidate`·`AnalysisContext` (Task 4)
- Produces:
  - `ScoredCandidate(phrase: NounPhrase, score: float)`
  - `rank_candidates(ref: ReferenceExpression, window: list[SentenceIR], weights: dict[str, float]) -> list[ScoredCandidate]` — 내림차순 정렬
  - `ReferenceAnalyzer().analyze(ws, ctx)` — `rule_ids = ("REF101",)`. 후보 2개 이상이고 `top1.score - top2.score < threshold`일 때만 REF101 + 후보 목록 보고
  - 설정 (`src/ttoryeot/config/default.yaml`): `reference: {window: 5, threshold: 0.2, weights: {distance: 0.4, role: 0.25, head_match: 0.25, recency: 0.1}}` — 임계값 0.2는 대표 모호 케이스(후보 점수차 0.175)를 손계산으로 검증한 초기값. 벤치마크 튜닝 대상.
  - 점수 요소 (모두 0~1 정규화): distance=`1/(1+문장거리)`, role=후보 명사구 뒤 조사가 주격(이/가)·목적격(을/를)이면 1.0 아니면 0.3, head_match=ref.head가 후보 텍스트에 포함되거나 후보 head와 일치하면 1.0 아니면 0.0, recency=후보가 윈도 내 마지막 문장에 있으면 1.0 아니면 0.0. 윈도는 같은 블록 시퀀스 내 선행 문장 최대 N개 — heading 블록을 만나면 중단 (섹션 경계 페널티의 v1 구현).

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/analysis/test_references.py`

```python
from pathlib import Path

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.references.analyzer import ReferenceAnalyzer
from ttoryeot.parsing.workspace import load_workspace


def make_ws(tmp_path: Path, content: str):
    (tmp_path / "doc.md").write_text(content, encoding="utf-8")
    return load_workspace(tmp_path)


def run(ws, config=None):
    ctx = AnalysisContext(config=config or {})
    return list(ReferenceAnalyzer().analyze(ws, ctx))


def test_ref101_on_ambiguous_reference(tmp_path):
    ws = make_ws(tmp_path,
        "사용자 테이블과 주문 테이블을 조인합니다.\n\n해당 데이터를 저장합니다.\n")
    diags = run(ws)
    assert [d.rule for d in diags] == ["REF101"]
    assert len(diags[0].candidates) >= 2


def test_clear_single_candidate_is_silent(tmp_path):
    ws = make_ws(tmp_path, "조인 결과를 만듭니다.\n\n해당 결과를 저장합니다.\n")
    assert run(ws) == []


def test_no_reference_no_diagnostic(tmp_path):
    ws = make_ws(tmp_path, "조인 결과를 저장합니다.\n")
    assert run(ws) == []


def test_section_boundary_cuts_window(tmp_path):
    ws = make_ws(tmp_path,
        "주문 테이블을 만듭니다.\n\n# 다른 섹션\n\n"
        "사용자 로그를 수집합니다.\n\n해당 로그를 저장합니다.\n")
    diags = run(ws)
    # 섹션 이전의 '주문 테이블'은 후보가 아니므로 후보는 '사용자 로그' 계열뿐 → 침묵
    assert diags == []


def test_threshold_configurable(tmp_path):
    ws = make_ws(tmp_path,
        "사용자 테이블과 주문 테이블을 조인합니다.\n\n해당 데이터를 저장합니다.\n")
    # 임계값 0이면 어떤 점수 차든 통과 → 진단 없음
    assert run(ws, {"reference": {"threshold": 0.0}}) == []
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/analysis/test_references.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: 후보 점수화 구현** — `src/ttoryeot/analysis/references/candidates.py`

```python
from pydantic import BaseModel

from ttoryeot.ir.models import NounPhrase, ReferenceExpression, SentenceIR

DEFAULT_WEIGHTS = {"distance": 0.4, "role": 0.25, "head_match": 0.25, "recency": 0.1}
SUBJ_OBJ_PARTICLES = {"이", "가", "을", "를", "은", "는"}


class ScoredCandidate(BaseModel):
    phrase: NounPhrase
    score: float


def _role_score(phrase: NounPhrase, sent: SentenceIR) -> float:
    for i, tok in enumerate(sent.tokens):
        if tok.range.end_offset == phrase.range.end_offset:
            nxt = sent.tokens[i + 1] if i + 1 < len(sent.tokens) else None
            if nxt is not None and nxt.tag.startswith("J") and nxt.form in SUBJ_OBJ_PARTICLES:
                return 1.0
    return 0.3


def rank_candidates(
    ref: ReferenceExpression,
    window: list[SentenceIR],
    weights: dict[str, float] | None = None,
) -> list[ScoredCandidate]:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    scored = []
    n = len(window)
    for dist_idx, sent in enumerate(reversed(window)):  # dist_idx=0이 직전 문장
        for phrase in sent.noun_phrases:
            if phrase.range.end_offset >= ref.range.start_offset:
                continue  # 지시어 이후 등장 후보 제외
            distance = 1.0 / (1.0 + dist_idx)
            role = _role_score(phrase, sent)
            head_match = 1.0 if (ref.head == phrase.head or ref.head in phrase.text) else 0.0
            recency = 1.0 if dist_idx == 0 else 0.0
            score = (w["distance"] * distance + w["role"] * role
                     + w["head_match"] * head_match + w["recency"] * recency)
            scored.append(ScoredCandidate(phrase=phrase, score=round(score, 4)))
    scored.sort(key=lambda c: -c.score)
    return scored
```

- [ ] **Step 4: 분석기 구현** — `src/ttoryeot/analysis/references/analyzer.py`

```python
from typing import Iterable

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.references.candidates import rank_candidates
from ttoryeot.diagnostics.models import Candidate, Diagnostic
from ttoryeot.ir.models import WorkspaceIR

DEFAULTS = {"window": 5, "threshold": 0.2, "weights": None}


class ReferenceAnalyzer:
    rule_ids = ("REF101",)

    def analyze(self, ws: WorkspaceIR, ctx: AnalysisContext) -> Iterable[Diagnostic]:
        cfg = {**DEFAULTS, **ctx.config.get("reference", {})}
        for doc in ws.documents:
            # 문서 내 문장 시퀀스 (heading에서 윈도 리셋)
            window = []
            for block in doc.blocks:
                if block.kind == "heading":
                    window = []
                    continue
                for sent in block.sentences:
                    for ref in sent.references:
                        ranked = rank_candidates(ref, window[-cfg["window"]:],
                                                 cfg["weights"])
                        # 같은 표면형의 반복 언급만 하나로 접는다 —
                        # '사용자 테이블'과 '주문 테이블'은 head가 같아도 서로 다른 후보
                        seen, unique = set(), []
                        for c in ranked:
                            if c.phrase.text not in seen:
                                seen.add(c.phrase.text)
                                unique.append(c)
                        if len(unique) >= 2 and (unique[0].score - unique[1].score) < cfg["threshold"]:
                            yield Diagnostic(
                                rule="REF101", severity="warning",
                                message=f"'{ref.text}'의 지시 대상이 불명확합니다.",
                                range=ref.range,
                                candidates=[
                                    Candidate(text=c.phrase.text, score=c.score)
                                    for c in unique[:3]
                                ],
                            )
                    window.append(sent)
```

- [ ] **Step 5: 기본 설정 파일 작성** — `src/ttoryeot/config/default.yaml`

```yaml
reference:
  window: 5
  threshold: 0.2
  weights:
    distance: 0.4
    role: 0.25
    head_match: 0.25
    recency: 0.1
```

- [ ] **Step 6: 통과 확인**

Run: `uv run pytest tests/analysis/test_references.py -q`
Expected: `5 passed` — 점수 요소는 결정적이므로 실패 시 가중치가 아니라 후보 추출(명사구/윈도) 로직부터 확인한다.

- [ ] **Step 7: Commit**

```bash
git add src/ttoryeot/analysis/references src/ttoryeot/config tests/analysis/test_references.py
git commit -m "feat: 지시어 해석 위험 패스 (REF101 — 후보 점수차 기반 모호성 탐지)"
```

---

### Task 12: 픽스처 저장소 + golden 테스트 + `ttoryeot lint`

**Files:**
- Create: `corpus/fixtures/data-platform/{terms.yaml, expected.yaml, glossary.md, docs/pipeline.md, docs/deploy.md, docs/faq.md}`, `src/ttoryeot/runner.py`
- Modify: `src/ttoryeot/cli.py` (lint 커맨드 추가)
- Test: `tests/test_golden.py`

**Interfaces:**
- Consumes: `load_workspace` (Task 9), `TermAnalyzer`·`load_term_dictionary` (Task 10), `ReferenceAnalyzer` (Task 11)
- Produces:
  - `run_workspace(root: Path, terms_path: Path | None, config: dict) -> list[Diagnostic]` — 파싱 실패 문서마다 `INT001` info 진단 추가, 이후 두 분석기 실행
  - CLI: `ttoryeot lint <root> [--terms terms.yaml]` → `file:line RULE message` 형식 출력, 진단 있으면 exit code 1
  - 픽스처 `expected.yaml` 형식(스펙 §4.2): `diagnostics: [{rule, file, line}]`, `clean_files: [...]`

- [ ] **Step 1: 픽스처 작성**

`corpus/fixtures/data-platform/terms.yaml`:
```yaml
terms:
  - canonical: 데이터세트
    aliases: [데이터셋, 데이터 세트]
```

`corpus/fixtures/data-platform/glossary.md`:
```markdown
# 용어집

데이터세트란 분석 가능한 논리적 테이블의 집합이다.
```

`corpus/fixtures/data-platform/docs/pipeline.md`:
```markdown
# 파이프라인

데이터세트란 단일 BigQuery 테이블이다.

사용자 테이블과 주문 테이블을 조인합니다.

해당 데이터를 저장합니다.
```

`corpus/fixtures/data-platform/docs/deploy.md`:
```markdown
# 배포

데이터셋을 프로덕션에 배포합니다.
```

`corpus/fixtures/data-platform/docs/faq.md`:
```markdown
# FAQ

조인 결과를 저장합니다.
```

`corpus/fixtures/data-platform/expected.yaml`:
```yaml
diagnostics:
  - rule: TERM102
    file: docs/pipeline.md
    line: 3
  - rule: REF101
    file: docs/pipeline.md
    line: 7
  - rule: TERM101
    file: docs/deploy.md
    line: 3
clean_files:
  - docs/faq.md
```

- [ ] **Step 2: 실패하는 golden 테스트 작성** — `tests/test_golden.py`

```python
from pathlib import Path

import yaml

from ttoryeot.runner import run_workspace

FIXTURE = Path("corpus/fixtures/data-platform")


def test_golden_data_platform():
    expected = yaml.safe_load((FIXTURE / "expected.yaml").read_text(encoding="utf-8"))
    diags = run_workspace(FIXTURE, FIXTURE / "terms.yaml", {})
    got = {(d.rule, d.range.file, d.range.start_line) for d in diags}
    want = {(e["rule"], e["file"], e["line"]) for e in expected["diagnostics"]}
    assert want <= got, f"missing: {want - got}"
    # clean_files에는 어떤 진단도 없어야 한다 (오탐 체크)
    for clean in expected["clean_files"]:
        assert not [d for d in diags if d.range.file == clean], clean
    # expected에 없는 파일별 초과 진단도 오탐으로 간주
    extra = got - want
    assert not extra, f"unexpected: {extra}"
```

- [ ] **Step 3: 실패 확인**

Run: `uv run pytest tests/test_golden.py -q`
Expected: FAIL (`ModuleNotFoundError: ttoryeot.runner`)

- [ ] **Step 4: 러너 구현** — `src/ttoryeot/runner.py`

```python
from pathlib import Path
from typing import Any

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.references.analyzer import ReferenceAnalyzer
from ttoryeot.analysis.terms.analyzer import TermAnalyzer
from ttoryeot.analysis.terms.dictionary import load_term_dictionary
from ttoryeot.diagnostics.models import Diagnostic
from ttoryeot.ir.source import SourceRange
from ttoryeot.parsing.workspace import load_workspace


def run_workspace(
    root: Path, terms_path: Path | None, config: dict[str, Any]
) -> list[Diagnostic]:
    ws = load_workspace(root)
    ctx = AnalysisContext(config=config)
    diags: list[Diagnostic] = []
    for doc in ws.documents:
        if doc.parse_error is not None:
            diags.append(Diagnostic(
                rule="INT001", severity="info",
                message=f"문서를 파싱하지 못해 분석에서 제외했습니다: {doc.parse_error}",
                range=SourceRange(file=doc.path, start_line=1, start_col=1,
                                  end_line=1, end_col=1, start_offset=0, end_offset=0),
            ))
    analyzers = [ReferenceAnalyzer()]
    if terms_path is not None and terms_path.exists():
        analyzers.insert(0, TermAnalyzer(load_term_dictionary(terms_path)))
    for analyzer in analyzers:
        diags.extend(analyzer.analyze(ws, ctx))
    return diags
```

- [ ] **Step 5: golden 통과 확인**

Run: `uv run pytest tests/test_golden.py -q`
Expected: `1 passed` — 실패하면 `expected.yaml`의 line 번호를 실제 진단과 대조해 **어느 쪽이 스펙에 맞는지 먼저 판정**한다. 분석기 버그면 분석기를 고치고, 픽스처 기대값 오기면 expected를 고친다. 분석기를 기대값에 끼워 맞추지 말 것.

- [ ] **Step 6: lint CLI 추가** — `src/ttoryeot/cli.py`에 추가

```python
@app.command()
def lint(
    root: Path,
    terms: Path | None = typer.Option(None, help="용어 사전 YAML"),
) -> None:
    from ttoryeot.runner import run_workspace

    diags = run_workspace(root, terms, {})
    for d in sorted(diags, key=lambda d: (d.range.file, d.range.start_line)):
        typer.echo(f"{d.range.file}:{d.range.start_line} {d.rule} {d.message}")
        for c in d.candidates:
            typer.echo(f"    후보 {c.score:.2f}  {c.text}")
    if diags:
        raise typer.Exit(code=1)
```

- [ ] **Step 7: CLI 스모크 확인**

Run: `uv run ttoryeot lint corpus/fixtures/data-platform --terms corpus/fixtures/data-platform/terms.yaml; echo "exit=$?"`
Expected: TERM101·TERM102·REF101 진단 출력 + `exit=1`

- [ ] **Step 8: Commit**

```bash
git add corpus/fixtures src/ttoryeot/runner.py src/ttoryeot/cli.py tests/test_golden.py
git commit -m "feat: 픽스처 저장소 golden 테스트 + ttoryeot lint CLI"
```

---

### Task 13: 엔진 벤치 어댑터 + `bench report`

**Files:**
- Create: `src/ttoryeot/bench/adapter.py`, `src/ttoryeot/bench/report.py`, `benchmark/data/category-map.md`, `benchmark/data/sample-sentences.jsonl`
- Modify: `src/ttoryeot/bench/harness.py` (ENGINES에 `ttoryeot` 등록), `src/ttoryeot/cli.py` (report 커맨드)
- Test: `tests/bench/test_adapter.py`, `tests/bench/test_report.py`

**Interfaces:**
- Consumes: `BenchEngine`·`Prediction` (Task 4), `lower_document` (Task 9), `TermAnalyzer`·`TermEntry` (Task 10), `ReferenceAnalyzer` (Task 11), `BenchResult` (Task 6)
- Produces:
  - `RULE_CATEGORY: dict[str, str]` = `{"REF101": "ambiguous_reference", "TERM100": "term_inconsistency", "TERM101": "term_inconsistency", "TERM102": "term_definition_conflict"}`
  - `TtoryeotEngine(name="ttoryeot")` — `context_before + "\n\n" + text`로 임시 단일 문서를 만들어 분석기 실행, `text` 범위 안의 진단만 `Prediction`으로 변환 (스펙 §4.3 채점 방식)
  - `write_report(results_dir: Path) -> Path` — `results/*.json` 전체를 읽어 `benchmark/results/report.md` 생성 (엔진×카테고리 P/R/F1 표)

- [ ] **Step 1: 실패하는 어댑터 테스트 작성** — `tests/bench/test_adapter.py`

```python
from ttoryeot.bench.adapter import TtoryeotEngine
from ttoryeot.bench.schema import SentenceItem


def item(text, ctx=""):
    return SentenceItem(id="t", source="t", document_type="f",
                        context_before=ctx, text=text)


def test_predicts_ambiguous_reference_within_text_span():
    preds = TtoryeotEngine().predict(item(
        "해당 데이터를 저장합니다.",
        ctx="사용자 테이블과 주문 테이블을 조인합니다.",
    ))
    assert len(preds) == 1
    p = preds[0]
    assert p.category == "ambiguous_reference"
    assert p.span == (0, 6)  # text 기준 '해당 데이터'


def test_context_only_diagnostics_are_excluded():
    # context_before에서만 발생하는 진단은 예측에 포함되지 않는다
    preds = TtoryeotEngine().predict(item(
        "조인 결과를 저장합니다.",
        ctx="해당 데이터를 조인합니다. 사용자 테이블과 주문 테이블이 있습니다.",
    ))
    assert preds == []
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/bench/test_adapter.py -q`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: 어댑터 구현** — `src/ttoryeot/bench/adapter.py`

```python
from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.references.analyzer import ReferenceAnalyzer
from ttoryeot.analysis.terms.analyzer import TermAnalyzer
from ttoryeot.analysis.terms.dictionary import TermEntry
from ttoryeot.bench.engine import Prediction
from ttoryeot.bench.schema import SentenceItem
from ttoryeot.ir.models import WorkspaceIR
from ttoryeot.parsing.lowering import lower_document
from ttoryeot.parsing.workspace import get_kiwi

RULE_CATEGORY = {
    "REF101": "ambiguous_reference",
    "TERM100": "term_inconsistency",
    "TERM101": "term_inconsistency",
    "TERM102": "term_definition_conflict",
}

# 트랙 1용 시드 용어 사전 — 조사표 도착 시 확장
SEED_TERMS = [TermEntry(canonical="데이터세트", aliases=["데이터셋", "데이터 세트"])]


class TtoryeotEngine:
    name = "ttoryeot"

    def predict(self, item: SentenceItem) -> list[Prediction]:
        prefix = item.context_before + "\n\n" if item.context_before else ""
        source = prefix + item.text
        doc = lower_document("item.md", source, get_kiwi())
        ws = WorkspaceIR(root=".", documents=[doc])
        ctx = AnalysisContext()
        base = len(prefix)
        preds = []
        for analyzer in (TermAnalyzer(SEED_TERMS), ReferenceAnalyzer()):
            for d in analyzer.analyze(ws, ctx):
                start = d.range.start_offset - base
                end = d.range.end_offset - base
                if start < 0 or d.rule not in RULE_CATEGORY:
                    continue
                preds.append(Prediction(span=(start, min(end, len(item.text))),
                                        category=RULE_CATEGORY[d.rule]))
        return preds
```

`src/ttoryeot/bench/harness.py`의 ENGINES에 등록 (import 순환 방지를 위해 지연 임포트):
```python
def _make_ttoryeot():
    from ttoryeot.bench.adapter import TtoryeotEngine
    return TtoryeotEngine()

ENGINES["ttoryeot"] = _make_ttoryeot  # 값이 팩토리이므로 run_and_save의 `ENGINES[engine_name]()` 호출과 호환
```

- [ ] **Step 4: 어댑터 통과 확인**

Run: `uv run pytest tests/bench/test_adapter.py -q`
Expected: `2 passed`

- [ ] **Step 5: 실패하는 리포트 테스트 작성** — `tests/bench/test_report.py`

```python
import json
from pathlib import Path

from ttoryeot.bench.report import write_report


def result(engine, cat, tp, fp, fn):
    return {
        "engine": engine, "n_items": 10,
        "scores": {
            cat: {"tp": tp, "fp": fp, "fn": fn},
            "__total__": {"tp": tp, "fp": fp, "fn": fn},
        },
    }


def test_write_report(tmp_path: Path):
    (tmp_path / "baseline-regex.json").write_text(
        json.dumps(result("baseline-regex", "spacing", 5, 5, 0)))
    (tmp_path / "ttoryeot.json").write_text(
        json.dumps(result("ttoryeot", "spacing", 5, 1, 0)))
    out = write_report(tmp_path)
    md = out.read_text(encoding="utf-8")
    assert "baseline-regex" in md and "ttoryeot" in md
    assert "spacing" in md and "0.833" in md  # ttoryeot precision 5/6
```

- [ ] **Step 6: 리포트 구현** — `src/ttoryeot/bench/report.py`

```python
import json
from pathlib import Path

from ttoryeot.bench.harness import BenchResult


def write_report(results_dir: Path) -> Path:
    results = [
        BenchResult.model_validate(json.loads(p.read_text(encoding="utf-8")))
        for p in sorted(results_dir.glob("*.json"))
    ]
    lines = ["# 벤치마크 리포트", ""]
    categories = sorted({c for r in results for c in r.scores if c != "__total__"})
    header = "| engine | " + " | ".join(categories) + " | total F1 |"
    sep = "|---" * (len(categories) + 2) + "|"
    lines += ["P/R/F1 per category:", "", header, sep]
    for r in results:
        cells = []
        for cat in categories:
            s = r.scores.get(cat)
            cells.append(f"{s.precision:.3f}/{s.recall:.3f}/{s.f1:.3f}" if s else "—")
        total = r.scores["__total__"]
        lines.append(f"| {r.engine} | " + " | ".join(cells) + f" | {total.f1:.3f} |")
    out = results_dir / "report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
```

`src/ttoryeot/cli.py`의 `bench_app`에 추가:
```python
@bench_app.command()
def report(results_dir: Path = typer.Option(Path("benchmark/results"))) -> None:
    from ttoryeot.bench.report import write_report

    out = write_report(results_dir)
    typer.echo(f"리포트 생성 → {out}")
```

- [ ] **Step 7: 카테고리 대응표 + 샘플 데이터 작성**

`benchmark/data/category-map.md`:
```markdown
# 카테고리 ↔ 규칙 ↔ KAGAS 대응표

| category | 진단 rule | KAGAS 유형 (참고) | 비고 |
|---|---|---|---|
| ambiguous_reference | REF101 | (해당 없음 — 본 연구 고유) | 지시 대상 해석 위험 |
| term_inconsistency | TERM100, TERM101 | (해당 없음) | 표기 혼용 |
| term_definition_conflict | TERM102 | (해당 없음) | 문서 간 정의 충돌 |
| loanword_spelling | (베이스라인만, 1차) | WS/SPELL 계열 | 외래어 표기 |
| spacing | (베이스라인만, 1차) | WS (word spacing) | 띄어쓰기 |

조사표 도착 시 실제 오류 분류 전체로 확장한다.
```

`benchmark/data/sample-sentences.jsonl` — 실제 조사표 도착 전 데모용 소형 데이터 (7~10줄, positive/negative 짝 포함). Task 2·5의 테스트 케이스 문장을 재사용해 손으로 작성:
```json
{"id":"sent-0001","source":"seed","document_type":"fixture","context_before":"사용자 테이블과 주문 테이블을 조인합니다.","text":"해당 데이터를 저장합니다.","annotations":[{"span":[0,6],"category":"ambiguous_reference","severity":"warning","correction":"조인 결과를 저장합니다.","rationale":"선행 후보 3개","evidence":{"source":"seed","url":null},"confidence":"high"}]}
{"id":"sent-0002","source":"seed","document_type":"fixture","context_before":"조인 결과를 만듭니다.","text":"해당 결과를 저장합니다.","annotations":[]}
{"id":"sent-0003","source":"seed","document_type":"fixture","text":"리쿠르팅 존을 준비중입니다.","annotations":[{"span":[0,4],"category":"loanword_spelling","severity":"warning","correction":"리크루팅","evidence":{"source":"seed","url":null},"confidence":"high"},{"span":[7,12],"category":"spacing","severity":"warning","correction":"준비 중입니다","evidence":{"source":"seed","url":null},"confidence":"high"}]}
{"id":"sent-0004","source":"seed","document_type":"fixture","text":"리크루팅 존을 준비 중입니다.","annotations":[]}
```

- [ ] **Step 8: 전체 확인 + 엔드투엔드 스모크**

Run:
```bash
uv run pytest -q
uv run ttoryeot bench run --data benchmark/data/sample-sentences.jsonl --engine baseline-naive-ref
uv run ttoryeot bench run --data benchmark/data/sample-sentences.jsonl --engine ttoryeot
uv run ttoryeot bench report
```
Expected: 전체 테스트 통과. naive-ref는 sent-0002(정상 문장)에서 FP가 나 precision이 낮고, ttoryeot는 sent-0001만 잡아 ambiguous_reference precision이 더 높게 나온다. `benchmark/results/report.md` 생성 확인 (results JSON은 git-ignore, report.md도 결과물이므로 커밋하지 않음).

- [ ] **Step 9: Commit**

```bash
git add src/ttoryeot/bench/adapter.py src/ttoryeot/bench/report.py src/ttoryeot/bench/harness.py src/ttoryeot/cli.py tests/bench/test_adapter.py tests/bench/test_report.py benchmark/data/category-map.md benchmark/data/sample-sentences.jsonl
git commit -m "feat: 엔진 벤치 어댑터 + bench report — 베이스라인 대비 비교 파이프라인 완성"
```

---

## 완료 기준 체크 (스펙 §2)

13개 태스크 완료 시:
- 벤치마크 스키마·변환기·샘플 데이터 ✓ (Task 2, 3, 13)
- 언어 중립 IR + JSON Schema ✓ (Task 4, 7) / 파싱 파이프라인 ✓ (Task 8, 9)
- 분석 패스 2개 ✓ (Task 10, 11) / 픽스처 golden ✓ (Task 12)
- 베이스라인 대비 정량 비교 리포트 ✓ (Task 5, 6, 13)

**남는 수동 단계 (조사표 CSV 도착 후):** `benchmark/raw/`에 CSV 배치 → `columns.yaml` 작성 → `ttoryeot bench convert` → `bench run` × 4엔진 → `bench report`. 이 결과가 1차 라운드 최종 실험 리포트의 본문이 된다. 공개 오픈소스 한국어 docs 오탐률 측정(`corpus/external/`)도 이 단계에서 수행.

**스펙 대비 의도적 축소:** 픽스처는 스펙 §4.2의 5~10세트 중 이 계획에서는 1세트만 구축한다. 나머지 세트는 조사표의 실제 패턴이 확보된 뒤 같은 형식(`terms.yaml` + `expected.yaml`)으로 추가한다 — 코드 변경 없이 데이터만 늘어나며, golden 테스트는 `corpus/fixtures/*` glob으로 확장한다.




