# 역할 (R6)

> 단계: `harness/pipeline.md` · 파일: `harness/artifacts.md` · 게이트: `harness/gates.md`
> 에이전트 정의: `.claude/agents/*.md` · 쓰기 범위 강제: PreToolUse hook (R7에서 구성)

## 1. 에이전트와 편집 범위

| 에이전트 | 단계 | 편집 가능 (hook 강제) | Figma | 모델 |
|---|---|---|---|---|
| `ref-analyst` | S1 | `harness/runs/*/01-*` | 쓰기 없음 | sonnet |
| `screen-planner` | S2 | `harness/runs/*/02-*` | 쓰기 없음 | sonnet |
| `keyscreen-designer` | S3 | `harness/runs/*/03-*` | `Keyscreen` 섹션만 | opus |
| `builder` | S4 | `harness/runs/*/04-*` | `Build` 섹션만 | opus |
| `judge` | S5 | **없음** (스크립트만 `05-report.json`을 씀) | 없음 | haiku |
| 오케스트레이터 (메인 세션) | — | `harness/runs/*/state.json`, `00-input.json` | 없음 | — |

### 실행 중 누구도 쓸 수 없는 경로

- `harness/rules.json`, `harness/scripts/`, `docs/`
- `harness/runs/*/approval.json` — 예외는 하나뿐이다. 사람이 `하네스 승인` / `하네스 반려 {사유}`라고 입력했을 때, 오케스트레이터가 그 입력을 그대로 기록한다.

## 2. 읽기 전용 판정자

- 판정은 LLM이 아니라 `harness/scripts/judge.py`가 한다. 같은 스냅샷을 넣으면 언제나 같은 결과가 나온다.
- `judge` 에이전트의 도구는 `Read`와 `Bash`뿐이다. Bash는 `python3 harness/scripts/judge.py *`만 허용한다(hook으로 강제).
- `judge` 에이전트는 스크립트를 실행하고 `05-report.json`을 요약할 뿐, 판정을 바꾸거나 해석을 덧붙이지 않는다.

## 3. Keyscreen 잠금

- Figma 쓰기는 hook으로 막을 수 없으므로 G3 규칙 `keyscreen.locked`로 센다.
- `04-build-snapshot.json`에 기록된 `Keyscreen` 섹션 노드의 해시가 `03-keyscreen-snapshot.json`과 같아야 한다. 달라진 노드가 1개라도 있으면 위반이다.

## 4. 자연어 트리거

| 트리거 | 동작 |
|---|---|
| `하네스 시작 {섹션ID}` | 실행 폴더 생성 → S0 입력 확인 → S1부터 진행 |
| `하네스 이어서` | `state.json`을 읽고 멈춘 단계부터 진행 |
| `하네스 승인` / `하네스 반려 {레이아웃/톤\|기능누락}` | 사람 입력을 그대로 `approval.json`에 기록 → G2 판정 |
| `하네스 판정` | S5만 다시 실행 |
| `하네스 상태` | 현재 단계, 게이트별 시도 횟수, 마지막 위반 수를 출력 |
