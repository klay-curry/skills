# Skills

Portable agent skills for AI/ML experiment planning, implementation, automation, debug recording, and loop engineering.

## Included Skills

| Skill | Purpose |
| --- | --- |
| `cc-pattern-research-loop-planner` | Write reproducible experiment plans covering model groups, datasets, code architecture, logs, charts, and handoff rules. |
| `cc-pattern-research-code-writer` | Implement experiment code from a plan with smoke tests, logging, simplification reports, and `code_debug` records. |
| `cc-pattern-research-auto-runner` | Monitor experiments, recover from crashes, and optionally tune allowed hyperparameters through bounded loops. |
| `cc-bugfix-research-debug-hook` | Record experiment failures and verified fixes into `code_debug/` using a portable hook script. |
| `cc-pattern-agent-loop-engineering` | Design controlled agent loops with state, action allowlists, validation, retry, stop, and audit rules. |

## Typical Workflow

1. Use `cc-pattern-research-loop-planner` to create `docs/experiment_plan.md`.
2. Use `cc-pattern-research-code-writer` to implement the planned experiment.
3. Use `cc-pattern-research-auto-runner` to monitor or tune the experiment.
4. Use `cc-bugfix-research-debug-hook` when failures occur.
5. Use `cc-pattern-agent-loop-engineering` when the task needs a reusable autonomous feedback loop.

## Debug Hook

The debug hook script is here:

```text
cc-bugfix-research-debug-hook/scripts/research_debug_hook.py
```

It can be copied into a project and called manually, from CI, or from a Codex-style hook.

Example:

```bash
python3 .codex/hooks/research_debug_hook.py \
  --project . \
  --event failure \
  --experiment-id exp-demo \
  --command "python train.py --config configs/demo.yaml" \
  --exit-code 1 \
  --stderr-file runs/exp-demo/logs/stderr.log
```

See `cc-bugfix-research-debug-hook/references/codex-hooks.example.json` for a failure-only hook example.
