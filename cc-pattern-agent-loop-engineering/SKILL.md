---
name: cc-pattern-agent-loop-engineering
description: Design controlled agent loops instead of one-shot prompts. Use this whenever the user mentions loops, AutoResearch, autonomous agents, repeated experiment iterations, self-improvement loops, monitor/fix/retry cycles, long-running tool workflows, or wants an agent to keep working until a measurable condition is met.
---

# Agent Loop Engineering

Use this skill to design a feedback loop for an agentic workflow. A loop is a small control system: it observes state, chooses an action, executes it, validates the result, records evidence, and decides whether to continue.

## Inspiration

This skill is informed by:
- "Loops replace prompts" style loop engineering: prompt, tool, state, test, stop rules.
- AutoResearch-style experimentation: fixed budget, measurable score, one bounded change per trial, keep or revert based on evidence.

See `references/source-notes.md` for source links and distilled design notes.

## When to Use a Loop

Use a loop when the task is:
- long-running
- measurable
- tool-based
- likely to fail and need recovery
- improved by repeated trials
- too expensive for manual copy-paste iteration

Do not use a loop for simple one-shot tasks such as a short explanation, a direct translation, or a tiny code snippet.

## Loop Spec Template

Write or update `docs/loop_spec.md`:

```markdown
# Loop Spec: [name]

## Goal
- Objective:
- Success metric:
- Metric direction:
- Completion condition:

## State
- State file:
- Required fields:
- How state is read:
- How state is updated:

## Action Space
Allowed actions:
- observe
- run command
- edit allowlisted files
- restart/resume
- propose next trial

Forbidden actions:
- change evaluation metric
- change dataset split
- delete historical results
- exceed budget

## Validator
- Commands/checks:
- Expected artifacts:
- Failure signals:

## Decision Rules
- Keep:
- Revert:
- Retry:
- Escalate:

## Budget and Stop Rules
- Max iterations:
- Max runtime:
- Max retries per fingerprint:
- Max cost:
- Human approval triggers:

## Audit Log
- Journal path:
- Required per-iteration fields:
```

## Standard Loop

```text
observe -> plan -> act -> validate -> decide -> record
                  ^                         |
                  |--------- feedback ------|
```

Each iteration should be small enough that a bad action can be understood and reverted.

## Design Rules

### Objective

Define a measurable target. If the target cannot be measured automatically, use human review checkpoints rather than pretending the loop can optimize it alone.

### State

Keep state outside the model context in a file such as `loop_state.json`. Include:
- phase
- current baseline
- last action
- last result
- best result
- retry count
- error fingerprint
- next action

### Action Space

The loop is safer when the agent can only change a small surface:
- one file
- one config directory
- one hyperparameter allowlist
- one experiment branch

If the loop can change everything, failures become hard to attribute.

### Validation

Every action needs a validator:
- tests
- build command
- metric parser
- log freshness check
- artifact existence check
- benchmark score

### Stop Rules

Stop rules are part of correctness:
- success reached
- max iterations reached
- repeated same failure
- metric becomes invalid
- action requires permission
- budget exceeded
- rollback fails

### Audit

Write a journal line for every iteration. The journal is how future agents learn why a decision was made.

## Anti-Patterns

- Optimizing without a metric
- Retrying forever with the same error
- Changing evaluation code during tuning
- Mixing multiple changes in one trial
- Recording only final results, not failed attempts
- Using hooks on every successful action and creating noisy memory

## Final Response

Return:
- loop spec path
- state file path
- action allowlist
- validator command
- stop conditions
- first iteration command
