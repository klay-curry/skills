---
name: cc-pattern-research-loop-planner
description: Design reproducible AI/ML research experiment plans before implementation. Use this whenever the user asks for experiment planning, experimental technical documentation, model group selection, dataset selection, code architecture for experiments, chart/log/output rules, ablation design, or an AutoResearch-style research plan, even if they do not explicitly say "write a plan".
---

# Research Loop Planner

Use this skill to turn a vague research idea into an executable experiment contract. The output should be useful to a separate coding agent, automation agent, or human researcher without needing hidden context.

## Core Idea

Treat the plan as a contract, not a brainstorming note. The plan must define:
- what hypothesis is being tested
- which models and datasets are in scope
- what code structure should exist
- what logs, metrics, artifacts, and charts must be produced
- what counts as success or failure

## When Starting

If any of these are missing and cannot be inferred safely, ask at most three focused questions before writing the plan:
- research goal or target paper/technique
- available compute and time budget
- allowed datasets, models, and codebase constraints

If the user wants immediate drafting, state assumptions explicitly and continue.

## Required Workflow

1. Read the available context: paper notes, README, existing code, prior experiment logs, and dataset/model constraints.
2. Define a stable experiment id such as `exp-YYYYMMDD-short-topic`.
3. Write or update `docs/experiment_plan.md` unless the user requests another path.
4. Include a handoff section that tells the code-writing agent exactly what to implement first.
5. Avoid pretending uncertain research choices are settled. Mark them as assumptions or decision points.

## Experiment Plan Template

Use this structure unless the repo already has a stronger convention:

```markdown
# Experiment Plan: [title]

## 1. Objective
- Research question:
- Hypothesis:
- Primary success metric:
- Secondary metrics:

## 2. Scope and Assumptions
- In scope:
- Out of scope:
- Compute/time budget:
- Reproducibility requirements:

## 3. Model Groups
| Group | Model/Method | Purpose | Expected change | Notes |
| --- | --- | --- | --- | --- |
| baseline | | reference result | | |
| target | | tested technique | | |
| ablation | | isolate mechanism | | |
| sanity | | catch data/metric bugs | | |

## 4. Dataset Protocol
- Dataset candidates:
- Final dataset choice:
- Splits:
- Preprocessing:
- Leakage checks:
- Sampling rules:
- Licensing/privacy constraints:

## 5. Code Architecture
```text
configs/
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
- Required modules:
- Entry points:
- Config files:
- Interfaces between modules:

## 6. Logging and Artifact Contract
All runs write to `runs/[experiment_id]/`.

```text
runs/[experiment_id]/
  logs/
  metrics/
  checkpoints/
  figures/
  artifacts/
  debug/
```

Required outputs:
- training log:
- validation metrics:
- config snapshot:
- git commit or code snapshot:
- random seed:
- hardware/runtime summary:

## 7. Charts and Tables
| Output | Why it matters | Source data | Destination |
| --- | --- | --- | --- |
| training curve | detect convergence and instability | metrics log | figures/training_curve.png |
| validation comparison | compare model groups | metrics summary | figures/validation_compare.png |
| ablation table | isolate causal contribution | experiment results | artifacts/ablation.md |

Add task-specific charts such as confusion matrix, ROC/PR, retrieval recall, latency/cost table, or qualitative examples when relevant.

## 8. Execution Plan
1. Smoke test:
2. Baseline run:
3. Target run:
4. Ablations:
5. Analysis:

## 9. Risks and Guardrails
- Known technical risks:
- Dataset risks:
- Overfitting risks:
- Stop conditions:
- Rollback plan:

## 10. Handoff to Code Writer
- First file to create or edit:
- Minimal smoke test command:
- Must-not-simplify items:
- Allowed simplifications, if any:
```

## Model Group Guidance

Use at least four groups for serious experiments:
- baseline: known simple method or previous implementation
- target: the proposed method
- ablation: remove or change one mechanism at a time
- sanity: tiny dataset, shuffled labels, random baseline, or deterministic check

Do not compare a large target model only against a weak baseline unless the plan explicitly explains why.

## Dataset Selection Guidance

Prefer datasets that are:
- aligned with the hypothesis
- legally usable
- small enough for fast smoke tests
- large enough for the target claim
- split in a way that prevents leakage

If a public benchmark is too expensive, define a two-tier plan: `smoke_subset` for implementation checks and `full_eval` for final claims.

## Output Rules

The final response should include:
- plan path
- assumptions made
- first implementation step
- validation command or smoke-test command

Do not write experiment code from this skill unless the user explicitly asks to combine planning and implementation.
