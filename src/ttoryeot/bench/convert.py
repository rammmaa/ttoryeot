import csv
from pathlib import Path

import yaml

from ttoryeot.bench.schema import Annotation, Evidence, SentenceItem


_REQUIRED_MAPPING_KEYS = (
    "text", "correction", "category", "rationale",
    "evidence_url", "confidence", "source", "document_type",
)


def convert_csv(csv_path: Path, mapping_path: Path, out_path: Path) -> int:
    try:
        m = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"columns.yaml 파싱 실패: {mapping_path} ({exc})") from exc
    if not isinstance(m, dict):
        raise ValueError(f"columns.yaml 최상위는 매핑이어야 합니다: {mapping_path}")
    missing = [k for k in _REQUIRED_MAPPING_KEYS if k not in m]
    if missing:
        raise ValueError(f"columns.yaml에 누락된 키: {', '.join(missing)}")
    severity = m.get("default_severity", "warning")
    items: list[SentenceItem] = []
    with csv_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or m["text"] not in reader.fieldnames:
            raise ValueError(
                f"CSV에 원문 열 '{m['text']}'이 없습니다. "
                f"실제 헤더: {reader.fieldnames}"
            )
        for i, row in enumerate(reader, start=1):
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
                    id=f"sent-{len(items) + 1:04d}",
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
