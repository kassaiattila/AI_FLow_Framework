"""PostToolUse hook: fast tsc --noEmit on aiflow-admin/ TS edits.

Reads tool-use JSON on stdin. If the edited file is a .ts/.tsx under aiflow-admin/,
runs `npx --no-install tsc --noEmit --incremental -p tsconfig.json` in aiflow-admin/.
Non-blocking: emits a systemMessage on failure; never denies the edit.
"""

import json
import subprocess
import sys


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    resp = payload.get("tool_response") or {}
    inp = payload.get("tool_input") or {}
    file_path = (resp.get("filePath") or inp.get("file_path") or "").replace("\\", "/")

    if "aiflow-admin/" not in file_path:
        return
    if not (file_path.endswith(".ts") or file_path.endswith(".tsx")):
        return

    try:
        result = subprocess.run(
            ["npx", "--no-install", "tsc", "--noEmit", "--incremental", "-p", "tsconfig.json"],
            cwd="aiflow-admin",
            capture_output=True,
            text=True,
            timeout=28,
            shell=True,
        )
    except subprocess.TimeoutExpired:
        print(
            json.dumps(
                {
                    "systemMessage": "tsc hook timed out (>28s) — run `cd aiflow-admin && npm run type-check` manually"
                }
            )
        )
        return
    except Exception as e:
        print(json.dumps({"systemMessage": f"tsc hook skipped: {e}"}))
        return

    if result.returncode == 0:
        return

    combined = (result.stdout or "") + (result.stderr or "")
    tail = combined.strip()[-1500:]
    print(json.dumps({"systemMessage": f"tsc errors (aiflow-admin):\n{tail}"}))


if __name__ == "__main__":
    main()
