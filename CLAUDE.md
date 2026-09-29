# Huddling 디자인 하네스 — 오케스트레이터 규칙

이 프로젝트의 메인 세션은 **하네스 오케스트레이터**다.
`하네스 …`로 시작하는 메시지는 아래 파이프라인만 따른다.
그 밖의 요청은 전역 설정(OMC)을 그대로 따른다.

## 0. 우선순위

- `하네스 …` 트리거가 오면 OMC 모드(autopilot, ralph, ultrawork, team 등)와 OMC 에이전트를 쓰지 않는다.
  쓰는 에이전트는 `.claude/agents/`의 5개(`ref-analyst`, `screen-planner`, `keyscreen-designer`, `builder`, `judge`)뿐이다.
- 문서가 서로 충돌하면 이 순서를 따른다: `harness/rules.json` > `harness/gates.md` > 이 파일 > 나머지 문서.

## 1. 참조 문서

| 문서 | 역할 |
|---|---|
| `docs/story-service.md` | 판정 기준: 유저스토리, 금지규칙 A·B |
| `docs/story-work.md` | 작업 흐름의 원형 (판정 기준 아님) |
| `docs/design.md` | 디자인 가이드 원문 (사람용) |
| `harness/rules.json` | **판정 SSOT** (기계용) |
| `harness/harness-purpose.md` | 입력, 사용자, 완료 기준 |
| `harness/pipeline.md` | 단계 S0~S5, 입출력, 돌아가는 지점 |
| `harness/artifacts.md` | 실행 폴더 구조, 파일명, 재개 |
| `harness/gates.md` | 게이트 G1·G2·G3 통과 조건 |
| `harness/roles.md` | 에이전트별 편집 범위, 트리거 |

## 2. 트리거

| 입력 | 동작 |
|---|---|
| `하네스 시작 {섹션ID}` | §3 순서로 새 실행 |
| `하네스 이어서` | 진행 중인 run의 `state.json`을 읽고 `current_stage`부터 진행 |
| `하네스 승인` | `approval.json`에 `{decision:"승인", reason:null, by:"user", at}`을 기록 → S4 |
| `하네스 반려 {레이아웃/톤\|기능누락}` | `approval.json`에 반려와 사유를 기록 → 사유가 `레이아웃/톤`이면 S3, `기능누락`이면 S2 |
| `하네스 판정` | S5만 다시 실행 |
| `하네스 상태` | run_id, current_stage, attempts, 마지막 violations.count를 출력 |

## 3. 실행 순서

1. **S0 입력 확인.** `harness/runs/{YYYYMMDD}-{섹션ID}/`를 만들고 `00-input.json`과 `state.json`을 쓴다.
   아래 중 하나라도 해당하면 **멈추고 사용자에게 요청한다.**
   - `refs/` 이미지가 3장 미만이거나 10장 초과
   - `figma_file_url`이 없음
   - 진행 중(status ≠ done)인 다른 run이 있음
2. `current_stage=S1` → `ref-analyst` 호출 → `judge.py G1` 직접 실행 → 실패하면 S1 재시도
3. `current_stage=S2` → `screen-planner` 호출
4. `current_stage=S3` → `keyscreen-designer` 호출 → `judge.py G2_precheck` 직접 실행 → 실패하면 S3 재시도
5. **사람 승인에서 멈춘다.** `awaiting_approval=true`로 두고, 키스크린 스크린샷과 Figma 링크를 보여준 뒤 턴을 끝낸다.
6. `하네스 승인`이 오면 → `current_stage=S4` → `builder` 호출
7. `current_stage=S5` → **`judge` 에이전트 호출** (G3는 반드시 judge를 거친다) → 실패하면 S4 재시도
8. G3를 통과하면 `status=done`으로 바꾸고, `harness-purpose.md` §4 완료 체크리스트를 채워 출력한다.

각 단계에 들어갈 때 **먼저 `state.json`의 `current_stage`를 갱신한 뒤** 서브에이전트를 호출한다.
guard hook이 이 값을 보고 쓰기 범위를 판단한다.

## 4. 오케스트레이터가 하지 않는 일

- `01~05` 산출물을 직접 쓰거나 고치지 않는다. 해당 단계 에이전트를 다시 호출한다.
- Figma를 편집하지 않는다.
- 판정 결과를 해석하거나, 완화하거나, 건너뛰지 않는다. 위반이 1건이라도 있으면 실패다.
- 사용자의 `하네스 승인/반려` 입력 없이 `approval.json`을 쓰지 않는다 (hook이 막는다).
- 실행 중에는 `docs/`, `harness/rules.json`, `harness/scripts/`, `.claude/`, `CLAUDE.md`를 수정하지 않는다 (hook이 막는다).

## 5. 멈춤 조건

- G2 사람 승인 대기
- 같은 게이트에서 `attempts`가 3에 도달 → `status=stopped`로 두고 마지막 위반 목록을 보여준다
- S0 입력이 규칙에 맞지 않음

## 6. 강제 장치

- `.claude/settings.json`
  - PreToolUse → `harness/scripts/guard.py`: `current_stage`에 맞는 `0N-*` 파일만 쓸 수 있다
  - UserPromptSubmit → `harness/scripts/mark_prompt.py`: 승인 입력 여부를 기록한다
- 판정: `harness/scripts/judge.py {G1|G2_precheck|G3} {run_dir}` → 결과를 `05-report.json`에 쓴다 (G3)
