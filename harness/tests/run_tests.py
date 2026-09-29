#!/usr/bin/env python3
"""judge.py 회귀 테스트 (R8).

    python3 harness/tests/run_tests.py

통과 조건:
  1) 모든 fixture에서 judge가 잡은 rule_id 집합 == expect.json의 rules
  2) rules.json의 판정 규칙 id마다 fail fixture가 1개 이상 존재
  3) design.md hex가 rules.json에서 빠지면 judge가 exit 2로 판정을 거부
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JUDGE = ROOT / "harness" / "scripts" / "judge.py"
FIX = ROOT / "harness" / "tests" / "fixtures"
NOT_JUDGED = {"g2.writer"}  # guard.py가 강제 (dryrun.py에서 확인)


def judge(gate, run, rules=None):
    cmd = [sys.executable, str(JUDGE), gate, str(run), "--dry"]
    if rules:
        cmd += ["--rules", str(rules)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout or "{}")


def main():
    fails, covered, total = [], set(), 0
    for d in sorted(p for p in FIX.iterdir() if p.is_dir()):
        for exp in json.loads((d / "expect.json").read_text()):
            total += 1
            rc, out = judge(exp["gate"], d)
            got = set(out.get("by_rule", {}))
            want = set(exp["rules"])
            want_rc = 0 if not want else 1
            ok = got == want and rc == want_rc
            covered |= want
            print(f"{'PASS' if ok else 'FAIL'}  {d.name:24} {exp['gate']:12} want={sorted(want)} got={sorted(got)} rc={rc}")
            if not ok:
                fails.append(d.name)

    rules = json.loads((ROOT / "harness" / "rules.json").read_text())
    ids = {r["id"] for g in rules["gates"].values() for r in g.get("rules", []) if isinstance(r, dict) and "id" in r}
    ids |= set(rules["design"]) | set(rules["service"])
    uncovered = sorted(ids - covered - NOT_JUDGED)
    print(f"\n규칙 커버리지: {len(ids - NOT_JUDGED) - len(uncovered)}/{len(ids - NOT_JUDGED)}  누락={uncovered}")

    # 동기화 검사: design.md hex 1개를 rules에서 빼면 exit 2
    total += 1
    bad = json.loads(json.dumps(rules))
    bad["design"]["color.allowed"]["allowed"].remove("#adadad")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as t:
        json.dump(bad, t)
    rc, out = judge("G3", FIX / "pass", rules=t.name)
    sync_ok = rc == 2 and "sync.design-hex" in out.get("error", "")
    print(f"{'PASS' if sync_ok else 'FAIL'}  sync.design-hex (hex 누락 시 exit 2)  rc={rc}")
    if not sync_ok:
        fails.append("sync")

    print(f"\n결과: {total - len(fails)}/{total} 통과, 규칙 누락 {len(uncovered)}개")
    sys.exit(0 if not fails and not uncovered else 1)


if __name__ == "__main__":
    main()
