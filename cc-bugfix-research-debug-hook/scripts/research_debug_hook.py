#!/usr/bin/env python3
"""Portable experiment debug recorder.

Records failed experiment commands and verified fixes into code_debug/.
It can be used manually, from CI, or from a Codex-style hook JSON payload.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def now_local() -> str:
    return dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def now_slug() -> str:
    return dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def normalize(text: str) -> str:
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fingerprint(text: str) -> str:
    basis = normalize(text)[:500] or "empty-error"
    return "err-" + hashlib.sha1(basis.encode("utf-8", errors="ignore")).hexdigest()[:10]


def read_text_file(path: Optional[str]) -> str:
    if not path:
        return ""
    p = Path(path).expanduser()
    if not p.exists():
        return f"[stderr file not found: {p}]"
    return p.read_text(encoding="utf-8", errors="replace")


def read_stdin() -> str:
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read()


def ensure_debug_dir(project: Path) -> Path:
    debug_dir = project / "code_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    index = debug_dir / "index.md"
    if not index.exists():
        index.write_text("# Code Debug Index\n\n", encoding="utf-8")
    return debug_dir


def append_index(debug_dir: Path, record_path: Path, fp: str, status: str, summary: str) -> None:
    rel = record_path.name
    line = f"- {now_local()} | {status} | `{fp}` | [{rel}]({rel}) | {summary[:120]}\n"
    with (debug_dir / "index.md").open("a", encoding="utf-8") as f:
        f.write(line)


def latest_record(debug_dir: Path) -> Optional[Path]:
    records = sorted(p for p in debug_dir.glob("*.md") if p.name != "index.md")
    return records[-1] if records else None


def payload_from_hook_stdin() -> Dict[str, Any]:
    raw = read_stdin().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_stdin": raw}


def text_from_payload(payload: Dict[str, Any]) -> str:
    parts = []
    for key in ["error", "stderr", "message", "reason", "details", "raw_stdin"]:
        value = payload.get(key)
        if value:
            parts.append(str(value))
    tool_output = payload.get("tool_output")
    if tool_output:
        parts.append(json.dumps(tool_output, ensure_ascii=False) if not isinstance(tool_output, str) else tool_output)
    return "\n".join(parts)


def command_from_payload(payload: Dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        return str(tool_input.get("command") or tool_input.get("cmd") or tool_input)
    return ""


def create_failure_record(
    project: Path,
    experiment_id: str,
    command: str,
    exit_code: str,
    evidence: str,
) -> Path:
    debug_dir = ensure_debug_dir(project)
    fp = fingerprint(evidence or command)
    record = debug_dir / f"{now_slug()}-{fp}.md"
    summary = normalize(evidence).split(". ")[0][:160] if evidence else command[:160]
    content = f"""# Debug Record: {fp}

- Status: open
- Experiment id: {experiment_id or "unknown"}
- Command: `{command or "unknown"}`
- Exit code: {exit_code or "unknown"}
- Error fingerprint: `{fp}`
- First seen: {now_local()}
- Last updated: {now_local()}

## Failure Evidence

```text
{evidence.strip()[:8000] or "No stderr or error text captured."}
```

## Root Cause

TBD.

## Minimal Fix

TBD.

## Verification

TBD.

## Reusable Lesson

TBD.

## Should Update Agent Instructions?
- research-code-writer: TBD
- research-auto-runner: TBD
- loop-engineering: TBD
"""
    record.write_text(content, encoding="utf-8")
    append_index(debug_dir, record, fp, "open", summary)
    return record


def append_fix_record(project: Path, debug_file: str, message: str) -> Path:
    debug_dir = ensure_debug_dir(project)
    record = Path(debug_file).expanduser() if debug_file else latest_record(debug_dir)
    if record is None:
        record = debug_dir / f"{now_slug()}-{fingerprint(message)}.md"
        record.write_text(f"# Debug Record: {fingerprint(message)}\n\n", encoding="utf-8")
    if not record.is_absolute():
        record = project / record
    if not record.exists():
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text("# Debug Record\n\n", encoding="utf-8")
    with record.open("a", encoding="utf-8") as f:
        f.write(f"\n## Fix Update: {now_local()}\n\n{message.strip() or 'Fix recorded without message.'}\n")
    text = record.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"- Status: open", "- Status: fixed", text, count=1)
    text = re.sub(r"- Last updated: .*", f"- Last updated: {now_local()}", text, count=1)
    record.write_text(text, encoding="utf-8")
    append_index(debug_dir, record, fingerprint(text), "fixed", message or "fix recorded")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Record experiment failures and fixes into code_debug/.")
    parser.add_argument("--project", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument("--event", choices=["failure", "fix", "note"], default="failure")
    parser.add_argument("--experiment-id", default="")
    parser.add_argument("--command", default="")
    parser.add_argument("--exit-code", default="")
    parser.add_argument("--stderr-file", default="")
    parser.add_argument("--message", default="")
    parser.add_argument("--debug-file", default="")
    parser.add_argument("--from-hook-json", action="store_true", help="Read Codex-style hook payload JSON from stdin.")
    args = parser.parse_args()

    payload: Dict[str, Any] = {}
    if args.from_hook_json:
        payload = payload_from_hook_stdin()

    project = Path(args.project or payload.get("cwd") or ".").expanduser().resolve()
    if payload.get("cwd") and args.project == ".":
        project = Path(str(payload.get("cwd"))).expanduser().resolve()

    if args.event == "fix":
        record = append_fix_record(project, args.debug_file, args.message or text_from_payload(payload))
        print(str(record))
        return 0

    evidence_parts = [
        args.message,
        read_text_file(args.stderr_file),
        text_from_payload(payload),
    ]
    evidence = "\n".join(x for x in evidence_parts if x)
    command = args.command or command_from_payload(payload)
    exit_code = args.exit_code or str(payload.get("exit_code") or payload.get("status") or "")
    experiment_id = args.experiment_id or str(payload.get("experiment_id") or "")
    record = create_failure_record(project, experiment_id, command, exit_code, evidence)
    print(str(record))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
