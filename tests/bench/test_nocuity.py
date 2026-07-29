import pytest

from ttoryeot.bench.nocuity import (
    RefInstance,
    certainty,
    evaluate,
    is_nocuous,
    sweep,
)


def inst(judgments, id="r1", candidates=("A", "B")):
    return RefInstance(
        id=id, doc="a.md", context=["앞 문장."], sentence="해당 값을 씁니다.",
        reference="해당 값", candidates=list(candidates), judgments=list(judgments),
    )


def test_certainty_is_share_of_all_judgments_including_unsure():
    """certainty = 그 후보를 고른 판정 수 / 전체 판정 수. '잘 모르겠다'도 분모에
    들어간다 — 모르겠다는 응답 자체가 해석이 갈린다는 신호이기 때문이다
    (Chantree 2006, Yang 2011)."""
    c = certainty(["A", "A", "B", "UNSURE"])
    assert c["A"] == 0.5
    assert c["B"] == 0.25
    assert "UNSURE" not in c


def test_innocuous_requires_exactly_one_candidate_above_tau():
    # 10명 중 9명이 A → certainty 0.9
    judgments = ["A"] * 9 + ["B"]
    assert not is_nocuous(judgments, tau=0.8)
    assert is_nocuous(judgments, tau=0.95)


def test_split_judgments_are_nocuous_at_every_valid_tau():
    judgments = ["A"] * 5 + ["B"] * 5
    for tau in (0.51, 0.7, 0.9, 1.0):
        assert is_nocuous(judgments, tau=tau)


def test_tau_must_exceed_half_so_the_winner_is_unique():
    """τ ≤ 0.5면 두 후보가 동시에 임계를 넘을 수 있어 'innocuous = 승자 유일'이
    깨진다 (Yang 2011의 0.5 < τ ≤ 1.0 제약)."""
    with pytest.raises(ValueError):
        is_nocuous(["A"], tau=0.5)
    with pytest.raises(ValueError):
        is_nocuous(["A"], tau=1.5)


def test_no_judgments_is_nocuous():
    assert is_nocuous([], tau=0.7)


def test_evaluate_reports_f2_weighting_recall():
    """Yang·Ezzini 모두 F2(재현율 2배 가중)를 주지표로 쓴다 — 모호성 탐지는
    놓치는 비용이 오탐 비용보다 크다는 판단이다."""
    instances = [
        inst(["A"] * 5 + ["B"] * 5, id="n1"),   # nocuous
        inst(["A"] * 5 + ["B"] * 5, id="n2"),   # nocuous
        inst(["A"] * 10, id="i1"),              # innocuous
    ]
    # 엔진이 nocuous 하나만 맞히고 innocuous 하나를 오탐
    score = evaluate(instances, flagged={"n1", "i1"}, tau=0.7)
    assert score.tp == 1 and score.fp == 1 and score.fn == 1
    assert score.precision == 0.5
    assert score.recall == 0.5
    # F2는 recall 가중이지만 P=R이면 F1과 같다
    assert score.f2 == pytest.approx(0.5)

    perfect = evaluate(instances, flagged={"n1", "n2"}, tau=0.7)
    assert perfect.precision == 1.0 and perfect.recall == 1.0 and perfect.f2 == 1.0


def test_f2_prefers_recall_over_precision():
    instances = [inst(["A"] * 5 + ["B"] * 5, id=f"n{i}") for i in range(4)]
    instances.append(inst(["A"] * 10, id="i1"))
    high_recall = evaluate(instances, flagged={"n0", "n1", "n2", "n3", "i1"}, tau=0.7)
    high_precision = evaluate(instances, flagged={"n0"}, tau=0.7)
    assert high_recall.recall == 1.0 and high_recall.precision == 0.8
    assert high_precision.precision == 1.0 and high_precision.recall == 0.25
    assert high_recall.f2 > high_precision.f2


def test_parse_judgment_form_reads_checked_boxes():
    """판정 서식(마크다운 체크박스)을 다시 읽어 판정 분포로 되돌린다 —
    판정자는 텍스트 파일만 만지면 되고, 집계는 도구가 한다."""
    from ttoryeot.bench.nocuity import parse_judgment_form

    form = (
        "## r1\n\n> 앞 문장.\n> **해당 값을 씁니다.**\n\n"
        "'해당 값'이(가) 가리키는 것:\n\n"
        "- [x] A\n- [ ] B\n- [ ] UNSURE (잘 모르겠다)\n\n"
        "## r2\n\n"
        "- [ ] A\n- [X] B\n- [x] UNSURE (잘 모르겠다)\n"
    )
    assert parse_judgment_form(form) == {"r1": ["A"], "r2": ["B", "UNSURE"]}


def test_merge_judgments_appends_across_annotators():
    """판정자마다 서식을 하나씩 채우고, 도구가 인스턴스별로 모은다.
    집계(다수결)하지 않고 분포 그대로 쌓는다 (ChaosNLI)."""
    from ttoryeot.bench.nocuity import merge_judgments

    base = [inst([], id="r1"), inst([], id="r2")]
    merged = merge_judgments(base, [{"r1": ["A"]}, {"r1": ["B"], "r2": ["A"]}])
    by_id = {i.id: i for i in merged}
    assert by_id["r1"].judgments == ["A", "B"]
    assert by_id["r2"].judgments == ["A"]


def test_sweep_reports_every_tau():
    instances = [
        inst(["A"] * 9 + ["B"], id="a"),
        inst(["A"] * 5 + ["B"] * 5, id="b"),
    ]
    rows = sweep(instances, flagged={"b"}, taus=(0.7, 0.9, 1.0))
    assert [r.tau for r in rows] == [0.7, 0.9, 1.0]
    # τ가 오르면 nocuous로 판정되는 인스턴스가 단조 증가한다
    counts = [r.n_nocuous for r in rows]
    assert counts == sorted(counts)
