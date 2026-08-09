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


def run(ws, entries=None):
    return list(TermAnalyzer(entries or ENTRIES).analyze(ws, AnalysisContext()))


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


ADMITTED = [TermEntry(canonical="데이터세트", aliases=[
    {"surface": "데이터셋", "status": "deprecated"},
    {"surface": "데이터 세트", "status": "admitted"},
])]


def enforce(ws, entries):
    return list(TermAnalyzer(entries).analyze(
        ws, AnalysisContext(config={"terms": {"enforce_canonical": True}})))


def test_admitted_alias_is_not_flagged_as_nonpreferred(tmp_path):
    """ISO 704·TBX administrativeStatus·SKOS altLabel/hiddenLabel·Acrolinx가 공통으로
    갖는 축: '써도 되는 이표기(admitted)'와 '쓰면 안 되는 표기(deprecated)'는 다르다.
    admitted를 TERM104로 경고하면 사전에 이표기를 적는 순간 오탐이 된다."""
    ws = make_ws(tmp_path, {"a.md": "데이터 세트를 만듭니다.\n"})
    assert [d.rule for d in enforce(ws, ADMITTED)] == []


def test_deprecated_alias_is_flagged(tmp_path):
    ws = make_ws(tmp_path, {"a.md": "데이터셋을 만듭니다.\n"})
    assert [d.rule for d in enforce(ws, ADMITTED)] == ["TERM104"]


def test_string_alias_defaults_to_deprecated(tmp_path):
    """하위 호환 — 문자열 alias는 기존 동작(deprecated)을 유지한다."""
    ws = make_ws(tmp_path, {"a.md": "데이터셋을 만듭니다.\n"})
    assert [d.rule for d in enforce(ws, ENTRIES)] == ["TERM104"]


def test_admitted_alias_still_counts_as_notation_mixing(tmp_path):
    """상태 축은 TERM104(정책)만 가른다 — 혼용 사실(TERM100/101)은 그대로 보고한다."""
    ws = make_ws(tmp_path, {"a.md": "데이터세트를 만듭니다.\n\n데이터 세트를 씁니다.\n"})
    assert "TERM100" in [d.rule for d in run(ws, ADMITTED)]


def test_term_match_requires_eojeol_boundary(tmp_path):
    """'세트'가 '데이터세트' 안에서 매칭되면 안 된다 — Kiwi가 복합명사를 형태소로
    쪼개므로 토큰 경계로는 부족하고 어절 경계로 판정해야 한다. 조사는 허용."""
    from ttoryeot.analysis.terms.dictionary import build_symbol_table

    entries = [TermEntry(canonical="세트")]
    ws = make_ws(tmp_path / "compound", {"a.md": "데이터세트를 만듭니다.\n"})
    assert build_symbol_table(ws, entries)["세트"] == []

    ws = make_ws(tmp_path / "spaced", {"a.md": "세트를 만듭니다.\n"})
    assert len(build_symbol_table(ws, entries)["세트"]) == 1


def test_load_dictionary(tmp_path):
    p = tmp_path / "terms.yaml"
    p.write_text(
        "terms:\n  - canonical: 데이터세트\n    aliases: [데이터셋]\n", encoding="utf-8"
    )
    entries = load_term_dictionary(p)
    assert entries[0].canonical == "데이터세트"


# ── 다수결 빈도 증거 (LanguageTool 일관성 규칙·RedPen 관행) ──────────────────
# 대칭 '불일치'는 어느 쪽을 고칠지 말해주지 않는다. 워크스페이스 전역 빈도와
# 정본 위치를 실어 방향 있는 제안으로 만든다.


def test_term101_message_includes_both_counts(tmp_path):
    ws = make_ws(tmp_path, {
        "a.md": "데이터세트를 만듭니다.\n\n데이터세트를 저장합니다.\n",
        "b.md": "데이터셋을 저장합니다.\n",
    })
    diags = [d for d in run(ws) if d.rule == "TERM101"]
    assert len(diags) == 1
    assert "'데이터셋'(전체 1회)" in diags[0].message
    assert "'데이터세트'(전체 2회)" in diags[0].message


def test_term100_message_includes_both_counts(tmp_path):
    ws = make_ws(tmp_path, {
        "a.md": "데이터세트를 만듭니다.\n\n데이터셋을 저장합니다.\n"
    })
    diags = [d for d in run(ws) if d.rule == "TERM100"]
    assert len(diags) == 1
    assert "'데이터셋'(전체 1회)" in diags[0].message
    assert "'데이터세트'(전체 1회)" in diags[0].message


def test_term101_evidence_lists_canonical_locations(tmp_path):
    """RedPen은 오류 메시지에 모든 변이 출현 위치를 싣는다 — 수정하러 갈 곳을
    알려줘야 진단이 행동으로 이어진다. 정본 표기의 파일:줄을 evidence에 싣는다."""
    ws = make_ws(tmp_path, {
        "a.md": "데이터세트를 만듭니다.\n",
        "b.md": "데이터셋을 저장합니다.\n",
    })
    diags = [d for d in run(ws) if d.rule == "TERM101"]
    assert len(diags) == 1
    assert diags[0].evidence is not None
    assert "정본 '데이터세트' 위치: a.md:1" in diags[0].evidence


