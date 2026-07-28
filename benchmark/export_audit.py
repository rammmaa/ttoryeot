"""조사표 xlsx → bench convert용 CSV 내보내기.

당근 팀블로그 국어 품질 조사표(2026-07-26)의 '이슈 목록' 시트를
`ttoryeot bench convert`가 읽는 CSV(columns.example.yaml 헤더)로 변환한다.

- 세부 분류(49종)는 채점 가능한 벤치 버킷으로 접는다 — 대응표는 아래
  CATEGORY_BUCKETS가 단일 소스이고 benchmark/data/category-map.md에 문서화한다.
  원본 세부 분류는 '판정 이유' 앞에 [분류] 태그로 보존한다.
- 각 이슈의 수정안을 무주석(negative) 문장으로 짝지어 뒤에 붙인다 —
  스펙 §4.1의 "오류:정상 ≥ 1:1" 요구.
- 조사표 셀은 'A / B'로 복수 조각을 담는 관행이 있다 (원문 '신규 상품 런칭 / 런칭
  이후', 수정안 '론칭했습니다 / 출시했습니다'). 항목은 단일 문장이어야 하므로
  원문·수정안 모두 첫 조각만 취한다 — 그대로 두면 한 주석에 복수 발화가 걸려
  FP 아티팩트가 생긴다 (실측: 런칭 2회 등장 행 2건).

실행 (openpyxl은 프로젝트 의존성이 아니므로 --with로):
    uv run --with openpyxl python benchmark/export_audit.py <조사표.xlsx> benchmark/raw/audit.csv
"""
import csv
import sys
from collections import Counter
from pathlib import Path

CATEGORY_BUCKETS: dict[str, str] = {
    # loanword_spelling — 외래어 표기
    "외래어 표기": "loanword_spelling",
    # spacing — 띄어쓰기 계열 (예시 전수 확인: 원문↔수정안 차이가 띄어쓰기)
    "조사 띄어쓰기": "spacing", "명사구": "spacing", "보조 용언": "spacing",
    "의존 명사": "spacing", "활용형 띄어쓰기": "spacing", "합성어": "spacing",
    "합성 동사": "spacing", "보조적 구성": "spacing", "부사구": "spacing",
    "횟수 표현": "spacing", "띄어쓰기": "spacing", "직업명 띄어쓰기": "spacing",
    "단위성 명사": "spacing", "파생어": "spacing", "연결 어미": "spacing",
    "보조 용언·의존 표현": "spacing", "합성 부사": "spacing",
    "관형어 띄어쓰기": "spacing", "고유 행사명 띄어쓰기": "spacing",
    "부정 표현": "spacing", "차례 표기": "spacing",
    # term_inconsistency — 표기 통일 (TERM1xx 계열의 표적)
    "표기 통일": "term_inconsistency",
    # grammar_agreement — 조사·어미·호응
    "조사 선택": "grammar_agreement", "비표준 어미": "grammar_agreement",
    "목적격 조사": "grammar_agreement", "필수 성분 누락": "grammar_agreement",
    "주격 조사": "grammar_agreement", "병렬·호응": "grammar_agreement",
    "문장 호응": "grammar_agreement", "주술 호응": "grammar_agreement",
    "간접 의문절": "grammar_agreement", "인용 구성": "grammar_agreement",
    "인용·문장 구조": "grammar_agreement", "어미 선택": "grammar_agreement",
    "종결형 표기": "grammar_agreement", "서술어 선택": "grammar_agreement",
    "부사어 구성": "grammar_agreement", "비표준 어미·띄어쓰기": "grammar_agreement",
    # sentence_clarity — 문장 수준 리라이트
    "문장 다듬기": "sentence_clarity", "문장 구조": "sentence_clarity",
    "정보 명확성": "sentence_clarity", "문장 단절": "sentence_clarity",
    # punctuation
    "문장 부호": "punctuation", "문장 부호·공백": "punctuation",
    # typo_or_damage — 오탈자·손상·사실 오류
    "오탈자": "typo_or_damage", "표준어·오탈자": "typo_or_damage",
    "텍스트 손상": "typo_or_damage", "내용 정합성": "typo_or_damage",
}

CONFIDENCE = {"높음": "high", "중간": "medium", "낮음": "low"}

HEADERS = ["원문", "수정안", "오류 분류", "판정 이유", "근거 URL", "확신도", "출처", "문서 장르"]


def first_alternative(correction: str) -> str:
    return correction.split(" / ")[0].strip()


def export(xlsx_path: Path, out_csv: Path) -> None:
    import openpyxl

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    rows = list(wb["이슈 목록"].iter_rows(values_only=True))
    header = [str(h) for h in rows[0]]
    issues = [dict(zip(header, r)) for r in rows[1:] if any(c is not None for c in r)]

    out_rows: list[dict[str, str]] = []
    n_negative = 0
    for issue in issues:
        category = str(issue["분류"]).strip()
        if category not in CATEGORY_BUCKETS:
            raise SystemExit(f"매핑에 없는 분류: {category!r} — CATEGORY_BUCKETS를 갱신하라")
        confidence = CONFIDENCE[str(issue["확신도"]).strip()]
        base = {
            "근거 URL": str(issue["원문 URL"] or "").strip(),
            "확신도": confidence,
            "출처": str(issue["글 제목"] or "audit").strip(),
            "문서 장르": "team_blog",
        }
        text = first_alternative(str(issue["원문"]).strip())
        assert " / " not in text
        out_rows.append({
            **base,
            "원문": text,
            "수정안": first_alternative(str(issue["수정안"] or "")),
            "오류 분류": CATEGORY_BUCKETS[category],
            "판정 이유": f"[{category}] {str(issue['판정 이유'] or '').strip()}",
        })
        negative = first_alternative(str(issue["수정안"] or ""))
        if negative:
            n_negative += 1
            out_rows.append({
                **base,
                "원문": negative,
                "수정안": "",
                "오류 분류": "",  # 무주석 → 정상 문장 (오탐 측정용)
                "판정 이유": f"[정상 대조] {category} 이슈 {issue['ID']}의 수정안",
            })

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(out_rows)

    buckets = Counter(r["오류 분류"] for r in out_rows if r["오류 분류"])
    print(f"이슈 {len(issues)}건 → 오류 {len(issues)} + 정상 {n_negative} = {len(out_rows)}행")
    print("버킷 분포:", dict(buckets.most_common()))
    assert sum(buckets.values()) == len(issues)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    export(Path(sys.argv[1]), Path(sys.argv[2]))
