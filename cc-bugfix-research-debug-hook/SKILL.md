---
name: cc-bugfix-research-debug-hook
description: Capture, document, and reuse fixes for AI/ML experiment failures. Use this whenever experiment code crashes, training logs show errors, automation detects a failed run, code_debug records are required, or the user wants a hook that records failures and later summarizes successful fixes.
---

# Research Debug Hook

Use this skill to make experiment failures recoverable. The hook records what failed, how it was fixed, and whether the fix should change future coding or experiment-agent instructions.

This skill ships a portable script:

```text
scripts/research_debug_hook.py
```

The script has no third-party dependencies.

## Responsibilities

- create and maintain `code_debug/`
- record failure fingerprints
- capture failed command, exit code, stderr, and relevant log path
- track status from `open` to `fixed`
- record verified fixes
- summarize reusable lessons for future agents

It should not directly rewrite experiment code. Fixing belongs to the code-writing agent or automation agent.

## Directory Contract

```text
code_debug/
  index.md
  YYYYMMDD-HHMMSS-[fingerprint].md
```

Each record should include:

```markdown
# Debug Record: [fingerprint]

- Status: open/fixed
- Experiment id:
- Command:
- Exit code:
- Error fingerprint:
- First seen:
- Last updated:

## Failure Evidence

## Root Cause

## Minimal Fix

## Verification

## Reusable Lesson

## Should Update Agent Instructions?
- research-code-writer: yes/no, reason
- research-auto-runner: yes/no, reason
- loop-engineering: yes/no, reason
```

## Manual Usage

From a project root:

```bash
python3 path/to/research_debug_hook.py \
  --project . \
  --event failure \
  --experiment-id exp-demo \
  --command "python train.py --config configs/demo.yaml" \
  --exit-code 1 \
  --stderr-file runs/exp-demo/logs/stderr.log
```

After a fix:

```bash
python3 path/to/research_debug_hook.py \
  --project . \
  --event fix \
  --debug-file code_debug/20260616-120000-err-abc123.md \
  --message "Fixed dataset path resolution and verified with python train.py --smoke."
```

## Codex Hook Usage

Copy `scripts/research_debug_hook.py` into the target project, for example:

```text
.codex/hooks/research_debug_hook.py
```

Then adapt the example in `references/codex-hooks.example.json`.

Prefer attaching it only to failure events. High-frequency success hooks create noise and make long sessions harder to use.

## Fix Review

When a failure is fixed, review whether the lesson should update:
- the code writer skill: recurring implementation mistake
- the auto runner skill: recurring recovery or tuning mistake
- the loop engineering skill: missing stop, retry, state, or budget rule

Only update agent instructions when the lesson is reusable across future experiments. Do not update skills for one-off typos or environment-only failures.

## Final Response

When using this skill, report:
- debug record path
- error fingerprint
- current status
- verification command, if fixed
- whether any agent instruction should change
