#!/usr/bin/env python3
"""하네스 드라이런 (R8). Figma 없이 fixture로 CLAUDE.md §3 흐름을 따라간다.

임시 폴더에 프로젝트 사본을 만들고, 오케스트레이터가 할 일(state.json 갱신)을 흉내 내면서
각 단계에서 guard.py가 허용/차단을 맞게 하는지, judge.py 게이트가 맞게 나오는지 센다.

    python3 harness/tests/dryrun.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]
FIX = SRC / "harness" / "tests" / "fixtures"
results = []


def check(label, ok):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}")


def main():
    tmp = Path(tempfile.mkdtemp())
    for d in ("docs", "harness/scripts"):
        shutil.copytree(SRC / d, tmp / d)
    shutil.copy(SRC / "harness" / "rules.json", tmp / "harness" / "rules.json")
    run = tmp / "harness" / "runs" / "20260929-6-5"
    env = {"CLAUDE_PROJECT_DIR": str(tmp), "PATH": "/usr/bin:/bin"}

    def guard(tool, rel=None, cmd=None):
        ti = {"command": cmd} if cmd else {"file_path": str(tmp / rel)}
        p = subprocess.run([sys.executable, str(tmp / "harness/scripts/guard.py")],
                           input=json.dumps({"tool_name": tool, "tool_input": ti}), text=True,
                           capture_output=True, env=env)
        return p.returncode

    def judge(gate, run_dir=run):
        p = subprocess.run([sys.executable, str(tmp / "harness/scripts/judge.py"), gate, str(run_dir)],
                           capture_output=True, text=True)
        return p.returncode

    def state(**kw):
        sp = run / "state.json"
        st = json.loads(sp.read_text()) if sp.exists() else {}
        st.update(kw)
        sp.write_text(json.dumps(st, ensure_ascii=False))
        return st

    def put(name, fixture="pass"):
        shutil.copy(FIX / fixture / name, run / name)

    def prompt(text):
        subprocess.run([sys.executable, str(tmp / "harness/scripts/mark_prompt.py")],
                       input=json.dumps({"prompt": text}), text=True, env=env)

    # S0
    shutil.copytree(FIX / "pass" / "refs", run / "refs")
    put("00-input.json")
    state(run_id=run.name, current_stage="S0", status="running", passed_gates=[],
          attempts={"G1": 0, "G2": 0, "G3": 0}, awaiting_approval=False)
    check("S0 refs 3~10장", 3 <= len(list((run / "refs").iterdir())) <= 10)

    # S1 → G1
    state(current_stage="S1")
    check("S1 guard: 01-analysis.json 허용", guard("Write", f"harness/runs/{run.name}/01-analysis.json") == 0)
    check("S1 guard: 02-spec.json 차단", guard("Write", f"harness/runs/{run.name}/02-spec.json") == 2)
    check("S1 guard: docs/design.md 차단", guard("Edit", "docs/design.md") == 2)
    put("01-analysis.json")
    check("G1 통과", judge("G1") == 0)
    state(passed_gates=["G1"])

    # S2
    state(current_stage="S2")
    check("S2 guard: 02-spec.json 허용", guard("Write", f"harness/runs/{run.name}/02-spec.json") == 0)
    check("S2 guard: 01-analysis.json 차단", guard("Write", f"harness/runs/{run.name}/01-analysis.json") == 2)
    put("02-spec.json")

    # S3 → G2 사전검사 → 승인 대기
    state(current_stage="S3")
    check("S3 guard: 03 스냅샷 허용", guard("Write", f"harness/runs/{run.name}/03-keyscreen-snapshot.json") == 0)
    put("03-keyscreen-snapshot.json")
    check("G2 사전검사 통과", judge("G2_precheck") == 0)
    state(awaiting_approval=True)
    prompt("좋아 보이네")
    check("승인 입력 전 approval.json 차단", guard("Write", f"harness/runs/{run.name}/approval.json") == 2)
    prompt("하네스 승인")
    check("'하네스 승인' 후 approval.json 허용", guard("Write", f"harness/runs/{run.name}/approval.json") == 0)
    put("approval.json")
    check("G2 통과", judge("G2") == 0)
    state(awaiting_approval=False, passed_gates=["G1", "G2"])

    # S4 → S5 → G3 실패 3회 → 멈춤
    state(current_stage="S4")
    check("S4 guard: 03 스냅샷 차단 (승인된 컨셉 보호)",
          guard("Write", f"harness/runs/{run.name}/03-keyscreen-snapshot.json") == 2)
    check("S4 guard: 05-report.json 직접 쓰기 차단", guard("Write", f"harness/runs/{run.name}/05-report.json") == 2)
    check("S4 guard: Bash로 rules.json 수정 차단",
          guard("Bash", cmd="sed -i '' s/0/1/ harness/rules.json") == 2)
    check("S5 guard: judge.py 실행 허용",
          guard("Bash", cmd=f"python3 harness/scripts/judge.py G3 harness/runs/{run.name}") == 0)
    attempts = 0
    for fx in ("fail-A-screen", "fail-shadow", "fail-radius"):
        put("04-build-snapshot.json", fx)
        state(current_stage="S5")
        attempts += 1
        if judge("G3") != 0:
            st = state(attempts={"G1": 0, "G2": 0, "G3": attempts})
    stopped = st["attempts"]["G3"] >= 3
    if stopped:
        state(status="stopped")
    check("G3 3회 연속 실패 → stopped", stopped and json.loads((run / "state.json").read_text())["status"] == "stopped")
    report = json.loads((run / "05-report.json").read_text())
    check("05-report.json 생성, 마지막 위반=radius.allowed", report["by_rule"] == {"radius.allowed": 1})

    # 재개 → 수정본으로 G3 통과
    state(status="running", current_stage="S4", attempts={"G1": 0, "G2": 0, "G3": 0})
    put("04-build-snapshot.json")
    state(current_stage="S5")
    check("G3 통과 (수정본)", judge("G3") == 0)
    state(status="done", current_stage="DONE", passed_gates=["G1", "G2", "G3"])
    check("done 이후 rules.json 수정 허용", guard("Edit", "harness/rules.json") == 0)

    shutil.rmtree(tmp)
    print(f"\n드라이런: {sum(results)}/{len(results)} 통과")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
