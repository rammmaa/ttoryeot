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
