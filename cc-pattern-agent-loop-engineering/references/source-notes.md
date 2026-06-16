# Source Notes

These notes summarize public ideas used by `cc-pattern-agent-loop-engineering`.

## KnightLi: Loops Replace Prompts

Source: https://knightli.com/2026/06/10/loops-replace-prompts-agent-loop-engineering/

Useful ideas:
- A prompt is one request; a loop is a feedback system.
- Reliable loops need explicit goal, action, feedback, stop, and audit rules.
- Long-running agent work shifts complexity from wording to state, validation, budget, and safety design.

## Karpathy AutoResearch

Source: https://github.com/karpathy/autoresearch

Useful ideas:
- Make one bounded change per trial.
- Use a fixed time or compute budget so experiments are comparable.
- Score results with a clear metric.
- Keep or discard changes based on measured improvement.
- Keep the editable surface small so the loop remains reviewable.

## Local Design Choice

For general research projects, this skill separates:
- experiment planning
- code writing
- auto-running and tuning
- debug recording
- loop design

This keeps each agent role small enough to verify.
