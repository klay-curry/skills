---
name: cc-pattern-research-code-writer
description: Implement AI/ML experiment code from an experiment plan. Use this whenever the user asks to write, reproduce, or implement research experiment code based on a planning document, paper, baseline, ablation, training script, metrics pipeline, or logging contract. Especially use it when simplifications must be documented and code_debug records are required.
---

# Research Code Writer

Use this skill to implement experiment code from a written plan. The code should preserve the technical intent of the plan and make any simplification visible.

## Inputs

Expected inputs:
- `docs/experiment_plan.md` or equivalent plan
- target repo or empty project directory
- paper/technique notes if available
- constraints such as device, budget, framework, and allowed dependencies

If no plan exists, use the research planning skill first or ask the user whether to create one.

## Implementation Principles

- Implement the plan, not a convenient substitute.
- Keep the first version minimal but runnable.
- Make logs and metrics first-class outputs, not afterthoughts.
- Record implementation problems in `code_debug/`.
- Never fabricate experiment results.

## Required Workflow

1. Read the experiment plan and extract a checklist of required modules, metrics, logs, and artifacts.
2. Inspect existing repo conventions before creating files.
3. Create or update code in the smallest coherent architecture.
4. Add a smoke test path that runs quickly on a tiny subset or synthetic input.
5. Verify that logs, metrics, and config snapshots are written to the expected run directory.
6. Write an implementation report with any deviations.

## Default Project Structure

Use the repo convention when it exists. For new Python ML experiments, prefer:

```text
configs/
  experiments/
src/
  data/
  models/
  training/
  evaluation/
  logging/
scripts/
tests/
docs/
runs/
code_debug/
```

Keep model logic, data loading, training loops, evaluation, and logging separate enough that ablations can change one part without rewriting the whole script.

## Plan Compliance Matrix

Create or update `docs/implementation_report.md` with:

```markdown
# Implementation Report

## Plan Compliance
| Plan item | Status | Evidence | Notes |
| --- | --- | --- | --- |
| baseline model | done/partial/missing | file or command | |
| target method | done/partial/missing | file or command | |
| metrics logging | done/partial/missing | output path | |
| required charts | done/partial/missing | script/path | |

## Simplifications
| Simplification | Reason | Risk | How to remove later |
| --- | --- | --- | --- |

## Verification
- Smoke command:
- Expected outputs:
- Latest result path:
```

If a framework, algorithm, module, or training detail is simplified, mention it in this report before finalizing.

## Logging Requirements

Every runnable experiment must write:
- resolved config snapshot
- run metadata: timestamp, seed, device, git commit if available
- training and validation metrics
- errors or warnings when they occur
- final summary suitable for automation parsing

Prefer machine-readable files such as JSONL, CSV, or TSV for metrics, plus readable Markdown summaries for humans.

## code_debug Requirement

Maintain `code_debug/` during implementation.

When a code problem occurs, create or append a Markdown record:

```markdown
# Debug Record: [short title]

- Status: open/fixed/ignored
- Command:
- Error fingerprint:
- Root cause:
- Minimal fix:
- Verification command:
- Follow-up:
```

When the bug is fixed, update the same record with the fix and verification command.

## Verification Checklist

Before final response:
- run the smallest smoke test available
- confirm expected run directories exist
- confirm at least one metrics file is produced
- confirm logs are readable
- confirm implementation report lists deviations

## Final Response

Return:
- files changed
- smoke test command and result
- output directory
- simplifications, if any
- next experiment step
