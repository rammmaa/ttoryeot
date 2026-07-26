# 연구 코어 1차 핸드오프 (2026-07-27)

> 세션·머신에 종속되지 않는 진행 상태 문서. 다른 노트북에서 이어서 작업할 때 이 문서부터 읽으면 된다.
> 스펙: [specs/2026-07-26-research-core-design.md](../superpowers/specs/2026-07-26-research-core-design.md) ·
> 플랜: [plans/2026-07-26-research-core.md](../superpowers/plans/2026-07-26-research-core.md) ·
> 관련 연구: [research/2026-07-26-related-work.md](../research/2026-07-26-related-work.md)

## 현재 상태

- **연구 코어 1차 구현 완료.** 플랜의 13개 태스크 전부 구현·머지됨 (master `1084125`).
- 테스트 56/56 통과. 시드 데이터 스모크: **또렷 엔진 P=1.000 / R=0.600 / F1=0.750** vs
  베이스라인 F1 0.286~0.333 (`benchmark/data/sample-sentences.jsonl`, 8건).
- 최종 전체 브랜치 리뷰 결과 "With fixes" → must-fix 3건 + 기회성 2건 모두 반영 완료 (`b6d22bc`).

## 빠른 시작 (새 머신)

```bash
gh auth login                # rammmaa 개인 계정
git clone https://github.com/rammmaa/ttoryeot.git && cd ttoryeot
uv sync
uv run pytest -q             # 56 passed
uv run ttoryeot lint corpus/fixtures/data-platform --terms corpus/fixtures/data-platform/terms.yaml
uv run ttoryeot bench run --data benchmark/data/sample-sentences.jsonl --engine ttoryeot
uv run ttoryeot bench report
```

## 1차 완료 기준까지 남은 것 (스펙 §2)

**조사표 CSV가 유일한 재료.** 스프레드시트에서 CSV로 내려받아:

1. `benchmark/raw/`에 배치 (git-ignore됨 — 머신 간 별도 이동 필요)
2. `benchmark/raw/columns.example.yaml`을 `columns.yaml`로 복사해 실제 헤더에 맞게 수정
3. `uv run ttoryeot bench convert benchmark/raw/<파일>.csv benchmark/raw/columns.yaml benchmark/data/sentences.jsonl`
4. 4개 엔진 각각 `bench run` → `bench report` → 결과가 1차 정량 실험 리포트의 본문
5. 공개 오픈소스 한국어 docs를 `corpus/external/`에 받아 오탐/1,000줄 측정

## 최종 리뷰에서 잡혀 수정된 버그 (전부 반영 완료)

| 심각도 | 내용 | 수정 |
|---|---|---|
| Critical | 블록쿼트 내용이 block_quote+paragraph로 이중 분석 → 진단 2배 | 컨테이너 블록을 위치 전용(text="")으로 |
| Important | TERM100 조기 return이 다른 문서의 TERM100·TERM101 전부 침묵 (플랜 참조 코드 버그) | 혼용 문서 집합 수집 후 규칙별 분리 보고 |
| Important | TERM102가 정본과 동일한 정의까지 충돌로 플래그 | 정규화 정의가 다를 때만 보고 |
| Minor | Excel CSV의 BOM에서 변환기 크래시 | `utf-8-sig` |
| Minor | `benchmark/results/report.md` gitignore 누락 | 추가 |

구현 중 리뷰로 잡은 이전 버그: CSV 변환기 id 비연속(빈 행 스킵 시), 나이브 베이스라인
정규식-테스트 모순(플랜 내부 모순 — 조사 포함 (0,7)이 계약), 채점기 탐욕 매칭의 순서
의존성(→ 최대 이분 매칭으로 교체, 순서 불변성 테스트로 고정).

## 플랜 대비 의도적 편차 (전부 검증됨)

- Markdown 파싱: 플랜의 lstrip 오프셋 산술 대신 markdown-it `inline.content`를 원문에서
  재탐색 — 오프셋 불변식을 실제로 지키는 유일한 방식이었음
- Kiwi 실측: '동일한'은 동일+하+ᆫ 다중 토큰(별도 attributive 패스로 처리), '위'는 항상 NNG
  (플랜의 MM 태그 게이트는 데드 코드였음)
- 채점: 최대 이분 매칭 (플랜의 탐욕 매칭은 순서 의존)
- 나이브 지시어 베이스라인은 의도적으로 조사 포함 매칭 — 형태소 분석 대비 대조군
- REF101 후보 dedup은 head가 아닌 표면형 기준 ('사용자 테이블'/'주문 테이블' 구분)
- 샘플 데이터 8건 (플랜 예시 4건에서 확장), span 오기 [7,12]→[8,14] 수정

## 스펙 정오표 (round-2 계획 시 반영할 것)

- 플랜 Task 10 참조 코드의 TERM100 `return`과 TERM102 무조건 플래그는 버그였음 (위 표 참조)
- 스펙 §5 "인라인 코드 Kiwi 제외"는 미구현 — 오프셋 불변식과의 트레이드오프로 유입 허용 중.
  round-2에서 오프셋 보존 마스킹 패스 후보
- 스펙 §6.2 프로즈의 list_item `용어: 정의` 형식 정의 탐지는 참조 코드·테스트에 없어 미구현

## Round-2 백로그 (우선순위순)

1. `src/ttoryeot/config/default.yaml`을 러너·어댑터에 실제 연결 + `TtoryeotEngine`에 config
   주입 — **REF101 튜닝 챕터(스펙 §6.3) 전 필수.** 현재 YAML은 코드 상수와 중복(드리프트 위험)
2. `bench run` 기본 데이터 경로가 존재하지 않는 `sentences.jsonl`을 가리킴 (조사표 변환 후엔
   자연 해소되지만 그 전까지 FileNotFoundError)
3. 미등록 `--engine` 이름에 bare KeyError → 등록 엔진 목록 안내 + exit 2
4. harness/cli pytest 커버리지 (typer CliRunner 스모크)
5. list_item 정의 형식 탐지, TERM occurrence의 줄바꿈 걸친 문장 line 근사 개선
6. 픽스처 확장 (스펙은 5~10세트, 현재 1세트 — 조사표 패턴 확보 후)

## 실험 리포트에 명시할 알려진 한계

- REF101은 **같은 문장 안의 선행어를 후보로 보지 않음** ("A와 B를 조인하고 해당 데이터를…"
  은 침묵) — 윈도가 이전 문장까지만 포함하는 설계
- 인라인 코드가 Kiwi에 유입되어 식별자가 SL 명사구 후보로 등장할 수 있음
- TERM 심벌 테이블의 line/col은 문장 시작 기준 근사 (오프셋은 정확)

## 참고

- 원격: `https://github.com/rammmaa/ttoryeot` (프라이빗, 개인 계정 rammmaa).
  이 저장소의 로컬 git 설정에 개인 계정 자격증명 헬퍼가 걸려 있음 — 새 머신에서는
  `gh auth login`(rammmaa)만 하면 됨
- `.superpowers/`·`.claude/`는 세션 스크래치(머신 로컬, git 미추적) — 필요한 내용은 모두
  이 문서로 옮겨짐
- 벤치 결과 재현: 위 빠른 시작의 명령이 전부. 채점은 결정적(순서 불변)이라 숫자가 그대로
  나와야 정상
