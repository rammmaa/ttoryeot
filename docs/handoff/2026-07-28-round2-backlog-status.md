# Round-2 백로그 소진 + 외부 코퍼스 측정 + 1차 정량 실험 핸드오프 (2026-07-28)

> 최신 진행 상태 문서. 이전: [2026-07-27 1차 핸드오프](2026-07-27-round1-status.md) ·
> 측정 상세: [외부 코퍼스 REF101 발화율](../research/2026-07-28-external-corpus-fp.md) ·
> [1차 정량 실험](../research/2026-07-28-round1-quantitative.md)

## 현재 상태

- **1차 완료 기준(스펙 §2) 달성.** 조사표(당근 팀블로그 국어 품질 조사, 139 이슈)가
  도착해 트랙 1 벤치를 완성했다: 278 항목(오류:정상 1:1), 4개 시스템 비교, 결과는
  [1차 정량 실험 리포트](../research/2026-07-28-round1-quantitative.md).
  핵심 수치: subst P=1.000/R=0.201 · naive-ref 오탐 21(정상 문장 11) ·
  **엔진 표적 밖 완전 침묵(fp=0)** + 표적(시드) F1 0.750.
- 조사표 xlsx 원본은 사용자 iCloud에 있고 `benchmark/raw/`는 git-ignore —
  변환 산출물(`benchmark/data/sentences.jsonl` 278항목)은 커밋되어 xlsx 없이도
  `bench run`부터 재현 가능 (`benchmark/results/`는 결정적 재생성 산출물이라 git 외부).
  변환 파이프라인은 `benchmark/export_audit.py`.

- **1차 핸드오프의 Round-2 백로그 1~5번 전부 구현 완료** (`round2-backlog` 브랜치). 테스트 86/86.
- 브랜치 전체 리뷰 "With fixes" → Important 2건(아래 CLI 가드 표의 config·terms 항목)
  포함 전부 반영 완료.
- **외부 코퍼스 오탐 측정 완료** (1차 완료 기준 중 조사표 CSV가 필요 없는 항목):
  fe-news 29.0/1,000줄 · ko.react.dev 14.3/1,000줄, 무작위 표본 20건 전부 실질 오탐
  (구조 참조·담화 지시·자명한 1위). 시사점은 측정 문서 §Round-2 시사점.
- 측정이 이끈 수정 2건: 단어 중간 이/MM 지시어 기각(시드 벤치 F1 0.750 불변),
  lint 루트 부재 시 exit 2.
- 시드 벤치 스모크: 엔진 P=1.000 / R=0.600 / F1=0.750 (불변).

## 이번에 구현된 것

| 항목 | 내용 |
|---|---|
| config 단일 소스화 | 분석기 `DEFAULTS`·랭킹 `DEFAULT_WEIGHTS`가 `config/default.yaml`에서 로드됨 (드리프트 가드 테스트). `load_config(path)`는 기본값 위 딥머지 |
| config 주입 | `TtoryeotEngine(config=…)` — REF101 튜닝 스윕은 `TtoryeotEngine(config)` + `run_engine` 조합으로. CLI는 `lint --config <yaml>` |
| bench run 가드 | 미등록 엔진 → 등록 목록 안내 + exit 2. 데이터 파일 부재 → `bench convert` 안내 + exit 2 |
| lint 루트 가드 | 존재하지 않는 루트 → exit 2 (기존: 조용히 exit 0 '클린') |
| lint --terms 가드 | 없는 사전 파일 → exit 2 (기존: TermAnalyzer 조용한 탈락 = TERM 무진단 통과 위장). runner도 이제 없는 파일을 조용히 건너뛰지 않음 |
| lint --config 가드 | 없는 파일·YAML 파싱 실패·비매핑 최상위 → `ConfigError` + exit 2. 빈 섹션(`reference:`)은 '오버라이드 없음'으로 처리 (기존: 분석기 TypeError) |
| bench convert 가드 | columns.yaml 누락 키·CSV에 원문 열 부재 → 무엇이 빠졌는지 안내 + exit 2 (기존: bare KeyError) — 조사표 변환 직전 대비 |
| bench report 가드 | 결과 디렉터리 부재·결과 JSON 0개 → 안내 + exit 2 (기존: traceback / 헤더만 있는 빈 리포트) |
| CLI 테스트 | `typer.testing.CliRunner` 스모크 — lint(진단·--config)·bench run/report/convert |
| TERM 위치 정확화 | occurrence 줄·칸을 문장 내 개행 기준으로 정확 계산 (기존: 문장 시작 줄 근사, col=1 고정) |
| list_item 정의 탐지 | `- 용어: 정의` 형식도 TERM102 정의로 인식 (스펙 §6.2 잔여 항목). 어미 '이다'·마침표 차이는 정규화로 흡수 |
| 지시어 단어 경계 | 단어 중간에서 시작한 이/MM(외래어 오분해 아티팩트)은 지시어로 인정하지 않음 |

## 다음 백로그 (우선순위순, round-2 본론)

1. REF101 튜닝 챕터(스펙 §6.3) — config 스윕 경로는 마련됨. 외부 코퍼스 측정의
   threshold 민감도(0.2→0.05에서 react −44.8%)와 표본 판정을 출발점으로
2. 구조 참조 처리 — 링크·코드블록·제목을 후보 우주에 포함하거나 (위|이)+구조 head 억제.
   외부 측정 표본 기준 REF101 오탐 최대 지렛대
3. TERM104 (사전 기반 비권장 표기 검출, TERM103은 스펙의 미지 용어 규칙용 예약) —
   정량 실험에서 실증된 간극: 고립 문장의 '오너쉽'류는 혼용(TERM100/101)으로는
   원리적으로 못 잡는다. 조사표 치환 시트가 시드 사전
4. 인라인 코드 마스킹 패스 (스펙 §5 미구현, 측정에서 '이 사용 가능' 사례 실측)
5. 담화 지시 head 분류 (문제/경우/방법/원칙/변화 — 명제 선행사)
6. 픽스처 확장 (스펙 5~10세트, 현재 1세트) — 조사표 실패 패턴('상관 없이'/'편향없이'
   상반 사례, 표기 통일 계열)을 픽스처로 재구성 (스펙 §4.2)

## 주의사항 (이번에 배운 것)

- macOS `sort | uniq -c`는 한글 협착 문제로 집계가 오염된다 — 분포 집계는 Python으로
- list_item `용어: 정의` 탐지는 정의가 하드랩으로 여러 줄에 걸치면 조용히 미탐
  (오탐은 없음) — 필요해지면 개행 허용 패턴으로 확장
- 분석기의 config 읽기 계약: 자기 섹션을 `{**DEFAULTS, **(ctx.config.get("섹션") or {})}`
  로 겹쳐 읽어야 부분 주입·빈 섹션에서 안전 (`analysis/base.py` 주석 참조)
- Kiwi 분해는 문맥 의존: 같은 단어('메모이제이션')도 주변 어절에 따라 오분해 여부가
  달라진다. 회귀 테스트 문장을 바꿀 때 주의
- 외부 코퍼스는 git-ignore됨 — 재현 명령은 측정 문서 §재현

## 참고

- 원격: `https://github.com/rammmaa/ttoryeot` (프라이빗, rammmaa). 새 머신은 `gh auth login` 후
  clone → `uv sync` → `uv run pytest -q` (75 passed)
