import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ttoryeot.bench.schema import SentenceItem, export_json_schema, load_items


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


