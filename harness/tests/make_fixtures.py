#!/usr/bin/env python3
"""judge.py 검증용 fixture 생성기 (R8).

pass/ : 모든 규칙을 지킨 run. G1·G2_precheck·G2·G3 모두 위반 0건.
fail-*/ : pass를 복사한 뒤 규칙 1개만 어긴 run. expect.json에 기대 rule_id를 적는다.

    python3 harness/tests/make_fixtures.py   # harness/tests/fixtures/ 를 다시 만든다
"""
import copy
import json
import shutil
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fixtures"


def solid(c):
    return [{"type": "SOLID", "color": c}]


def text(nid, t, color="#141414", weight=400, size=15, **kw):
    n = {"node_id": nid, "type": "TEXT", "component": None, "fills": solid(color), "strokes": [],
         "radius": None, "font": {"family": "Pretendard", "weight": weight, "size": size, "letterSpacing": 0},
         "effects": [], "text": t}
    n.update(kw)
    return n


def box(nid, comp, fill, radius, **kw):
    n = {"node_id": nid, "type": "FRAME", "component": comp, "fills": solid(fill) if fill else [],
         "strokes": [], "radius": radius, "effects": [], "text": None}
    n.update(kw)
    return n


def frame_sc1(p, section):
    return {"node_id": f"{p}:1", "name": "SC1 내 자산", "section": section, "screen_id": "SC1",
            "width": 390, "height": 844, "effects": [], "nodes": [
                text(f"{p}:10", "내 자산", weight=700, size=28),
                text(f"{p}:11", "제출한 미션을 자산으로 관리해요", color="#707070", weight=300, size=17),
                box(f"{p}:12", "segmented-control", "#f3f3f3", 9999),
                box(f"{p}:13", "segmented-control-active", "#ffffff", 9999, group="visibility", text="비공개"),
                box(f"{p}:14", None, "#f3f3f3", 24),
                box(f"{p}:15", "pricing-card", "#ffffff", 24, strokes=solid("#f0f0f0")),
                box(f"{p}:16", "app-icon-squircle", "#ffffff", 12, width=40, height=40),
                {"node_id": f"{p}:17", "type": "RECTANGLE", "component": None,
                 "fills": [{"type": "IMAGE"}], "strokes": [], "radius": 16, "effects": []},
                box(f"{p}:18", "button-primary", "#141414", 9999),
                text(f"{p}:19", "판매 신청하기", color="#ffffff", weight=600),
                box(f"{p}:20", "badge-popular", "#0066ff", 9999),
            ]}


def frame_sc2(p, section):
    return {"node_id": f"{p}:2", "name": "SC2 판매 신청", "section": section, "screen_id": "SC2",
            "width": 390, "height": 844, "effects": [], "nodes": [
                text(f"{p}:30", "판매 신청", weight=700, size=28),
                box(f"{p}:31", "text-input", "#f0f0f0", 16),
                text(f"{p}:32", "개인정보가 포함되지 않았어요"),
                text(f"{p}:33", "고객정보가 포함되지 않았어요"),
                text(f"{p}:34", "회사기밀이 포함되지 않았어요"),
                text(f"{p}:35", "타인 저작물이 포함되지 않았어요"),
                text(f"{p}:36", "검수중", color="#707070", size=12),
                box(f"{p}:37", "button-outline", "#ffffff", 9999, strokes=solid("#e0e0e0")),
            ]}


def with_hashes(snap):
    for fr in snap["frames"]:
        for n in fr["nodes"]:
            n["hash"] = f"h-{n['node_id']}"
    return snap


def base():
    ks = with_hashes({"frames": [frame_sc1("1", "Keyscreen"), frame_sc2("1", "Keyscreen")]})
    build = with_hashes({"frames": [frame_sc1("2", "Build"), frame_sc2("2", "Build")]})
    build["keyscreen_hashes"] = {n["node_id"]: n["hash"] for fr in ks["frames"] for n in fr["nodes"]}
    return {
        "00-input.json": {"prd_section": "6-5", "refs": ["refs/a.png", "refs/b.png", "refs/c.png"],
                          "figma_file_url": "https://www.figma.com/design/FIXTURE/Huddling-Harness"},
        "01-analysis.json": {"prd_section": "6-5", "points": [
            {"id": "P1", "title": "상태 칩으로 자산 상태 표시", "why": "...", "refs": ["refs/a.png"]},
            {"id": "P2", "title": "공개 범위 세그먼트", "why": "...", "refs": ["refs/b.png"]},
            {"id": "P3", "title": "판매 전 체크리스트", "why": "...", "refs": ["refs/c.png", "refs/a.png"]}]},
        "02-spec.json": {"rule_scope": ["A", "B"], "screens": [
            {"id": "SC1", "name": "내 자산", "kind": "asset-list", "points": ["P1", "P2"],
             "components": ["segmented-control", "pricing-card", "button-primary"], "visibility_default": "private"},
            {"id": "SC2", "name": "판매 신청", "kind": "sale-request", "points": ["P3"],
             "components": ["text-input", "button-outline"], "states": ["검수중", "승인", "수정요청", "반려"]}]},
        "03-keyscreen-snapshot.json": ks,
        "04-build-snapshot.json": build,
        "approval.json": {"decision": "승인", "reason": None, "by": "user", "at": "2026-09-29T10:00:00+09:00"},
    }


def node(f, fname, nid):
    for fr in f[fname]["frames"]:
        for n in fr["nodes"]:
            if n["node_id"] == nid:
                return n
    raise KeyError(nid)


# 각 fail 케이스: (이름, 게이트, 기대 rule_id, 변형 함수)
def m(fn):
    return fn


CASES = []


