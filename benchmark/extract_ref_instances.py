"""REF101 평가용 지시 표현 인스턴스 추출기.

인간 판정을 받으려면 먼저 "판정할 것"이 있어야 한다. 이 스크립트는 실제 한국어 기술
문서에서 지시 표현을 표집해, 판정자가 채워 넣을 수 있는 형식으로 내보낸다.

**표집 설계 — 엔진이 경고한 것만 모으면 안 된다.** 그러면 재현율을 잴 수 없다(엔진이
놓친 nocuous가 표본에 없다). 그래서 REF101 발화 여부와 무관하게 **모든 지시 표현**에서
표집하되, 발화/침묵 두 층에서 각각 뽑아 층화한다. 엔진 발화 여부는 `flagged.json`에
따로 저장해 채점 시 예측으로 쓴다 — 인스턴스 파일에는 넣지 않는다(판정자에게 힌트가
되면 안 되고, 엔진이 바뀌면 다시 계산해야 한다).

후보 목록은 엔진의 랭킹 상위 N개를 쓴다. 이는 판정자 부담을 줄이는 실용적 선택이지만
**엔진이 놓친 선행어는 후보에 없다**는 편향을 낳으므로, 판정 서식에 '후보에 없음'과
'잘 모르겠다' 선택지를 함께 둔다.

실행:
    uv run python benchmark/extract_ref_instances.py <문서루트> <출력.jsonl> [--n 200]
"""
import argparse
import json
import random
from pathlib import Path

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.references.analyzer import ReferenceAnalyzer
from ttoryeot.analysis.references.candidates import rank_candidates
from ttoryeot.bench.nocuity import RefInstance, save_instances
from ttoryeot.config import default_config
from ttoryeot.parsing.workspace import load_workspace

NOT_LISTED = "NOT_LISTED"  # 판정 서식의 '후보에 없음' 선택지


def collect(root: Path, window: int, top_k: int) -> tuple[list[RefInstance], set[str]]:
    """모든 지시 표현을 인스턴스로 만들고, 엔진이 경고한 id 집합을 함께 돌려준다."""
    ws = load_workspace(root)
    cfg = default_config()
    ref_cfg = cfg["reference"]
    instances: list[RefInstance] = []

    flagged_ranges = {
        (d.range.file, d.range.start_offset)
        for d in ReferenceAnalyzer().analyze(ws, AnalysisContext(config=cfg))
    }
    flagged: set[str] = set()

    for doc in ws.documents:
        recent: list = []
        for block in doc.blocks:
            if block.kind == "heading":
                recent = []
                continue
            for sent in block.sentences:
                for ref in sent.references:
                    ranked = rank_candidates(
                        ref, recent[-window:], ref_cfg["weights"]
                    )
                    seen, unique = set(), []
                    for c in ranked:
                        if c.phrase.text not in seen:
                            seen.add(c.phrase.text)
                            unique.append(c)
                    if len(unique) < 2:
                        continue  # 후보가 하나뿐이면 판정할 것이 없다
                    inst_id = f"{doc.path}#{ref.range.start_offset}"
                    instances.append(RefInstance(
                        id=inst_id,
                        doc=doc.path,
                        context=[s.text for s in recent[-window:]],
                        sentence=sent.text,
                        reference=ref.text,
                        candidates=[c.phrase.text for c in unique[:top_k]],
                    ))
                    if (doc.path, ref.range.start_offset) in flagged_ranges:
                        flagged.add(inst_id)
                recent.append(sent)
    return instances, flagged


def stratified_sample(
    instances: list[RefInstance], flagged: set[str], n: int, seed: int
) -> list[RefInstance]:
    """발화/침묵 두 층에서 절반씩 뽑는다 — 재현율을 재려면 침묵 쪽도 있어야 한다."""
    rng = random.Random(seed)
    fired = [i for i in instances if i.id in flagged]
    silent = [i for i in instances if i.id not in flagged]
    half = n // 2
    picked = rng.sample(fired, min(half, len(fired)))
    picked += rng.sample(silent, min(n - len(picked), len(silent)))
    rng.shuffle(picked)  # 판정 순서에 층 정보가 드러나지 않게
    return picked


def write_judgment_form(instances: list[RefInstance], path: Path) -> None:
    """판정자용 마크다운 서식. 각 항목에 후보 + '후보에 없음' + '잘 모르겠다'."""
    lines = [
        "# REF101 지시 대상 판정",
        "",
        "각 항목에서 **밑줄 친 지시 표현이 가리키는 것**을 하나 고르세요.",
        "정답을 맞히는 시험이 아니라 **읽는 사람마다 해석이 갈리는지**를 재는 조사입니다.",
        "확신이 안 서면 주저 말고 '잘 모르겠다'를 고르세요 — 그 응답 자체가 신호입니다.",
        "",
        "선택지를 `[ ]` → `[x]`로 바꿔 주세요.",
        "",
        "---",
        "",
    ]
    for inst in instances:
        lines.append(f"## {inst.id}")
        lines.append("")
        for c in inst.context:
            lines.append(f"> {c}")
        lines.append(f"> **{inst.sentence}**")
        lines.append("")
        lines.append(f"'{inst.reference}'이(가) 가리키는 것:")
        lines.append("")
        for c in inst.candidates:
            lines.append(f"- [ ] {c}")
        lines.append(f"- [ ] {NOT_LISTED} (후보에 없음 — 직접 적어 주세요: )")
        lines.append("- [ ] UNSURE (잘 모르겠다)")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--n", type=int, default=200, help="표집 개수 (선행연구 규모 150~200)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--window", type=int, default=None)
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    window = args.window or default_config()["reference"]["window"]
    instances, flagged = collect(args.root, window, args.top_k)
    print(f"지시 표현 인스턴스 {len(instances)}건 (엔진 발화 {len(flagged)}건)")

    picked = stratified_sample(instances, flagged, args.n, args.seed)
    save_instances(picked, args.out)
    picked_flagged = sorted(i.id for i in picked if i.id in flagged)
    args.out.with_suffix(".flagged.json").write_text(
        json.dumps(picked_flagged, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    write_judgment_form(picked, args.out.with_suffix(".form.md"))
    print(
        f"표집 {len(picked)}건 (발화 {len(picked_flagged)} / 침묵 "
        f"{len(picked) - len(picked_flagged)}) → {args.out}\n"
        f"판정 서식 → {args.out.with_suffix('.form.md')}"
    )


if __name__ == "__main__":
    main()
