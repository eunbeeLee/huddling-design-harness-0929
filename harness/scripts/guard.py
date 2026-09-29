#!/usr/bin/env python3
"""PreToolUse 쓰기 가드 (R7).

실행 중인 하네스가 있을 때, state.json의 current_stage가 허용하는 파일만 쓰게 한다.
exit 0 = 허용, exit 2 = 차단 (stderr가 Claude에게 전달된다).
실행 중인 하네스가 없으면 모든 쓰기를 허용한다.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
RUNS = ROOT / "harness" / "runs"
LAST_PROMPT = ROOT / "harness" / ".last-prompt.json"

STAGE_PREFIX = {"S1": "01-", "S2": "02-", "S3": "03-", "S4": "04-"}
ORCHESTRATOR_FILES = {"state.json", "00-input.json"}
APPROVAL_TRIGGER = re.compile(r"^\s*하네스\s*(승인|반려)")
APPROVAL_WINDOW_SEC = 600

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
BASH_WRITE_HINT = re.compile(r"(>|\btee\b|\bsed\s+-i|\brm\b|\bmv\b|\bcp\b|\btouch\b|\bchmod\b|\btruncate\b|open\(.*['\"][wa])")
JUDGE_CMD = re.compile(r"^\s*python3\s+harness/scripts/judge\.py\s")


def block(msg):
    print(f"[harness guard] 차단: {msg}", file=sys.stderr)
    sys.exit(2)


def active_run():
    """status가 done이 아닌 run 중 가장 최근 것. 없으면 None."""
    best = None
    for sp in RUNS.glob("*/state.json"):
        try:
            st = json.loads(sp.read_text())
        except Exception:
            continue
        if st.get("status") == "done":
            continue
        if best is None or sp.stat().st_mtime > best[0].stat().st_mtime:
            best = (sp, st)
    return (best[0].parent, best[1]) if best else (None, None)


def approval_allowed(st):
    if not st.get("awaiting_approval"):
        return False, "state.json의 awaiting_approval이 true가 아니다"
    try:
        lp = json.loads(LAST_PROMPT.read_text())
    except Exception:
        return False, "사용자의 '하네스 승인/반려' 입력 기록이 없다"
    if not APPROVAL_TRIGGER.match(lp.get("prompt", "")):
        return False, "최근 사용자 메시지가 '하네스 승인' 또는 '하네스 반려'가 아니다"
    if time.time() - lp.get("at", 0) > APPROVAL_WINDOW_SEC:
        return False, "승인 입력이 10분보다 오래되었다"
    return True, ""


def check_path(path: Path, run_dir, st):
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else None
    if rel is None:
        return
    rel_s = rel.as_posix()

    # 사용자 입력 플래그는 어떤 경우에도 도구로 쓸 수 없다
    if path == LAST_PROMPT:
        block("harness/.last-prompt.json은 hook만 쓴다")

    if run_dir is None:
        return  # 실행 중인 하네스 없음 → 허용

    # 실행 중 보호 경로
    if rel_s == "harness/rules.json" or rel_s.startswith("harness/scripts/") or rel_s.startswith("docs/") \
            or rel_s.startswith(".claude/") or rel_s == "CLAUDE.md":
        block(f"하네스 실행 중에는 {rel_s}을(를) 수정할 수 없다")

    if not rel_s.startswith("harness/runs/"):
        return

    if not path.is_relative_to(run_dir):
        block(f"실행 중인 run({run_dir.name}) 밖의 run 폴더에는 쓸 수 없다")

    name = path.relative_to(run_dir).as_posix()
    stage = st.get("current_stage", "")

    if name in ORCHESTRATOR_FILES:
        return
    if name == "approval.json":
        ok, why = approval_allowed(st)
        if ok:
            return
        block(f"approval.json은 사람 승인 입력으로만 쓸 수 있다 ({why})")
    if name.startswith("refs/"):
        block("refs/는 사용자가 직접 넣는다")
    if name.startswith("05-"):
        block("05-report.json은 judge.py만 쓴다")
    prefix = STAGE_PREFIX.get(stage)
    if prefix and name.startswith(prefix) and "/" not in name:
        return
    block(f"현재 단계 {stage or '(없음)'}에서는 {name}을(를) 쓸 수 없다 (허용: {prefix or '없음'}*)")


def main():
    data = json.load(sys.stdin)
    open("/private/tmp/claude-501/-Users-leeeunbee-Project-Practice-huddling-0929-design-harnes/7a43fd6a-0d3c-49cb-bf3b-046b4df03d1c/scratchpad/hooklog.jsonl","a").write(json.dumps({k:v for k,v in data.items() if k!="tool_input"})+"\n")  # DEBUG
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}
    run_dir, st = active_run()

    if tool in WRITE_TOOLS:
        fp = ti.get("file_path") or ti.get("notebook_path")
        if not fp:
            return
        p = Path(fp)
        if not p.is_absolute():
            p = Path(data.get("cwd") or ROOT) / p
        check_path(p.resolve(), run_dir, st or {})
        return

    if tool == "Bash" and run_dir is not None:
        cmd = ti.get("command", "")
        if JUDGE_CMD.match(cmd):
            return
        touches_protected = re.search(r"(harness/|docs/|\.claude/|CLAUDE\.md)", cmd)
        if touches_protected and BASH_WRITE_HINT.search(cmd):
            block("하네스 실행 중에는 Bash로 harness/·docs/·.claude/ 파일을 바꿀 수 없다 (Write/Edit를 쓰거나 judge.py만 실행)")


if __name__ == "__main__":
    main()
