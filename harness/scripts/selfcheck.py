#!/usr/bin/env python3
"""하네스 문서 정합성 검사 (R8). 불일치 개수가 0이어야 통과.

    python3 harness/scripts/selfcheck.py

검사 항목
  C1 gates.md의 rule_id  ==  rules.json의 rule_id
  C2 rules.json의 rule_id  ⊆  judge.CHECKS
  C3 에이전트 파일의 출력 파일명이 artifacts.md에 있고, 접두어가 guard.STAGE_PREFIX와 일치
  C4 guard.STAGE_PREFIX의 단계가 pipeline.md에 있음
  C5 design.md hex ⊆ rules.json color.allowed
  C6 CLAUDE.md가 참조하는 harness/ 경로가 모두 존재
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
H = ROOT / "harness"
AGENT_STAGE = {"ref-analyst": "S1", "screen-planner": "S2", "keyscreen-designer": "S3", "builder": "S4"}


def mod(name):
    spec = importlib.util.spec_from_file_location(name, H / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def rule_ids(rules):
    ids = {rules["sync"]["id"]}
    for g in rules["gates"].values():
        ids |= {r["id"] for r in g.get("rules", []) if isinstance(r, dict) and "id" in r}
    return ids | set(rules["design"]) | set(rules["service"])


def main():
    issues = []
    rules = json.loads((H / "rules.json").read_text())
    ids = rule_ids(rules)

    # C1
    gates_md = (H / "gates.md").read_text()
    md_ids = set(re.findall(r"^\| `([A-Za-z0-9_.\-]+)` \|", gates_md, re.M))
    md_ids |= set(re.findall(r"`(sync\.[a-z\-]+)`", gates_md))
    for x in sorted(ids - md_ids):
        issues.append(f"C1 gates.md에 없는 rule_id: {x}")
    for x in sorted(md_ids - ids):
        issues.append(f"C1 rules.json에 없는 rule_id: {x}")

    # C2
    judge = mod("judge")
    for x in sorted(ids - set(judge.CHECKS)):
        issues.append(f"C2 judge.py에 구현 없는 rule_id: {x}")

    # C3
    guard = mod("guard")
    artifacts = (H / "artifacts.md").read_text()
    for agent, stage in AGENT_STAGE.items():
        body = (ROOT / ".claude" / "agents" / f"{agent}.md").read_text()
        out = body.split("## 출력", 1)[-1].split("\n## ", 1)[0]
        names = set(re.findall(r"`harness/runs/\{run_id\}/(0\d-[\w\-]+\.(?:md|json))`", out))
        if not names:
            issues.append(f"C3 {agent}: 출력 파일명을 찾지 못함")
        for n in sorted(names):
            if n not in artifacts:
                issues.append(f"C3 {agent}: {n}이 artifacts.md에 없음")
            if not n.startswith(guard.STAGE_PREFIX.get(stage, "?")):
                issues.append(f"C3 {agent}: {n} 접두어가 {stage}({guard.STAGE_PREFIX.get(stage)})와 다름")

    # C4
    pipeline = (H / "pipeline.md").read_text()
    for st in guard.STAGE_PREFIX:
        if f"| {st} " not in pipeline:
            issues.append(f"C4 pipeline.md에 {st} 단계 없음")

    # C5
    design = (ROOT / "docs" / "design.md").read_text()
    hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", design)}
    allowed = {c.lower() for c in rules["design"]["color.allowed"]["allowed"]}
    for x in sorted(hexes - allowed):
        issues.append(f"C5 rules.json에 없는 design.md hex: {x}")

    # C6
    claude = (ROOT / "CLAUDE.md").read_text()
    for p in sorted(set(re.findall(r"`((?:harness|docs|\.claude)/[\w./\-]+\.(?:md|json|py))`", claude))):
        if not (ROOT / p).exists():
            issues.append(f"C6 CLAUDE.md가 참조하는 파일 없음: {p}")

    for i in issues:
        print(i)
    print(f"selfcheck: 불일치 {len(issues)}건")
    sys.exit(0 if not issues else 1)


if __name__ == "__main__":
    main()
