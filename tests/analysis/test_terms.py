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


def test_term100_reported_for_every_mixing_document(tmp_path):
    """여러 문서가 각각 내부 혼용을 갖고 있으면, 첫 문서에서 return 하지 않고
    모든 혼용 문서에 TERM100을, 나머지 순수 비정본 문서에는 TERM101을 보고해야 한다."""
    ws = make_ws(tmp_path, {
        "a.md": "데이터세트를 만듭니다.\n\n데이터셋을 저장합니다.\n",
        "b.md": "데이터세트를 조회합니다.\n\n데이터셋을 삭제합니다.\n",
        "c.md": "데이터셋을 사용합니다.\n",
    })
    diags = run(ws)

    term100_files = {d.range.file for d in diags if d.rule == "TERM100"}
    assert term100_files == {"a.md", "b.md"}

    term101_files = {d.range.file for d in diags if d.rule == "TERM101"}
    assert term101_files == {"c.md"}


def test_term102_identical_definition_is_not_flagged(tmp_path):
    """glossary.md와 정의가 완전히 동일한 문서는 오탐(false positive)이면 안 되고,
    실제로 다른 정의를 가진 문서에만 TERM102가 달려야 한다."""
    ws = make_ws(tmp_path, {
        "glossary.md": "데이터세트란 분석 가능한 논리적 테이블의 집합이다.\n",
        "guide.md": "데이터세트란 분석 가능한 논리적 테이블의 집합이다.\n",
        "pipeline.md": "데이터세트란 단일 BigQuery 테이블이다.\n",
    })
    diags = run(ws)
    term102 = [d for d in diags if d.rule == "TERM102"]
    assert len(term102) == 1
    assert term102[0].range.file == "pipeline.md"


def test_occurrence_line_col_exact_for_wrapped_sentence(tmp_path):
    """하드랩으로 줄바꿈을 걸친 문장 안의 occurrence는 문장 시작 줄 근사가 아니라
    실제 등장 줄·칸을 가리켜야 한다 (오프셋은 이전에도 정확했다)."""
    from ttoryeot.analysis.terms.dictionary import build_symbol_table

    source = "이 문서는 아주 긴 문장을 하드랩으로\n이어 쓰다가 데이터셋을 언급합니다.\n"
    ws = make_ws(tmp_path, {"a.md": source})
    table = build_symbol_table(ws, ENTRIES)
    occ = next(o for o in table["데이터세트"] if o.surface == "데이터셋")
    assert occ.range.start_line == 2
    assert occ.range.start_col == 8  # "이어 쓰다가 " 7자 다음
    assert occ.range.end_line == 2
    assert occ.range.end_col == 12
    assert source[occ.range.start_offset:occ.range.end_offset] == "데이터셋"


def test_term102_list_item_definition_conflict(tmp_path):
    """스펙 §6.2 — list_item의 `용어: 정의` 형식도 정의로 인식해 충돌을 잡아야 한다."""
    ws = make_ws(tmp_path, {
        "glossary.md": "데이터세트란 분석 가능한 논리적 테이블의 집합이다.\n",
        "guide.md": "- 데이터세트: 단일 BigQuery 테이블\n",
    })
    diags = run(ws)
    term102 = [d for d in diags if d.rule == "TERM102"]
    assert len(term102) == 1
    assert term102[0].range.file == "guide.md"


def test_term102_list_item_same_definition_not_flagged(tmp_path):
    """list_item 정의가 정본과 같은 내용이면 (어미 '이다'·마침표 차이만으로)
    충돌로 보고하면 안 된다."""
    ws = make_ws(tmp_path, {
        "glossary.md": "데이터세트란 분석 가능한 논리적 테이블의 집합이다.\n",
        "guide.md": "- 데이터세트: 분석 가능한 논리적 테이블의 집합이다.\n",
    })
    assert [d.rule for d in run(ws)] == []


def test_prose_definition_in_list_item_still_detected(tmp_path):
    """list_item 안의 프로즈형 정의('X란 …이다')는 기존대로 탐지되어야 한다."""
    ws = make_ws(tmp_path, {
        "glossary.md": "데이터세트란 분석 가능한 논리적 테이블의 집합이다.\n",
        "guide.md": "- 데이터세트란 단일 BigQuery 테이블이다.\n",
    })
    term102 = [d for d in run(ws) if d.rule == "TERM102"]
    assert len(term102) == 1
    assert term102[0].range.file == "guide.md"


def test_consistent_usage_is_clean(tmp_path):
    ws = make_ws(tmp_path, {
        "a.md": "데이터세트를 만듭니다.\n",
        "b.md": "데이터세트를 저장합니다.\n",
    })
    assert run(ws) == []


