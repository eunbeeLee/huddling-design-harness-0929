# 게이트 (R5)

> 판정 SSOT: `harness/rules.json` (이 문서는 사람용 설명이며, 값이 다르면 rules.json이 우선한다)
> 파일 위치: `harness/artifacts.md` · 단계: `harness/pipeline.md`

## 0. 판정 시작 전: 동기화 검사

- `sync.design-hex`: `docs/design.md`의 hex가 모두 `color.allowed`에 있어야 한다. 누락이 1개라도 있으면 판정을 시작하지 않는다.

## 1. G1 — 분석 → 설계 (기계)

대상: `01-analysis.json`

| id | 통과 조건 |
|---|---|
| `g1.points.count` | 반영 포인트 3 ≤ n ≤ 7 |
| `g1.points.refs` | 모든 포인트에 `refs` 1개 이상, 파일이 `refs/`에 실제로 있음 |
| `g1.prd_section` | `00-input.json`의 `prd_section`과 같음 |

실패 → S1

## 2. G2 — 키스크린 → 제작 (기계 사전검사 + 사람 승인)

### 2-1. 사전검사 (기계, 사람에게 보내기 전)

대상: `03-keyscreen-snapshot.json`

| id | 통과 조건 |
|---|---|
| `g2.frames.count` | 프레임 2 ≤ n ≤ 3 |
| `g2.frames.match_spec` | 프레임 수 = `02-spec.json` 화면 수 |
| `frame.size` | 모든 프레임 390×844 |
| `effects.shadow.count` | 그림자 0개 |

실패 → S3 (사람에게 보내지 않음)

### 2-2. 사람 승인 (하네스 전체에서 유일한 사람 승인 지점)

대상: `approval.json` — **사람만 작성한다. 에이전트의 쓰기는 PreToolUse hook이 막는다.**

| id | 통과 조건 |
|---|---|
| `g2.decision` | `승인` 또는 `반려` |
| `g2.reason` | `반려`이면 `레이아웃/톤` 또는 `기능누락` 중 하나 (비어 있으면 실패) |
| `g2.writer` | `approval.json`은 사람 입력으로만 기록 (judge가 아니라 `guard.py`가 강제) |

- `승인` → S4
- `반려` + `레이아웃/톤` → S3
- `반려` + `기능누락` → S2

## 3. G3 — 최종 판정 (기계)

대상: `04-build-snapshot.json`, `02-spec.json` · 통과: **위반 합계 = 0** · 실패 → S4 (S3는 다시 열지 않음)

### 3-1. 디자인 규칙 (design.md)

| id | 통과 조건 |
|---|---|
| `color.allowed` | 모든 fill·stroke·text 색이 허용 목록 10개 안 (이미지 노드 제외) |
| `color.f0f0f0.role` | #f0f0f0 fill은 입력창에만, 1px stroke는 카드에만 |
| `color.accent.not_cta` | #0066ff가 버튼 fill에 쓰인 노드 0개 |
| `accent.per_frame` | 프레임당 #0066ff 노드 ≤ 2 |
| `radius.allowed` | 0 / 16 / 24 / 9999만 (앱 아이콘만 30% 예외) |
| `font.family` | Pretendard |
| `font.weight` | 300 / 400 / 600 / 700 |
| `font.letterSpacing` | 0 |
| `effects.shadow.count` | 0 |
| `frame.size` | 390×844 |
| `keyscreen.locked` | S4 이후 `Keyscreen` 섹션 노드 해시가 `03-keyscreen-snapshot.json`과 모두 일치 (R6에서 추가) |

### 3-2. ★ 금지규칙 (story-service.md A·B)

| id | 설계 검사 (`02-spec.json`) | 화면 검사 (스냅샷) |
|---|---|---|
| `A.visibility_default` | `visibility_default`가 있으면 값은 `"private"`만 | 공개범위 컨트롤의 활성 옵션 텍스트 = `비공개` |
| `B.review_required` | 판매 신청 화면 `states` ⊇ {검수중, 승인, 수정요청, 반려} | 판매 신청 화면에 {개인정보, 고객정보, 회사기밀, 타인 저작물} 텍스트가 모두 있음 |
| `scope.declared` | `rule_scope` 배열이 있음 (빈 배열 = 해당 없음을 명시) | — |

- A·B 검사는 `rule_scope`에 해당 문자가 있을 때만 적용한다.
- `rule_scope` 자체가 없으면 위반이다 (해당 없음도 명시해야 한다).

## 4. 재시도

- 같은 게이트에서 3번 연속 실패하면 멈추고 사람에게 넘긴다 (`state.json`의 `attempts`).
