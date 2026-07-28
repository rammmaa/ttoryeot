# 1차 정량 실험: 조사표 벤치마크 (2026-07-28)

스펙 §2 완료 기준("벤치마크에서 두 분석 패스의 P/R을 측정하고 베이스라인과 비교한
수치가 담긴 리포트")의 트랙 1(문장 수준) 본문. 저장소 수준(트랙 2)·오탐 측정은
픽스처 golden 테스트와 [외부 코퍼스 측정](2026-07-28-external-corpus-fp.md)이 담당한다.

## 데이터

당근 채용 팀블로그 국어 품질 전수 스크리닝 조사표(2026-07-26, xlsx) '이슈 목록' 시트.

- **이슈 139건** (심각도 P2 14 · P3 104 · P4 15 · P5 6, 확신도 높음 118 · 중간 21) +
  각 이슈의 **수정안을 무주석 정상 문장으로 짝지어 139건** → 총 **278 항목** (오류:정상
  1:1 — 스펙 §4.1 요구).
- 세부 분류 49종은 채점 가능한 7개 버킷으로 접었다 (대응표:
  [category-map.md](../../benchmark/data/category-map.md), 단일 소스:
  `benchmark/export_audit.py`): spacing 67 · grammar_agreement 22 · sentence_clarity 19 ·
  loanword_spelling 17 · term_inconsistency 6 · punctuation 4 · typo_or_damage 4.
- **정제 결정:** 조사표 셀은 'A / B'로 복수 예문을 담는 관행이 있어 원문·수정안 모두
  첫 조각만 취했다. 그대로 두면 주석 1개에 발화 2회가 걸리는 FP 아티팩트가 생긴다
  (실측: '런칭' 2회 등장 행 2건 → 치환 베이스라인 P 0.933으로 왜곡).
- 조사표 항목에는 선행 문맥(context_before)이 없다 — 뒤의 해석에서 중요하다.

## 시스템 4종

| 시스템 | 정의 |
|---|---|
| baseline-subst | 조사표의 **'일괄 치환 후보' 시트 그대로**(13종) + 사전 시드 3종. 감사자가 전역 치환 안전으로 판정한 목록만 — 이슈 목록의 나머지는 감사자 스스로 문맥 의존으로 본 것('상관 없이'는 붙이고 '편향없이'는 띄는 상반 사례)이므로 규칙화하지 않는 것이 공정한 대조군 |
| baseline-regex | 시드 정규식 2종 (붙여쓴 '~중입니다', '열려있') |
| baseline-naive-ref | 지시어 표면 매칭 (해당/이/그/위 + 명사) |
| ttoryeot | 엔진 (TERM100/101/102 + REF101, 기본 config) |

## 결과 (278 항목)

| 시스템 | P | R | F1 | tp | fp | fn | 정상 문장 오발화 |
|---|---|---|---|---|---|---|---|
| baseline-subst | **1.000** | 0.201 | 0.335 | 28 | 0 | 111 | 0/139 |
| baseline-regex | 1.000 | 0.007 | 0.014 | 1 | 0 | 138 | 0/139 |
| baseline-naive-ref | 0.000 | 0.000 | 0.000 | 0 | **21** | 139 | **11/139** |
| ttoryeot | — | 0.000 | 0.000 | 0 | **0** | 139 | **0/139** |

카테고리별 (0이 아닌 것만): baseline-subst — loanword_spelling **0.941 R** (16/17,
미탐은 치환 목록에 없는 '컨셉→콘셉트' 1건) · grammar_agreement 4/22 ('-구요' 계열) ·
spacing 7/67 · typo_or_damage 1/4. baseline-regex — spacing 1/67.

## 해석

1. **목록 기반 치환의 프로필: 고정밀·저커버.** 감사자의 안전 목록은 오탐 0으로
   외래어 표기의 94%를 잡지만, 전체 오류의 20%에서 멈춘다. 커버리지의 한계가 곧
   목록의 정의다 — 목록 밖 오류('컨셉')는 구조적으로 못 잡는다.
2. **나이브 지시어 매칭의 비용.** 21회 발화 전부 오탐, 정상 문장 139개 중 11개(7.9%)
   에서 발화. 형태소·문맥 없이 지시어 표면만 보는 접근의 기대 비용을 정량화한다.
3. **엔진은 완전 침묵 (fp=0).** 두 층위의 사실이 겹친 결과다:
   - **문제 클래스 불일치 (연구 포지셔닝의 정량 확인):** 이 조사표는 어문 규범
     오류(띄어쓰기·외래어·호응 = 1차 non-goal 영역) 모음이고, 엔진의 표적(저장소
     수준 용어·참조 일관성)에 해당하는 주석이 없다. 엔진이 여기서 발화하지 않는
     것은 "낮은 오탐" 설계의 실증이다 — 표적 밖 오류 139 + 정상 139 어디서도
     오발화가 없었다 (나이브 베이스라인 21회와 대조).
   - **트랙 1의 구조적 한계:** REF101은 선행 문맥 없이 발화할 수 없고(조사표 항목엔
     context가 없음), TERM100/101은 두 표기의 공존(혼용) 없이 발화할 수 없다(고립
     문장엔 한 표기만 존재). 표기 통일 6건도 그래서 못 잡는다 — "잘못된 표기 검출"
     (사전 기준)과 "혼용 검출"(저장소 기준)은 다른 작업이며, 전자는 round-2의
     TERM104(사전 기반 비권장 표기, opt-in)로 구현됐다 — TERM103은 스펙의 '사전에
     없는 조직 고유 용어' 규칙용으로 예약. 스펙이 트랙을 둘로 나눈 이유의 실증.
4. **엔진 표적에서의 수치 (재인용):** 시드 문장(문맥 포함) F1 **0.750** vs 베이스라인
   0.286~0.333, 픽스처 golden 통과(TERM101·TERM102·REF101 + clean 파일 무오탐),
   외부 코퍼스 13.6만 줄 발화율·오탐 분석은 별도 리포트.

**연구 질문에 대한 1차 답의 구도:** 표기·서식 오류는 목록 치환으로 고정밀·저커버로
잡히고(문장 단위로 충분), 규범 문법 오류는 1차 non-goal이며, 저장소 일관성 위험은
문맥·구조 분석이 있어야만 잡히는 엔진 고유 영역이다 — 그 영역에서 엔진은 표적 데이터
F1 0.750, 표적 밖 오탐 0을 기록했다.

## 한계

- 단일 출처(한 팀블로그) 조사표 — 장르 일반화 불가
- 심각도(P2~P5) 미반영 (전부 warning으로 변환)
- 49→7 버킷팅에 판단 개입 (대응표로 공개, rationale에 원분류 보존)
- 정상 문장이 수정안 유래라 자연 분포가 아님 (오류와 같은 도메인이라는 장점은 있음)

## 재현

```bash
# 조사표 xlsx → CSV (원본은 git 외부, benchmark/raw/는 git-ignore)
uv run --with openpyxl python benchmark/export_audit.py <조사표.xlsx> benchmark/raw/audit.csv
cp benchmark/raw/columns.example.yaml benchmark/raw/columns.yaml
uv run ttoryeot bench convert benchmark/raw/audit.csv benchmark/raw/columns.yaml benchmark/data/sentences.jsonl
for e in baseline-subst baseline-regex baseline-naive-ref ttoryeot; do uv run ttoryeot bench run --engine $e; done
uv run ttoryeot bench report   # → benchmark/results/report.md
```

변환된 `benchmark/data/sentences.jsonl`(278 항목)은 커밋되어 있어 xlsx 없이도
`bench run`부터 재현 가능하다. `benchmark/results/`는 결정적 재생성 산출물이라
git 외부다(수치는 이 문서가 기록).