def test_term104_off_by_default_no_mixing_is_silent(tmp_path):
    ws = make_ws(tmp_path, {"a.md": "데이터셋을 저장합니다.\n"})
    assert run(ws) == []  # 혼용이 없으면 기본 설정에선 침묵


def test_term104_flags_alias_without_mixing_when_enabled(tmp_path):
    """1차 정량 실험에서 실증된 간극 — 고립 문서의 비권장 표기('오너쉽'류)는 혼용
    규칙(TERM100/101)으로 원리상 못 잡는다. terms.enforce_canonical 옵트인 시
    사전 기준으로 TERM104를 낸다."""
    ws = make_ws(tmp_path, {"a.md": "데이터셋을 저장합니다.\n"})
    diags = list(TermAnalyzer(ENTRIES).analyze(
        ws, AnalysisContext(config={"terms": {"enforce_canonical": True}})))
    assert [d.rule for d in diags] == ["TERM104"]
    assert "데이터세트" in diags[0].message


def test_term104_canonical_only_is_clean_when_enabled(tmp_path):
    ws = make_ws(tmp_path, {"a.md": "데이터세트를 저장합니다.\n"})
    diags = list(TermAnalyzer(ENTRIES).analyze(
        ws, AnalysisContext(config={"terms": {"enforce_canonical": True}})))
    assert diags == []


def test_term104_and_mixing_rules_are_orthogonal(tmp_path):
    """혼용 사실(TERM100/101)과 정책 위반(TERM104)은 별개 진단이다 — enforce가 켜진
    상태에서 혼용이 있으면 같은 occurrence에 둘 다 보고되는 것이 의도."""
    ws = make_ws(tmp_path, {"a.md": "데이터세트를 만듭니다.\n\n데이터셋을 저장합니다.\n"})
    diags = list(TermAnalyzer(ENTRIES).analyze(
        ws, AnalysisContext(config={"terms": {"enforce_canonical": True}})))
    rules = {d.rule for d in diags}
    assert {"TERM100", "TERM104"} <= rules


def test_term103_off_by_default(tmp_path):
    ws = make_ws(tmp_path, {
        "a.md": "Kafka를 씁니다. Kafka가 좋습니다.\n",
        "b.md": "Kafka를 배웁니다.\n",
    })
    assert run(ws) == []


def test_term103_flags_recurring_unknown_proper_noun(tmp_path):
    """스펙 §6.2 TERM103 — 사전에 없는 조직 고유 용어(NNP/SL 포함 명사구)가
    문서·횟수 임계 이상 반복되면 사전 등록 후보로 info 진단 (첫 등장 위치에 1건)."""
    ws = make_ws(tmp_path, {
        "a.md": "Kafka를 씁니다. Kafka가 좋습니다.\n",
        "b.md": "Kafka를 배웁니다.\n",
    })
    diags = list(TermAnalyzer(ENTRIES).analyze(
        ws, AnalysisContext(config={"terms": {"suggest_unknown": True}})))
    t103 = [d for d in diags if d.rule == "TERM103"]
    assert len(t103) == 1
    assert "Kafka" in t103[0].message
    assert t103[0].severity == "info"
    assert t103[0].range.file == "a.md"


def test_term103_respects_dictionary_thresholds_and_tags(tmp_path):
    cfg = AnalysisContext(config={"terms": {"suggest_unknown": True}})
    # 사전에 등록된 용어는 침묵
    entries = ENTRIES + [TermEntry(canonical="Kafka")]
    ws = make_ws(tmp_path / "known", {
        "a.md": "Kafka를 씁니다. Kafka가 좋습니다.\n",
        "b.md": "Kafka를 배웁니다.\n",
    })
    assert [d for d in TermAnalyzer(entries).analyze(ws, cfg)
            if d.rule == "TERM103"] == []
    # 한 문서에만 반복되면 침묵 (unknown_min_docs 기본 2)
    ws = make_ws(tmp_path / "onedoc",
                 {"a.md": "Kafka를 씁니다. Kafka가 좋습니다. Kafka도 있습니다.\n"})
    assert [d for d in TermAnalyzer(ENTRIES).analyze(ws, cfg)
            if d.rule == "TERM103"] == []
    # NNP/SL이 없는 일반 명사구는 후보가 아니다
    ws = make_ws(tmp_path / "generic", {
        "a.md": "테이블을 만듭니다. 테이블을 채웁니다.\n",
        "b.md": "테이블을 지웁니다.\n",
    })
    assert [d for d in TermAnalyzer(ENTRIES).analyze(ws, cfg)
            if d.rule == "TERM103"] == []


def test_load_dictionary(tmp_path):
    p = tmp_path / "terms.yaml"
    p.write_text(
        "terms:\n  - canonical: 데이터세트\n    aliases: [데이터셋]\n", encoding="utf-8"
    )
    entries = load_term_dictionary(p)
    assert entries[0].canonical == "데이터세트"
