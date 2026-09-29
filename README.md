# Huddling 디자인 하네스

허들링 앱의 기능 하나를 골라 **레퍼런스 분석 → 화면설계 → 키스크린 → 디자인 제작 → 가이드 위반 판정**까지 이어서 진행하는 Claude Code 하네스입니다.

단계마다 전용 에이전트가 산출물을 만들고, 게이트마다 판정 스크립트(`judge.py`)가 통과 여부를 셉니다. 판정은 LLM이 아니라 스크립트가 하므로 같은 입력에는 언제나 같은 결과가 나옵니다. 사람이 개입하는 지점은 키스크린 컨셉 승인 한 곳뿐입니다.

## 완료 기준

대상 기능의 390×844 키스크린이 **2~3개** Figma에 있고, 판정 스크립트가 **design.md 위반 0건**과 **금지규칙 A·B 위반 0건**을 보고했으며, 컨셉 승인 기록이 **1건** 있으면 완료입니다.

- **금지규칙 A:** 멤버가 만든 자료는 기본 비공개다.
- **금지규칙 B:** 판매 자산은 운영자 검수를 반드시 거치며 개인정보·고객정보·회사기밀·타인 저작물을 포함할 수 없다.

## 파이프라인

```
S0 입력 ─▶ S1 분석 ─[G1]─▶ S2 설계 ─▶ S3 키스크린 ─[G2 사전검사 + 사람 승인]─▶ S4 제작 ─▶ S5 판정 ─[G3]─▶ 완료
```

| 단계 | 담당 | 출력 |
|---|---|---|
| S0 입력 | 오케스트레이터 | `00-input.json`, `state.json` |
| S1 분석 | `ref-analyst` | `01-analysis.md/.json` (반영 포인트 3~7개) |
| S2 설계 | `screen-planner` | `02-spec.md/.json` (화면 2~3개) |
| S3 키스크린 | `keyscreen-designer` | Figma `Keyscreen` 섹션, `03-keyscreen-snapshot.json` |
| S4 제작 | `builder` | Figma `Build` 섹션, `04-build-snapshot.json` |
| S5 판정 | `judge` | `05-report.json` |

| 게이트 | 통과 조건 | 실패하면 |
|---|---|---|
| G1 | 반영 포인트 수·refs·PRD 섹션 일치 | S1 |
| G2 | 사전검사(프레임 수·크기·그림자) 뒤 사람이 `승인` | 반려 `레이아웃/톤` → S3, `기능누락` → S2 |
| G3 | 위반 합계 0 | S4 |

같은 게이트에서 3번 연속 실패하면 멈추고 사람에게 넘깁니다.

## 사용법

Claude Code에서 이 폴더를 열고, 아래 메시지를 입력합니다.

| 입력 | 동작 |
|---|---|
| `하네스 시작 {섹션ID}` | 새 실행 시작 (예: `하네스 시작 6-4`) |
| `하네스 이어서` | 멈춘 단계부터 이어서 진행 |
| `하네스 승인` | 키스크린 컨셉 승인 → S4 |
| `하네스 반려 레이아웃/톤` | S3부터 다시 |
| `하네스 반려 기능누락` | S2부터 다시 |
| `하네스 판정` | S5만 다시 실행 |
| `하네스 상태` | 현재 단계, 시도 횟수, 마지막 위반 수 출력 |

### 실행 전 준비

- PRD 섹션 ID 1개 (`docs/prd.md` 기준)
- 레퍼런스 스크린샷 3~10장 (png/jpg). 실행 폴더의 `refs/`에 넣습니다.
- Figma 파일 URL (`figma_file_url`)
- Figma MCP 연결

실행 결과는 `harness/runs/{YYYYMMDD}-{섹션ID}/`에 쌓이며, git에는 올리지 않습니다.

## 강제 장치

- **쓰기 범위 제한:** `.claude/settings.json`의 PreToolUse hook(`harness/scripts/guard.py`)이 현재 단계에 맞는 `0N-*` 파일만 쓰게 합니다. 실행 중에는 `docs/`, `harness/rules.json`, `harness/scripts/`를 누구도 수정할 수 없습니다.
- **사람 승인:** `approval.json`은 사용자가 `하네스 승인/반려`를 입력했을 때만 기록됩니다. UserPromptSubmit hook(`mark_prompt.py`)이 이를 확인합니다.
- **키스크린 잠금:** 승인된 키스크린을 S4에서 건드리면 G3 규칙 `keyscreen.locked`가 노드 해시 비교로 잡아냅니다.

## 폴더 구조

```
.
├── CLAUDE.md                 오케스트레이터 규칙 (트리거, 실행 순서)
├── .claude/
│   ├── settings.json         hook 설정
│   └── agents/               단계별 에이전트 5개
├── docs/
│   ├── prd.md                허들링 앱 PRD
│   ├── story-service.md      유저스토리, 금지규칙 A·B (판정 기준)
│   ├── story-work.md         작업 흐름 원형
│   └── design.md             디자인 가이드 원문
└── harness/
    ├── rules.json            판정 규칙 SSOT (기계용)
    ├── harness-purpose.md    입력, 사용자, 완료 기준
    ├── pipeline.md           단계와 되돌아가는 지점
    ├── artifacts.md          실행 폴더 구조, 스냅샷 스키마
    ├── gates.md              게이트 통과 조건
    ├── roles.md              에이전트별 편집 범위
    ├── scripts/              judge.py, guard.py, mark_prompt.py, selfcheck.py
    └── tests/                fixture 기반 회귀 테스트, 드라이런
```

문서끼리 충돌하면 `harness/rules.json` > `harness/gates.md` > `CLAUDE.md` > 나머지 순서로 따릅니다.

## 검사 스크립트

Python 3.9 이상이 필요합니다.

```bash
python3 harness/tests/run_tests.py     # fixture별 judge.py 판정이 expect.json과 맞는지
python3 harness/tests/dryrun.py        # Figma 없이 전체 흐름에서 guard·judge 동작 확인
python3 harness/scripts/selfcheck.py   # 문서·규칙·스크립트 사이 정합성 검사
```

판정만 따로 돌릴 때:

```bash
python3 harness/scripts/judge.py {G1|G2_precheck|G3} harness/runs/{run_id}
```
