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
