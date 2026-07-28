# Round-2 백로그 소진 + 외부 코퍼스 측정 + 1차 정량 실험 핸드오프 (2026-07-28)

> 전체 그림은 [세션 요약](2026-07-28-session-summary.md)이 더 짧다. 이 문서는 항목별 상세.

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

## Round-2 본론 (같은 날 후속 작업, `round2-core` 브랜치) — 전부 구현 완료

| 항목 | 내용 |
|---|---|
| 인라인 코드 마스킹 (스펙 §5) | 코드 스팬을 길이 보존 공백으로 치환해 Kiwi 입력에서만 제외 — 식별자 유입·코드 내 마침표 문장 분절 해소, 오프셋 불변 |
| REF101 구조 참조·담화 지시 억제 | `reference.suppress_heads` config 리스트 (외부 실측 표본 근거). '이 글'·'위 예시 앱'·'이 방법'류 침묵 |
| REF101 튜닝 챕터 (스펙 §6.3) | `benchmark/sweep_ref101.py` 스윕 → 기본값 확정 (th 0.2 · head_match 0.45). **발견: threshold 단독 튜닝은 절벽** (0.15에서 시드 recall 0). 외부 발화율 round-1 대비 fe-news −57%(12.5/1k줄)·react −39%(당시 8.8/1k줄, round-3 명사 런 수정 후 8.7 — 튜닝 챕터 주석 참조), 가드 불변. [튜닝 챕터](../research/2026-07-28-ref101-tuning.md) |
| TERM104 (비권장 표기, opt-in) | `terms.enforce_canonical` — 혼용 없는 고립 문서의 '오너쉽'류 (TERM103은 스펙 미지 용어 규칙용 예약) |
| 픽스처 5세트 | data-platform + notation-mix(표기 통일 패턴) + canonical-enforce(TERM104, 픽스처별 config.yaml 지원) + structural-clean(억제·마스킹 무오탐 가드) + definition-conflict(TERM102 list_item) — golden 파라미터라이즈 |

## Round-3 (같은 날 후속, `round3-core` 브랜치) — 완료

| 항목 | 내용 |
|---|---|
| TERM103 (opt-in) | 사전에 없는 조직 고유 용어 후보 제안 (NNP/SL 명사구, 3회·2문서 임계) — `terms.suggest_unknown`, unknown-terms 픽스처 |
| 마스킹 브리지 결함 수정 | 코드 밀집 왕복 property 테스트(리뷰 권고)가 적발 — 명사 런이 마스킹 공백을 건너뛰어 코드가 구 텍스트로 재유입되던 것을 런 간격 1자 제한으로 수정 |
| 3번째 장르 (k8s ko) | 레퍼런스·운영 장르 22.7/1,000줄 — 어휘 갭('예제' → 목록 보완)과 도메인 개체 지시 밀집이 원인. [재판정 문서](../research/2026-07-28-round3-residual-judgment.md) |
| 잔존 표본 재판정 (n=28) | 전부 실질 오탐 — 목록·점수 조정의 한계 도달, round-4는 추출·유형 분류(비교 '동일한'·접속 '그 결과'·자기 참조) 정제가 지렛대 |
| 억제 비용 표본 (n=14) | 제거분 전부 올바른 억제 — 야생에서 비용 0 관측 ('해당 방법' 클래스는 드묾) |

## 다음 백로그 (round-4 후보)

1. 지시 유형 분류 정제 — 비교('동일한 X')·접속('그 결과/그 다음')·명사화 아티팩트를
   REF101에서 분리 (잔존 표본의 최대 클래스)
2. head 일치 동점 깨기 — '해당 파드' 0.90=0.90 동점류 (자명한 1위 잔존)
3. 후보 우주 확장 (링크·코드블록·제목을 선행사로) — 억제(v1)의 다음 단계
4. 구조 목록의 의미 부류 일반화 (튜토리얼·저장소·장 등 어휘 갭의 근본 대응)
5. 조사표 심각도(P2~P5) severity 매핑, TERM103을 실코퍼스 사전 성장 루프에 적용

## 스펙 정오표 추가분 (round-3 계획 시 반영)

- §6.3 점수 공식의 w5(섹션 경계 페널티)는 heading 윈도 리셋으로, w3(의미 유형 일치)는
  표면 head_match + suppress_heads 리스트로 대체 구현됨 — 실측상 충분했음
- §4.1 "조사표 분류 그대로" → 49종 세부 분류라 버킷으로 접음 (category-map.md)

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
  clone → `uv sync` → `uv run pytest -q` (110 passed)