def test_term101_evidence_folds_beyond_three_locations(tmp_path):
    """정본 위치는 최대 3곳까지만 — 초과분은 '외 N곳'으로 접는다 (evidence가
    코퍼스 크기에 비례해 자라면 안 된다)."""
    ws = make_ws(tmp_path, {
        "a.md": "데이터세트를 만듭니다.\n\n데이터세트를 저장합니다.\n",
        "b.md": "데이터세트를 조회합니다.\n",
        "c.md": "데이터세트를 삭제합니다.\n",
        "d.md": "데이터셋을 사용합니다.\n",
    })
    diags = [d for d in run(ws) if d.rule == "TERM101"]
    assert len(diags) == 1
    ev = diags[0].evidence
    # 정렬(문서·줄) 기준 처음 3곳만 보이고 나머지는 접힌다
    assert "a.md:1" in ev and "a.md:3" in ev and "b.md:1" in ev
    assert "c.md:1" not in ev
    assert "외 1곳" in ev


def test_minority_canonical_direction_follows_dictionary_with_notice(tmp_path):
    """사전의 canonical이 전역 빈도상 소수여도 방향은 사전을 따른다 — 사전이
    정책이다. 다만 evidence의 주의 문구로 사전 재검토를 유도한다."""
    ws = make_ws(tmp_path, {
        "a.md": "데이터셋을 만듭니다. 데이터셋을 저장합니다.\n\n데이터셋을 조회합니다.\n",
        "b.md": "데이터세트를 사용합니다.\n",
    })
    diags = [d for d in run(ws) if d.rule == "TERM101"]
    # 진단은 여전히 alias('데이터셋') 위치에 달린다 — 다수라고 정본이 되지 않는다
    assert diags and all(d.range.file == "a.md" for d in diags)
    assert all(
        "주의: 정본 표기가 소수(1회 vs 3회)입니다" in d.evidence for d in diags
    )


def test_frequency_evidence_does_not_move_diagnostic_positions(tmp_path):
    """메시지·evidence 보강은 표시 계층의 변화일 뿐 — 진단의 rule/file/line
    (픽스처 golden의 비교 계약)은 불변이어야 한다."""
    ws = make_ws(tmp_path, {
        "a.md": "데이터세트를 만듭니다.\n\n데이터셋을 저장합니다.\n",
        "c.md": "데이터셋을 사용합니다.\n",
    })
    got = {(d.rule, d.range.file, d.range.start_line) for d in run(ws)}
    assert got == {("TERM100", "a.md", 3), ("TERM101", "c.md", 1)}


def test_frequency_counts_are_scoped_as_workspace_wide(tmp_path):
    """검증 리뷰 지적 — 전역 빈도를 '같은 문서에서 혼용됩니다' 문장 안에 그대로
    실으면 문서 내 빈도로 오독된다. '전체' 스코프 표식을 붙인다."""
    ws = make_ws(tmp_path, {
        "a.md": "데이터세트를 만듭니다.\n\n데이터셋을 저장합니다.\n",
        "b.md": "데이터세트를 봅니다. 데이터세트를 씁니다.\n",
    })
    t100 = [d for d in run(ws) if d.rule == "TERM100"]
    assert t100 and "(전체 1회)" in t100[0].message and "(전체 3회)" in t100[0].message


def test_evidence_locations_are_deduped_by_file_and_line(tmp_path):
    """검증 리뷰 지적 — 정본이 한 줄에 여러 번 등장하면 같은 file:line이 3칸 예산을
    다 소모해 다른 파일이 '외 N곳' 뒤로 접힌다. 표시 단위가 file:line이므로 같은
    키는 하나로 접는다."""
    ws = make_ws(tmp_path, {
        "a.md": "데이터세트와 데이터세트와 데이터세트를 봅니다.\n",
        "b.md": "데이터세트를 씁니다.\n",
        "c.md": "데이터셋을 저장합니다.\n",
    })
    t101 = [d for d in run(ws) if d.rule == "TERM101"]
    assert t101
    ev = t101[0].evidence
    assert "a.md:1 · b.md:1" in ev
    assert "외" not in ev.split("주의")[0]  # 중복 접힘이 없으면 '외 N곳'이 필요 없다


def test_absent_canonical_gets_distinct_message(tmp_path):
    """검증 리뷰 지적 — 정본이 코퍼스에 0회면 \"'데이터세트'(전체 0회) 표기와
    불일치\"는 자기모순 문장이다. 문형을 분기한다."""
    ws = make_ws(tmp_path, {
        "a.md": "데이터셋을 저장합니다.\n",
        "b.md": "데이터 세트를 만듭니다.\n",
    })
    diags = [d for d in run(ws) if d.rule in ("TERM100", "TERM101")]
    assert diags
    for d in diags:
        assert "0회) 표기와" not in d.message
        assert "표기가 코퍼스에 등장하지 않습니다" in d.message
