---
name: cc-pattern-research-auto-runner
description: Run, monitor, recover, and optionally tune AI/ML experiments through a controlled feedback loop. Use this whenever the user asks for automated experiment execution, training progress checks, log monitoring, crash recovery, hyperparameter tuning, overnight experiments, AutoResearch-style runs, or autonomous training loops.
---

# Research Auto Runner

Use this skill to operate experiments after a plan and runnable code exist. It has two modes with different permissions:

- monitor mode: keep the planned experiment running and recover from crashes
- tune mode: change allowed hyperparameters or modules to improve results

Do not enter tune mode unless the plan or user explicitly defines what may be changed.

## Required Inputs

- experiment plan
- runnable command
- output directory such as `runs/[experiment_id]/`
- primary metric and direction, such as lower validation loss or higher accuracy
- stop conditions
- tuning allowlist, if tune mode is requested

## State Files

Create or maintain:

```text
runs/[experiment_id]/
  loop_state.json
  experiment_journal.md
  metrics/
  logs/
  checkpoints/
  debug/
```

`loop_state.json` should record the current phase, latest command, latest metric, best metric, retry count, and next action.

## Common Loop

Use this loop for both modes:

```text
observe -> classify -> act -> verify -> record -> decide
```

- observe: read process status, logs, metrics, checkpoint freshness, and resource signals
- classify: normal progress, stalled progress, crashed, metric regression, completed
- act: wait, restart, minimally fix, resume, or run next allowed trial
- verify: confirm the action changed the state in the expected way
- record: update journal, state file, and debug notes
- decide: continue, stop, escalate to human, or start next trial

## Monitor Mode

Use monitor mode for reliability, not optimization.

Check:
- process is still running when expected
- logs are updated recently
- metrics are produced on schedule
- loss/metric is finite
- checkpoint writes are happening when required
- disk space is sufficient
- GPU/CPU memory is not clearly exhausted

If the run crashes:
1. capture command, exit code, stderr, last log lines, and latest metrics
2. write a `code_debug` record or invoke the debug hook if available
3. identify the smallest likely fix
4. rerun the smoke test if code changed
5. resume from latest safe checkpoint when possible
6. record the recovery decision

Escalate to the user after repeated failures with the same fingerprint or when a fix would change research meaning.

## Tune Mode

Tune mode changes the experiment. It must be bounded.

Before tuning, confirm:
- primary metric and direction
- max trials, wall-clock budget, and token/tool budget
- allowed hyperparameters or modules
- forbidden changes
- keep/revert rule

Tune one variable group per trial. Examples:
- learning rate
- batch size
- scheduler
- dropout
- sequence length
- retrieval top_k
- reranker threshold
- allowed model variant

Do not silently change dataset splits, metric definitions, evaluation code, or baseline identity.

## Keep/Revert Rule

For each trial:
1. save config snapshot
2. run fixed-budget experiment
3. compare against current best using the primary metric
4. keep if it improves and does not violate constraints
5. revert or mark rejected if it regresses, fails, or changes the experiment meaning
6. append result to `experiment_journal.md`

## Journal Template

```markdown
## Trial [N]: [short name]
- Mode: monitor/tune
- Hypothesis:
- Command:
- Changed variables:
- Start/end:
- Result metric:
- Decision: keep/revert/escalate
- Evidence:
- Next action:
```

## Stop Conditions

Stop when any condition is met:
- target metric reached
- max trials reached
- max runtime reached
- repeated same failure exceeds threshold
- metrics become invalid and root cause is unclear
- required change is outside the allowlist
- user confirmation is required

## Final Response

Return:
- current best trial
- latest metric and evidence path
- crashes recovered or unresolved
- files changed, if any
- next recommended run
