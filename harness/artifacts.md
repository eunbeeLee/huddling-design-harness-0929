# 산출물 (R4)

> 단계 정의: `harness/pipeline.md` · 판정 SSOT: `harness/rules.json`

## 1. 실행 폴더와 파일명

실행 1번 = 폴더 1개. 파일 이름 앞의 번호가 단계를 뜻한다.

```
harness/runs/{YYYYMMDD}-{prd섹션}/        예: 20260929-6-4/
├── refs/                        S0 사용자가 넣음 (3~10장, png/jpg)
├── 00-input.json                S0 {prd_section, refs[], figma_file_url}
├── 01-analysis.md               S1 (사람용)
├── 01-analysis.json             S1 (G1 판정용)
├── 02-spec.md                   S2 (사람용)
├── 02-spec.json                 S2 (G2·G3 판정용)
├── 03-keyscreen-snapshot.json   S3
├── approval.json                G2 {decision: 승인|반려, reason: 레이아웃/톤|기능누락|null, by, at}
├── 04-build-snapshot.json       S4
├── 05-report.json               S5
└── state.json                   진행 상태
```

| 파일 | 쓰는 쪽 | 읽는 쪽 |
|---|---|---|
| `refs/`, `00-input.json` | 사용자 | S1 |
| `01-analysis.md`, `01-analysis.json` | S1 | G1, S2 |
| `02-spec.md`, `02-spec.json` | S2 | S3, S5 |
| `03-keyscreen-snapshot.json` | S3 | G2 사전검사, S4 |
| `approval.json` | **사람만** | G2 |
| `04-build-snapshot.json` | S4 | S5 |
| `05-report.json` | S5 | G3 |
| `state.json` | 오케스트레이터 | 오케스트레이터 |

## 2. 규칙 SSOT: `harness/rules.json`

- 판정 스크립트가 읽는 규칙 파일은 이것 1개뿐이다.
- 규칙마다 `id`, `check`, `allowed`, `source`(design.md 섹션 또는 story-service A/B)를 가진다.
- 사람용 원문은 `docs/design.md`, 기계용 SSOT는 `rules.json`이다.
- **동기화 검사:** design.md에 등장하는 hex가 모두 `rules.json`의 `color.allowed`에 있어야 한다. 누락 개수가 0이 아니면 판정을 시작하지 않는다.

기본 규칙 (세부 조건과 파일 생성은 R5에서 확정):

| id | 규칙 |
|---|---|
| `color.allowed` | #141414, #0066ff, #ffffff, #f3f3f3, #f0f0f0, #e0e0e0, #262626, #707070, #adadad, rgba(115,115,115,0.56) |
| `radius.allowed` | 0, 16, 24, 9999 (앱 아이콘만 30% 예외) |
| `font.family` | Pretendard |
| `font.weight` | 300, 400, 600, 700 |
| `font.letterSpacing` | 0 |
| `effects.shadow.count` | 0 |
| `accent.per_frame` | ≤ 2 |
| `frame.size` | 390×844 |

## 3. 재개

- `state.json`: `{current_stage, passed_gates[], attempts: {G1, G2, G3}}`
- 다시 실행하면 마지막으로 통과한 게이트 다음 단계부터 이어서 한다.
- 단계를 다시 돌리면 그 단계 파일을 덮어쓰고 `attempts`만 올린다.
- 같은 게이트의 `attempts`가 3에 도달하면 멈추고 사람에게 넘긴다.

## 4. Figma 구조

- 파일 1개: `Huddling Harness`. URL은 `00-input.json`의 `figma_file_url`에 기록한다.
- 실행 1번 = 페이지 1개 (`{run_id}`).
- 페이지 안 섹션 2개:
  - `Keyscreen`: S3가 만든다. G2 승인 뒤에는 잠근다 (S4는 편집 금지).
  - `Build`: S4가 만든다.

## 5. 스냅샷 스키마 (`03-keyscreen-snapshot.json`, `04-build-snapshot.json`)

judge.py가 읽는 형식이다 (R8에서 확정).

```json
{
  "frames": [
    { "node_id": "1:2", "name": "SC1 내 자산", "section": "Keyscreen", "screen_id": "SC1",
      "width": 390, "height": 844, "effects": [],
      "nodes": [
        { "node_id": "1:3", "type": "TEXT", "component": null, "group": null,
          "fills": [{ "type": "SOLID", "color": "#141414" }], "strokes": [],
          "radius": null, "width": 358, "height": 36,
          "font": { "family": "Pretendard", "weight": 700, "size": 28, "letterSpacing": 0 },
          "effects": [], "text": "내 자산", "hash": "a1b2" }
      ] }
  ],
  "keyscreen_hashes": { "1:3": "a1b2" }
}
```

| 필드 | 규칙 |
|---|---|
| `section` | `Keyscreen`(03) 또는 `Build`(04) |
| `screen_id` | `02-spec.json`의 `screens[].id`와 일치 |
| `fills[].type` | `SOLID`만 색 검사 대상. `IMAGE` 등은 제외 |
| `component` | design.md 컴포넌트 이름 또는 `null` |
| `group` | 공개범위 컨트롤의 활성 옵션은 `"visibility"` (금지규칙 A 검사용) |
| `hash` | 노드의 시각 속성으로 만든 문자열. S3와 S4가 같은 방식으로 계산 |
| `keyscreen_hashes` | 04에만 있다. S4 종료 시점의 Keyscreen 노드 해시 |
