#!/usr/bin/env python3
"""UserPromptSubmit hook (R7).

사람이 입력한 최근 메시지를 harness/.last-prompt.json에 남긴다.
guard.py는 이 기록으로 approval.json 쓰기가 사람 입력에서 왔는지 확인한다.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
OUT = ROOT / "harness" / ".last-prompt.json"

data = json.load(sys.stdin)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"prompt": data.get("prompt", ""), "at": time.time()}, ensure_ascii=False))
