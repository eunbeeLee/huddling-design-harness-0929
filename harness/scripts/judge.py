#!/usr/bin/env python3
"""하네스 판정 스크립트 (R8). 읽기 전용 판정자.

사용법:
    python3 harness/scripts/judge.py {G1|G2_precheck|G2|G3} {run_dir} [--rules PATH] [--dry]

- 규칙 값은 harness/rules.json(SSOT)에서만 읽는다.
- 판정 전에 동기화 검사(sync.design-hex)를 먼저 한다.
- G3는 결과를 {run_dir}/05-report.json에 쓴다 (--dry이면 쓰지 않음).
- 종료 코드: 0 통과 · 1 위반 있음 · 2 사용법 오류·입력 파일 없음·동기화 실패
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHADOW_TYPES = {"DROP_SHADOW", "INNER_SHADOW"}
ACCENT = "#0066ff"


# ---------- 공통 ----------

def load(p: Path):
    try:
        return json.loads(p.read_text())
    except FileNotFoundError:
        fatal(f"입력 파일 없음: {p}")
    except json.JSONDecodeError as e:
        fatal(f"JSON 오류: {p} ({e})")


def fatal(msg):
    print(json.dumps({"pass": False, "error": msg}, ensure_ascii=False))
    sys.exit(2)


def norm_color(c):
    if c is None:
        return None
    return re.sub(r"\s+", "", str(c)).lower()


def paints(node, key):
    """SOLID 페인트 색 목록. IMAGE 등은 제외."""
    return [norm_color(p.get("color")) for p in node.get(key) or [] if p.get("type", "SOLID") == "SOLID"]


def all_nodes(frame):
    yield from frame.get("nodes") or []


class Report:
    def __init__(self, gate):
        self.gate = gate
        self.violations = []

    def add(self, rule_id, actual, allowed, node_id=None, frame=None):
        self.violations.append({"rule_id": rule_id, "frame": frame, "node_id": node_id,
                                "actual": actual, "allowed": allowed})

    def out(self):
        by_rule = {}
        for v in self.violations:
            by_rule[v["rule_id"]] = by_rule.get(v["rule_id"], 0) + 1
        return {"gate": self.gate, "pass": not self.violations, "count": len(self.violations),
                "by_rule": by_rule, "violations": self.violations}


# ---------- 동기화 검사 ----------

def sync_check(rules):
    design = (ROOT / rules["sources"]["design"]).read_text()
    hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", design)}
    allowed = {norm_color(c) for c in rules["design"]["color.allowed"]["allowed"]}
    missing = sorted(hexes - allowed)
    if len(missing) > rules["sync"]["max_missing"]:
        fatal(f"sync.design-hex 실패: design.md의 hex가 rules.json에 없음 {missing}")


# ---------- G1 ----------

def g1(run, rules, rep):
    a = load(run / "01-analysis.json")
    inp = load(run / "00-input.json")
    r = {x["id"]: x for x in rules["gates"]["G1"]["rules"]}
    pts = a.get("points") or []
    c = r["g1.points.count"]
    if not c["min"] <= len(pts) <= c["max"]:
        rep.add("g1.points.count", len(pts), f"{c['min']}~{c['max']}")
    for p in pts:
        refs = p.get("refs") or []
        missing = [x for x in refs if not (run / x).is_file()]
        if not refs or missing:
            rep.add("g1.points.refs", refs, "refs 1개 이상, 모두 존재", node_id=p.get("id"))
    if a.get("prd_section") != inp.get("prd_section"):
        rep.add("g1.prd_section", a.get("prd_section"), inp.get("prd_section"))


# ---------- 디자인 규칙 (프레임 단위) ----------

def check_frame_size(frame, rules, rep):
    fs = rules["design"]["frame.size"]
    if (frame.get("width"), frame.get("height")) != (fs["width"], fs["height"]):
        rep.add("frame.size", f"{frame.get('width')}x{frame.get('height')}",
                f"{fs['width']}x{fs['height']}", node_id=frame.get("node_id"), frame=frame.get("name"))


def check_shadow(frame, rules, rep):
    for n in [frame, *all_nodes(frame)]:
        for e in n.get("effects") or []:
            if e.get("type") in SHADOW_TYPES:
                rep.add("effects.shadow.count", e.get("type"), 0, node_id=n.get("node_id"), frame=frame.get("name"))


def check_design(frame, rules, rep):
    d = rules["design"]
    fname = frame.get("name")
    allowed_colors = {norm_color(c) for c in d["color.allowed"]["allowed"]}
    exempt = set(d["color.allowed"].get("exempt_node_types", []))
    role = d["color.f0f0f0.role"]
    radius_ok = set(d["radius.allowed"]["allowed"])
    squircle = {e["component"]: e["radius_ratio"] for e in d["radius.allowed"].get("exceptions", [])}
    accent_nodes = 0

    for n in all_nodes(frame):
        nid, comp, ntype = n.get("node_id"), n.get("component"), n.get("type")
        fills, strokes = paints(n, "fills"), paints(n, "strokes")

        if ntype not in exempt:
            for c in fills + strokes:
                if c not in allowed_colors:
                    rep.add("color.allowed", c, "color.allowed", nid, fname)

        if "#f0f0f0" in fills and comp not in role["fill_allowed_components"]:
            rep.add("color.f0f0f0.role", f"fill on {comp}", role["fill_allowed_components"], nid, fname)
        if "#f0f0f0" in strokes and comp not in role["stroke_allowed_components"]:
            rep.add("color.f0f0f0.role", f"stroke on {comp}", role["stroke_allowed_components"], nid, fname)

        if comp and comp.startswith("button-") and ACCENT in fills:
            rep.add("color.accent.not_cta", f"{comp} fill {ACCENT}", "button fill ≠ accent", nid, fname)
        if ACCENT in fills or ACCENT in strokes:
            accent_nodes += 1

        rad = n.get("radius")
        if rad is not None and rad not in radius_ok:
            ratio = squircle.get(comp)
            size = min(n.get("width") or 0, n.get("height") or 0)
            if not (ratio and size and abs(rad - ratio * size) <= 1):
                rep.add("radius.allowed", rad, sorted(radius_ok), nid, fname)

        f = n.get("font")
        if ntype == "TEXT" and f:
            if f.get("family") not in d["font.family"]["allowed"]:
                rep.add("font.family", f.get("family"), d["font.family"]["allowed"], nid, fname)
            if f.get("weight") not in d["font.weight"]["allowed"]:
                rep.add("font.weight", f.get("weight"), d["font.weight"]["allowed"], nid, fname)
            if f.get("letterSpacing", 0) not in d["font.letterSpacing"]["allowed"]:
                rep.add("font.letterSpacing", f.get("letterSpacing"), 0, nid, fname)

    if accent_nodes > d["accent.per_frame"]["max"]:
        rep.add("accent.per_frame", accent_nodes, f"≤{d['accent.per_frame']['max']}", frame.get("node_id"), fname)

    check_shadow(frame, rules, rep)
    check_frame_size(frame, rules, rep)


# ---------- G2 ----------

def g2_precheck(run, rules, rep):
    snap = load(run / "03-keyscreen-snapshot.json")
    spec = load(run / "02-spec.json")
    frames = snap.get("frames") or []
    c = next(x for x in rules["gates"]["G2_precheck"]["rules"] if x["id"] == "g2.frames.count")
    if not c["min"] <= len(frames) <= c["max"]:
        rep.add("g2.frames.count", len(frames), f"{c['min']}~{c['max']}")
    if len(frames) != len(spec.get("screens") or []):
        rep.add("g2.frames.match_spec", len(frames), len(spec.get("screens") or []))
    for fr in frames:
        check_frame_size(fr, rules, rep)
        check_shadow(fr, rules, rep)


def g2(run, rules, rep):
    ap = load(run / "approval.json")
    r = {x["id"]: x for x in rules["gates"]["G2"]["rules"]}
    dec = ap.get("decision")
    if dec not in r["g2.decision"]["allowed"]:
        rep.add("g2.decision", dec, r["g2.decision"]["allowed"])
    elif dec == "반려" and ap.get("reason") not in r["g2.reason"]["allowed"]:
        rep.add("g2.reason", ap.get("reason"), r["g2.reason"]["allowed"])
    elif dec == "반려":
        rep.add("g2.decision", dec, "승인")  # 형식은 맞지만 통과는 아님 → on_fail로 복귀


# ---------- G3 ----------

def g3(run, rules, rep):
    snap = load(run / "04-build-snapshot.json")
    ks = load(run / "03-keyscreen-snapshot.json")
    spec = load(run / "02-spec.json")
    frames = snap.get("frames") or []

    for fr in frames:
        check_design(fr, rules, rep)

    # keyscreen.locked
    now = snap.get("keyscreen_hashes") or {}
    for fr in ks.get("frames") or []:
        for n in all_nodes(fr):
            if now.get(n.get("node_id")) != n.get("hash"):
                rep.add("keyscreen.locked", now.get(n.get("node_id")), n.get("hash"), n.get("node_id"), fr.get("name"))

    service(spec, frames, rules, rep)


def service(spec, frames, rules, rep):
    s = rules["service"]
    if "rule_scope" not in spec or not isinstance(spec["rule_scope"], list):
        rep.add("scope.declared", None, "rule_scope 배열")
        return
    scope = set(spec["rule_scope"])
    screens = spec.get("screens") or []
    by_screen = {f.get("screen_id"): f for f in frames}

    if "A" in scope:
        vis = [sc for sc in screens if "visibility_default" in sc]
        if not vis:
            rep.add("A.visibility_default", "A 범위인데 visibility_default 화면 없음", "private")
        for sc in vis:
            if sc["visibility_default"] != "private":
                rep.add("A.visibility_default", sc["visibility_default"], "private", node_id=sc.get("id"))
            fr = by_screen.get(sc.get("id"))
            active = [n for n in all_nodes(fr or {}) if n.get("group") == "visibility"
                      and n.get("component") == "segmented-control-active"]
            if not active:
                rep.add("A.visibility_default", "공개범위 컨트롤 없음", "비공개", frame=sc.get("id"))
            for n in active:
                if (n.get("text") or "").strip() != "비공개":
                    rep.add("A.visibility_default", n.get("text"), "비공개", n.get("node_id"), sc.get("id"))

    if "B" in scope:
        b = s["B.review_required"]
        sale = [sc for sc in screens if sc.get("kind") in b["sale_kinds"]]
        if not sale:
            rep.add("B.review_required", "B 범위인데 판매 화면 없음", b["sale_kinds"])
        for sc in sale:
            miss = [x for x in b["required_states"] if x not in (sc.get("states") or [])]
            if miss:
                rep.add("B.review_required", f"states 누락 {miss}", b["required_states"], node_id=sc.get("id"))
            if sc.get("kind") == "sale-request":
                texts = " ".join(n.get("text") or "" for n in all_nodes(by_screen.get(sc.get("id")) or {}))
                miss = [x for x in b["required_checklist"] if x not in texts]
                if miss:
                    rep.add("B.review_required", f"체크리스트 누락 {miss}", b["required_checklist"], frame=sc.get("id"))


# ---------- 규칙 id → 구현 매핑 (selfcheck.py가 rules.json과 대조) ----------

CHECKS = {
    "sync.design-hex": sync_check,
    "g1.points.count": g1, "g1.points.refs": g1, "g1.prd_section": g1,
    "g2.frames.count": g2_precheck, "g2.frames.match_spec": g2_precheck,
    "g2.decision": g2, "g2.reason": g2, "g2.writer": "guard.py",
    "color.allowed": check_design, "color.f0f0f0.role": check_design, "color.accent.not_cta": check_design,
    "accent.per_frame": check_design, "radius.allowed": check_design, "font.family": check_design,
    "font.weight": check_design, "font.letterSpacing": check_design,
    "effects.shadow.count": check_shadow, "frame.size": check_frame_size,
    "keyscreen.locked": g3,
    "A.visibility_default": service, "B.review_required": service, "scope.declared": service,
}
GATES = {"G1": g1, "G2_precheck": g2_precheck, "G2": g2, "G3": g3}


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    dry = "--dry" in argv
    rules_path = ROOT / "harness" / "rules.json"
    if "--rules" in argv:
        rules_path = Path(argv[argv.index("--rules") + 1])
        args.remove(str(rules_path)) if str(rules_path) in args else None
    if len(args) != 2 or args[0] not in GATES:
        fatal("사용법: judge.py {G1|G2_precheck|G2|G3} {run_dir} [--rules PATH] [--dry]")
    gate, run = args[0], Path(args[1])
    if not run.is_dir():
        fatal(f"run 폴더 없음: {run}")

    rules = load(rules_path)
    sync_check(rules)
    rep = Report(gate)
    GATES[gate](run, rules, rep)
    out = rep.out()
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if gate == "G3" and not dry:
        (run / "05-report.json").write_text(text + "\n")
    print(text)
    sys.exit(0 if out["pass"] else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
