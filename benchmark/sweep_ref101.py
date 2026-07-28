"""REF101 튜닝 스윕 (스펙 §6.3).

그리드(threshold × weights × 억제 on/off)를 세 지표로 평가한다:
- 시드 벤치 (benchmark/data/sample-sentences.jsonl) 전체 F1 — recall 가드
- 픽스처 golden (corpus/fixtures/data-platform) 기대 진단 3종 + clean 파일 — 회귀 가드
- 외부 코퍼스 REF101 발화 건수/1,000줄 — 오탐 프록시 (라벨 없음)

코퍼스는 한 번만 파싱(load_workspace)하고 config별로 ReferenceAnalyzer만 재실행한다.

실행:
    uv run python benchmark/sweep_ref101.py [외부코퍼스경로 ...]
외부 코퍼스 경로를 주지 않으면 시드·픽스처 열만 출력한다 (코퍼스는 git-ignore라 머신 로컬).
"""
import sys
from pathlib import Path

import yaml

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.references.analyzer import ReferenceAnalyzer
from ttoryeot.analysis.terms.analyzer import TermAnalyzer
from ttoryeot.analysis.terms.dictionary import load_term_dictionary
from ttoryeot.bench.adapter import TtoryeotEngine
from ttoryeot.bench.harness import run_engine
from ttoryeot.bench.schema import load_items
from ttoryeot.parsing.workspace import load_workspace

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "corpus" / "fixtures" / "data-platform"
SEED = REPO / "benchmark" / "data" / "sample-sentences.jsonl"

# round-1 가중치를 명시적으로 고정한다 — default.yaml에 상대적으로 정의하면
# 기본값이 바뀔 때 베이스라인 행이 따라 움직여 튜닝 챕터가 재현 불가가 된다
# (자기 무효화 베이스라인).
ROUND1_WEIGHTS = {"distance": 0.4, "role": 0.25, "head_match": 0.25, "recency": 0.1}
HEAD_BOOST = {"distance": 0.3, "role": 0.15, "head_match": 0.45, "recency": 0.1}
NO_SUPPRESS = {"structural": [], "discourse": []}


def grid() -> list[tuple[str, dict]]:
    configs: list[tuple[str, dict]] = []
    configs.append(("억제 off · round-1 가중치 · th 0.2 (round-1 동작)",
                    {"reference": {"weights": ROUND1_WEIGHTS,
                                   "suppress_heads": NO_SUPPRESS}}))
    for th in (0.2, 0.15, 0.1, 0.05):
        configs.append((f"round-1 가중치 · th {th}",
                        {"reference": {"threshold": th,
                                       "weights": ROUND1_WEIGHTS}}))
    for th in (0.2, 0.15, 0.1):
        configs.append((f"head_match 0.45 · th {th}",
                        {"reference": {"threshold": th, "weights": HEAD_BOOST}}))
    return configs


def seed_f1(cfg: dict) -> tuple[float, float]:
    result = run_engine(TtoryeotEngine(config=cfg), load_items(SEED))
    ref = result.scores.get("ambiguous_reference")
    return result.scores["__total__"].f1, (ref.recall if ref else 0.0)


def fixture_ok(cfg: dict, fixture_ws, terms, expected: dict) -> bool:
    """test_golden과 같은 의미론: (rule, file, line) 삼중 완전 일치 + clean 파일 무진단.
    이보다 약하게 재면 스윕의 'fixture' 열이 진짜 golden 스위트와 어긋난다."""
    ctx = AnalysisContext(config=cfg)
    diags = list(TermAnalyzer(terms).analyze(fixture_ws, ctx))
    diags += list(ReferenceAnalyzer().analyze(fixture_ws, ctx))
    got = {(d.rule, d.range.file, d.range.start_line) for d in diags}
    want = {(e["rule"], e["file"], e["line"]) for e in expected["diagnostics"]}
    clean_ok = not any(
        d.range.file in expected["clean_files"] for d in diags
    )
    return got == want and clean_ok


def main() -> None:
    corpora = []
    for arg in sys.argv[1:]:
        path = Path(arg)
        ws = load_workspace(path)
        lines = sum(
            p.read_text(encoding="utf-8", errors="replace").count("\n")
            for p in sorted(path.rglob("*.md"))
        )
        corpora.append((path.name, ws, max(lines, 1)))
        print(f"파싱 완료: {path.name} ({lines}줄)")

    fixture_ws = load_workspace(FIXTURE)
    terms = load_term_dictionary(FIXTURE / "terms.yaml")
    expected = yaml.safe_load((FIXTURE / "expected.yaml").read_text(encoding="utf-8"))

    header = "| config | seed F1 | seed REF recall | fixture |"
    sep = "|---|---|---|---|"
    for name, _, _ in corpora:
        header += f" {name}/1k줄 |"
        sep += "---|"
    print()
    print(header)
    print(sep)
    for label, cfg in grid():
        f1, ref_recall = seed_f1(cfg)
        fx = "pass" if fixture_ok(cfg, fixture_ws, terms, expected) else "FAIL"
        row = f"| {label} | {f1:.3f} | {ref_recall:.2f} | {fx} |"
        for _, ws, lines in corpora:
            n = sum(1 for _ in ReferenceAnalyzer().analyze(
                ws, AnalysisContext(config=cfg)))
            row += f" {n} ({n / lines * 1000:.1f}) |"
        print(row)


if __name__ == "__main__":
    main()