def case(name, gate, rule):
    def deco(fn):
        CASES.append((name, gate, rule, fn))
        return fn
    return deco


# --- G1 ---
@case("fail-g1-count", "G1", "g1.points.count")
def _(f): f["01-analysis.json"]["points"] = f["01-analysis.json"]["points"][:2]

@case("fail-g1-refs", "G1", "g1.points.refs")
def _(f): f["01-analysis.json"]["points"][0]["refs"] = ["refs/missing.png"]

@case("fail-g1-section", "G1", "g1.prd_section")
def _(f): f["01-analysis.json"]["prd_section"] = "6-4"

# --- G2 사전검사 ---
@case("fail-g2-count", "G2_precheck", "g2.frames.count")
def _(f):
    f["03-keyscreen-snapshot.json"]["frames"] = f["03-keyscreen-snapshot.json"]["frames"][:1]
    f["02-spec.json"]["screens"] = f["02-spec.json"]["screens"][:1]

@case("fail-g2-match", "G2_precheck", "g2.frames.match_spec")
def _(f): f["02-spec.json"]["screens"].append({"id": "SC3", "name": "검수 결과", "kind": "sale-status"})

@case("fail-g2-size", "G2_precheck", "frame.size")
def _(f): f["03-keyscreen-snapshot.json"]["frames"][0]["height"] = 800

@case("fail-g2-shadow", "G2_precheck", "effects.shadow.count")
def _(f): node(f, "03-keyscreen-snapshot.json", "1:14")["effects"] = [{"type": "DROP_SHADOW"}]

# --- G2 승인 ---
@case("fail-g2-decision", "G2", "g2.decision")
def _(f): f["approval.json"]["decision"] = "보류"

@case("fail-g2-reason", "G2", "g2.reason")
def _(f): f["approval.json"].update(decision="반려", reason=None)

@case("fail-g2-rejected", "G2", "g2.decision")  # 형식은 맞는 반려도 통과는 아님
def _(f): f["approval.json"].update(decision="반려", reason="레이아웃/톤")

# --- G3 디자인 ---
@case("fail-color", "G3", "color.allowed")
def _(f): node(f, "04-build-snapshot.json", "2:14")["fills"] = solid("#fafafa")

@case("fail-f0f0f0", "G3", "color.f0f0f0.role")
def _(f): node(f, "04-build-snapshot.json", "2:14")["fills"] = solid("#f0f0f0")

@case("fail-accent-cta", "G3", "color.accent.not_cta")
def _(f): node(f, "04-build-snapshot.json", "2:18")["fills"] = solid("#0066ff")

@case("fail-accent-count", "G3", "accent.per_frame")
def _(f):
    nodes = f["04-build-snapshot.json"]["frames"][0]["nodes"]
    nodes += [box("2:90", "badge-popular", "#0066ff", 9999), box("2:91", "badge-popular", "#0066ff", 9999)]

@case("fail-radius", "G3", "radius.allowed")
def _(f): node(f, "04-build-snapshot.json", "2:14")["radius"] = 12

@case("fail-font-family", "G3", "font.family")
def _(f): node(f, "04-build-snapshot.json", "2:10")["font"]["family"] = "Inter"

@case("fail-font-weight", "G3", "font.weight")
def _(f): node(f, "04-build-snapshot.json", "2:10")["font"]["weight"] = 500

@case("fail-letterspacing", "G3", "font.letterSpacing")
def _(f): node(f, "04-build-snapshot.json", "2:10")["font"]["letterSpacing"] = -0.5

@case("fail-shadow", "G3", "effects.shadow.count")
def _(f): node(f, "04-build-snapshot.json", "2:14")["effects"] = [{"type": "DROP_SHADOW"}]

@case("fail-frame-size", "G3", "frame.size")
def _(f): f["04-build-snapshot.json"]["frames"][1]["width"] = 375

@case("fail-keyscreen-locked", "G3", "keyscreen.locked")
def _(f): f["04-build-snapshot.json"]["keyscreen_hashes"]["1:10"] = "changed"

# --- G3 금지규칙 A·B ---
@case("fail-A-spec", "G3", "A.visibility_default")
def _(f): f["02-spec.json"]["screens"][0]["visibility_default"] = "public"

@case("fail-A-screen", "G3", "A.visibility_default")
def _(f): node(f, "04-build-snapshot.json", "2:13")["text"] = "멤버 공개"

@case("fail-B-states", "G3", "B.review_required")
def _(f): f["02-spec.json"]["screens"][1]["states"].remove("수정요청")

@case("fail-B-checklist", "G3", "B.review_required")
def _(f):
    fr = f["04-build-snapshot.json"]["frames"][1]
    fr["nodes"] = [n for n in fr["nodes"] if n["node_id"] != "2:34"]

@case("fail-scope-missing", "G3", "scope.declared")
def _(f): del f["02-spec.json"]["rule_scope"]


def write(d: Path, files, expect):
    d.mkdir(parents=True)
    (d / "refs").mkdir()
    for r in ("a.png", "b.png", "c.png"):
        (d / "refs" / r).write_bytes(b"")
    for name, data in files.items():
        (d / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    (d / "expect.json").write_text(json.dumps(expect, ensure_ascii=False, indent=2) + "\n")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    write(OUT / "pass", base(), [{"gate": g, "rules": []} for g in ("G1", "G2_precheck", "G2", "G3")])
    for name, gate, rule, fn in CASES:
        f = copy.deepcopy(base())
        fn(f)
        write(OUT / name, f, [{"gate": gate, "rules": [rule]}])
    print(f"fixtures: 1 pass + {len(CASES)} fail → {OUT}")


if __name__ == "__main__":
    main()
