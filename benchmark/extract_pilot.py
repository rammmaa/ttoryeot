"""REF101 파일럿 판정 서식 추출 — 외부 3코퍼스 층화 표집.

재생성: uv run python benchmark/extract_pilot.py
출력:   benchmark/raw/ref-eval/pilot-60.{jsonl,flagged.json,form.md}

판정자에게는 form.md 사본만 배포한다. flagged.json은 엔진 발화 id 목록으로,
채점 전까지 판정자에게 보이면 안 된다.

채점: uv run ttoryeot bench nocuity benchmark/raw/ref-eval/pilot-60.jsonl \
          판정-*.md --flagged benchmark/raw/ref-eval/pilot-60.flagged.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_ref_instances import collect, stratified_sample, write_judgment_form

from ttoryeot.bench.nocuity import save_instances
from ttoryeot.config import default_config

# 장르 층화: 뉴스레터·튜토리얼·레퍼런스
ROOTS = {
    "fe-news": "corpus/external/fe-news",
    "react": "corpus/external/ko.react.dev/src/content",
    "k8s": "corpus/external/k8s-website/content/ko",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=20, help="코퍼스당 표본 수 (발화/침묵 반반)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("benchmark/raw/ref-eval/pilot-60.jsonl"))
    args = parser.parse_args()

    window = default_config()["reference"]["window"]
    picked, flagged_all = [], set()
    for name, root in ROOTS.items():
        instances, flagged = collect(Path(root), window, top_k=5)
        sample = stratified_sample(instances, flagged, n=args.n, seed=args.seed)
        picked += sample
        flagged_all |= {i.id for i in sample if i.id in flagged}
        fired = sum(1 for i in sample if i.id in flagged)
        print(f"{name}: 전체 {len(instances)}건 중 {len(sample)} 표집 (발화 {fired}/침묵 {len(sample) - fired})")

    # 코퍼스 순서·발화 여부가 항목 배치에서 드러나지 않게 셔플 (seed 고정 → 결정적)
    random.Random(args.seed).shuffle(picked)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    save_instances(picked, args.out)
    args.out.with_suffix(".flagged.json").write_text(
        json.dumps(sorted(flagged_all), ensure_ascii=False, indent=1), encoding="utf-8"
    )
    write_judgment_form(picked, args.out.parent / f"{args.out.stem}.form.md")
    print(f"\n합계 {len(picked)}건 (엔진 발화 {len(flagged_all)}) → {args.out.parent}/")


if __name__ == "__main__":
    main()
