# 파이프라인 (R3)

> 입력·완료 기준: `harness/harness-purpose.md` · 가이드 SSOT: `docs/design.md`

## 1. 단계

| 단계 | story-work | 입력 | 출력 | 다음 |
|---|---|---|---|---|
| S0 입력 | 1 (수동) | 사용자: PRD 섹션 ID 1개, `refs/` 스크린샷 3~10장 | — | S1 |
| S1 분석 | 2 | `refs/*`, `docs/prd.md` 해당 섹션 | `analysis.md`, `analysis.json` | G1 |
| S2 설계 | 3 | `analysis.json`, `docs/prd.md` 해당 섹션, `docs/story-service.md` | `spec.md`, `spec.json` | S3 |
| S3 키스크린 | 4 | `spec.json`, `docs/design.md` | Figma 키스크린 2~3개, `figma-snapshot.json` | G2 |
| S4 제작 | 6 | 승인된 키스크린, `docs/design.md` | Figma 토큰·컴포넌트·화면, `figma-snapshot.json` (갱신) | S5 |
| S5 판정 | 7 | `figma-snapshot.json`, `spec.json`, `docs/design.md`, `docs/story-service.md` | `report.json` | G3 |

## 2. 단계별 출력 규칙 (스크립트가 셀 수 있는 형태)

| 파일 | 규칙 |
|---|---|
| `analysis.json` | 반영 포인트 3~7개. 포인트마다 `refs` 파일명 1개 이상, `prd_section` 1개 |
| `spec.json` | 화면 2~3개. 화면마다 `components`에 design.md 컴포넌트 이름만 사용 |
| `figma-snapshot.json` | 프레임마다 `node_id`, `width`, `height`, `fills`, `strokes`, `radius`, `font`, `effects` 기록 |
| `report.json` | `violations` 배열과 `count`. 규칙 ID별로 개수를 집계 |

## 3. 게이트와 되돌아가는 지점

| 게이트 | 위치 | 통과 조건 | 실패하면 |
|---|---|---|---|
| G1 | S1 → S2 | `analysis.json` 규칙 충족 | S1 |
| G2 | S3 → S4 | 사람 승인 기록 `승인` 1건 | 반려 사유 `레이아웃/톤` → S3 · `기능누락` → S2 |
| G3 | S5 → 완료 | `report.json` count = 0 | S4 (S3는 다시 열지 않음) |

- 같은 게이트에서 **3번 연속 실패하면 멈추고** 사람에게 넘긴다.
- 게이트의 세부 조건은 R5에서 확정한다.

## 4. Figma 접근 원칙

- Figma를 읽고 쓰는 것은 S3·S4 에이전트만 한다 (Figma MCP `use_figma`, `get_metadata`, `get_variable_defs`).
- S5 판정 스크립트는 Figma에 접근하지 않고 `figma-snapshot.json`만 읽는다 (읽기 전용, 같은 스냅샷으로 판정을 다시 돌릴 수 있음).
- 파일 경로와 저장 위치는 R4에서 확정한다.
