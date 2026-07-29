"""유해 모호성(nocuous ambiguity) 채점 — REF101의 평가 하네스.

방법론은 요구공학의 nocuous ambiguity 계보를 따른다:

- Chantree, Nuseibeh, de Roeck, Willis (RE'06) — nocuous/innocuous 개념과
  인간 판정 분포 위의 **ambiguity threshold τ**
- Yang, de Roeck, Gervasi, Willis, Nuseibeh (REJ 16(3), 2011) — 조응 표현으로 확장.
  certainty가 τ를 넘는 후보가 **정확히 하나**면 innocuous, 아니면 nocuous.
  τ 제약 `0.5 < τ ≤ 1.0`은 innocuous일 때 승자가 유일함을 보장한다
- Abualhaija 외 (ReqEval@NLP4RE 2020) — detection/resolution 분리, 저비용 라벨링
- Nie, Zhou, Bansal (EMNLP 2020, ChaosNLI) — **판정을 집계하지 말고 분포로 보존**

주지표는 **F2**다 (Yang·Ezzini 모두 F2). 모호성 탐지는 놓치는 비용이 오탐 비용보다
크다는 판단이며, 또렷의 고재현율 지향과도 정합적이다.
"""
import json
import re
from pathlib import Path

from pydantic import BaseModel

#: 판정자가 "어느 것인지 모르겠다"를 고른 경우. 분모에는 들어가되 어떤 후보의
#: certainty도 올리지 않는다 — 모르겠다는 응답 자체가 해석 분기의 신호다.
UNSURE = "UNSURE"


class RefInstance(BaseModel):
    """지시 표현 하나와 그에 대한 인간 판정들."""

    id: str
    doc: str
    context: list[str]          # 선행 문장 윈도 (원문 순서)
    sentence: str               # 지시 표현이 있는 문장
    reference: str              # 지시 표현 표면형
    candidates: list[str]       # 판정자에게 제시한 선행어 후보
    judgments: list[str] = []   # 후보 표면형 또는 UNSURE. 집계하지 않고 그대로 보존


class NocuityScore(BaseModel):
    tau: float
    tp: int = 0
    fp: int = 0
    fn: int = 0
    n_nocuous: int = 0
    n_total: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f2(self) -> float:
        p, r = self.precision, self.recall
        return 5 * p * r / (4 * p + r) if (p + r) else 0.0


def certainty(judgments: list[str]) -> dict[str, float]:
    """후보별 certainty — 그 후보를 고른 판정 수 / 전체 판정 수.

    UNSURE는 분모에만 들어간다.
    """
    total = len(judgments)
    if total == 0:
        return {}
    counts: dict[str, int] = {}
    for j in judgments:
        if j == UNSURE:
            continue
        counts[j] = counts.get(j, 0) + 1
    return {k: v / total for k, v in counts.items()}


def is_nocuous(judgments: list[str], tau: float) -> bool:
    """certainty가 τ를 넘는 후보가 정확히 하나면 innocuous, 아니면 nocuous."""
    if not 0.5 < tau <= 1.0:
        raise ValueError(f"τ는 0.5 < τ ≤ 1.0 이어야 합니다 (받은 값: {tau})")
    above = [c for c, v in certainty(judgments).items() if v >= tau]
    return len(above) != 1


def evaluate(
    instances: list[RefInstance], flagged: set[str], tau: float
) -> NocuityScore:
    """엔진이 경고한 인스턴스 집합(`flagged`)을 인간 판정 기준으로 채점한다."""
    score = NocuityScore(tau=tau, n_total=len(instances))
    for inst in instances:
        nocuous = is_nocuous(inst.judgments, tau)
        score.n_nocuous += int(nocuous)
        if nocuous and inst.id in flagged:
            score.tp += 1
        elif nocuous:
            score.fn += 1
        elif inst.id in flagged:
            score.fp += 1
    return score


def sweep(
    instances: list[RefInstance],
    flagged: set[str],
    taus: tuple[float, ...] = (0.6, 0.7, 0.8, 0.9, 1.0),
) -> list[NocuityScore]:
    """단일 임계가 아니라 곡선으로 보고한다 (SemEval-2015 T16, Yang 2011의 관행)."""
    return [evaluate(instances, flagged, tau) for tau in taus]


_HEADING = re.compile(r"^##\s+(\S+)\s*$")
_CHECKED = re.compile(r"^-\s*\[[xX]\]\s*(.+?)\s*$")


def parse_judgment_form(text: str) -> dict[str, list[str]]:
    """판정 서식(마크다운 체크박스)을 인스턴스 id → 고른 선택지 목록으로 읽는다.

    선택지 라벨의 괄호 주석("UNSURE (잘 모르겠다)")은 떼어 후보 표면형만 남긴다.
    """
    out: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.split("\n"):
        m = _HEADING.match(line)
        if m:
            current = m.group(1)
            out.setdefault(current, [])
            continue
        if current is None:
            continue
        c = _CHECKED.match(line)
        if c:
            out[current].append(c.group(1).split(" (")[0].strip())
    return {k: v for k, v in out.items() if v}


def merge_judgments(
    instances: list[RefInstance], forms: list[dict[str, list[str]]]
) -> list[RefInstance]:
    """판정자별 서식을 인스턴스에 이어 붙인다 — 집계하지 않고 분포로 보존한다."""
    merged = []
    for inst in instances:
        judgments = list(inst.judgments)
        for form in forms:
            judgments.extend(form.get(inst.id, []))
        merged.append(inst.model_copy(update={"judgments": judgments}))
    return merged


def load_instances(path: Path) -> list[RefInstance]:
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(RefInstance.model_validate_json(line))
    return out


def save_instances(instances: list[RefInstance], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for inst in instances:
            f.write(inst.model_dump_json() + "\n")


def export_schema(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ref-instance.schema.json").write_text(
        json.dumps(RefInstance.model_json_schema(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
