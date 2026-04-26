from pathlib import Path

from ttoryeot.bench.convert import convert_csv
from ttoryeot.bench.schema import load_items

CSV = """원문,수정안,오류 분류,판정 이유,근거 URL,확신도,출처,문서 장르
배포 일정을 확인합니다.,배포 일정을 확인합니다.,style_check,표현 확인,,high,fixture,guide
정상 문장입니다.,,,,,high,fixture,guide
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
    assert items[0].annotations[0].category == "style_check"
    assert items[0].annotations[0].span == (0, len(items[0].text))
    # category가 비면 negative example
    assert items[1].annotations == []
    # id는 순번으로 부여
    assert items[0].id == "sent-0001" and items[1].id == "sent-0002"


def test_convert_csv_handles_bom(tmp_path: Path):
    """Excel에서 내보낸 CSV는 UTF-8 BOM('﻿')이 붙는 경우가 흔하다.
    BOM이 있어도 결과가 BOM 없는 CSV와 동일해야 한다 (첫 헤더 KeyError 금지)."""
    csv_p = tmp_path / "survey.csv"
    csv_p.write_text("﻿" + CSV, encoding="utf-8")
    map_p = tmp_path / "columns.yaml"
    map_p.write_text(MAPPING, encoding="utf-8")
    out_p = tmp_path / "sentences.jsonl"

    n = convert_csv(csv_p, map_p, out_p)

    assert n == 2
    items = load_items(out_p)
    assert items[0].annotations[0].category == "style_check"
    assert items[0].annotations[0].span == (0, len(items[0].text))
    assert items[1].annotations == []
    assert items[0].id == "sent-0001" and items[1].id == "sent-0002"


