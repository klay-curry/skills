---
name: exp-planner
description: "实验规划师。读取 program.md（由 program-md-designer 生成）和项目上下文，输出单实验规划文档（模型组、数据集、代码架构、图表、日志路径），供 exp-coder 实现。触发词：'规划实验'、'写实验规划'、'实验设计'、'plan experiment'、'design experiment'。"
user_invocable: true
version: "1.0.0"
---

# exp-planner: 实验规划师

## 定位（Position in Pipeline）

```
program-md-designer  →  program.md（协议：目标/预算/边界）
                          ↓
                       exp-planner          ← 你在这里
                          ↓
                docs/experiments/plan_<NN>_<slug>.md
                          ↓
                       exp-coder
                          ↓
                       exp-runner
                          ↓
                  self-debugger（持续观测）
```

**职责**：把一份 program.md 拆成 N 份**可执行的单实验规划**，每份都回答「跑什么、怎么跑、跑完算什么」。

**不负责**：不写代码、不跑实验、不修改 program.md。

## 何时调用

- 用户：「我想跑 ConvNeXt + focal loss，先帮我规划」
- 用户：「下一步该做什么实验？」
- exp-coder：「没有可用的 plan」
- exp-runner：「当前 plan 已收敛，需要新方向」

## 工作流（4 阶段）

### Phase 1: 上下文吸收（Context Absorption）

读取以下文件，构建规划依据：

| 文件 | 优先级 | 用途 |
|------|--------|------|
| `program.md` | 必需 | 目标指标、时间预算、可改/不可改文件、复杂度准则 |
| `docs/competition_roadmap.md` 或类似设计文档 | 高 | 模型梯队、实验顺序、防御策略 |
| `README.md` | 中 | 项目背景、数据集描述 |
| `results.tsv` / `results_weather.tsv` | 高 | 历史实验，避免重复 |
| `runs/train.log` 或最近一次 run 的日志 | 中 | 当前最佳基线 |
| `code_debug.md` | 中 | 已被 self-debugger 记录的反复失败模式 |

**关键判断**：
- program.md 的目标指标是什么？（val_acc / val_bpb / val_loss / 其他）
- 时间预算是多少？（决定每轮实验多激进）
- 模型组里哪些还没被试过？（避免重复）
- 有没有任何在 code_debug.md 里反复出现的失败？（影响 plan 设计）

### Phase 2: 五要素设计（Five-Dimension Spec）

每一份规划文档**必须**回答 5 个问题。如果某一维「和上次完全相同」也要写——可重复性是 plan 的一部分。

#### 维度 1：模型组（Model Group）

```markdown
## 模型组

| 成员 | 选择理由 | program.md 允许? |
|------|---------|-----------------|
| ConvNeXt-tiny | 已做过 baseline，作为锚点 | ✅ |
| DINOv2-base | 自监督预训练，特征质量高 | ✅ |
| Swin-base | 层级化注意力，对中尺度结构敏感 | ✅ |

**对照组**（必须有）：ConvNeXt + cross_entropy
**主实验**：DINOv2 + focal loss
**消融**：DINOv2 + cross_entropy（隔离 loss 的影响）
```

设计原则：
- **必须有「对照组 + 主实验 + ≥ 1 个消融」**，否则无法归因
- 模型选择要写「为什么选」，不是「选什么」
- 不能超出 program.md 允许的模型列表

#### 维度 2：数据集（Dataset Scope）

```markdown
## 数据集

| 字段 | 值 |
|------|-----|
| 训练集 | data/cloudy + data/rainy + data/snowy + data/sunny 全量 |
| 验证集 | 与 program.md 一致（80/10/10 分层切分，**只读**） |
| 子集策略 | 类别平衡采样（针对 snowy 100 张不足） |
| 增强 | src/data/transforms.py 现有 Compose，**仅调强度** |
| 排除 | 无 |

**关键决策**：
- 类别不平衡 6.1× → 是否上 WeightedRandomSampler？
- 是否冻结骨干？前几层解冻？
- 是否引入外部数据？**默认不引入**（除非 program.md 允许）
```

设计原则：
- 数据切分必须引用 program.md 的「只读文件」声明
- 子集策略要写「做了什么」和「为什么」
- 不能绕过评估集的 ground truth

#### 维度 3：代码架构（Code Architecture）

```markdown
## 代码架构

### 文件变更清单
- [ ] **修改** `src/train.py`：增加 focal loss 调用、scheduler 切换
- [ ] **修改** `src/configs/default.yaml`：把 `model.name` 改为 `dinov2`、`loss.name` 改为 `focal`
- [ ] **新增** `src/data/sampler.py`：WeightedRandomSampler（如果 program.md 允许新增文件）
- [ ] **不修改** `src/data/dataset.py`、`src/evaluate.py`、`src/losses/losses.py`

### 函数级变更
- `train.py::main()`：在 `loss = get_loss(...)` 之后传入 `class_weights` 参数
- `train.py::train_one_epoch()`：加入梯度累积分支

### 依赖
- 不引入新包（program.md 限制）
- 如需 `torchvision.ops.sigmoid_focal_loss`，确认已在 `src/requirements.txt`
```

设计原则：
- 必须列出「修改 / 新增 / 不修改」三类文件
- 关键函数签名变化要写出来
- 新依赖必须先核对 `pyproject.toml` / `requirements.txt`

#### 维度 4：图表设计（Chart Spec）

每张图都要有「**为什么画**」（诊断什么），不要为了画而画。

```markdown
## 图表设计

| 图 | 内容 | 工具 | 路径 | 诊断什么 |
|----|------|------|------|---------|
| loss 曲线 | train_loss + val_loss vs step | matplotlib | `runs/<exp_id>/loss_curve.png` | 是否过拟合、是否收敛 |
| 准确率曲线 | val_acc + val_macro_f1 vs epoch | matplotlib | `runs/<exp_id>/metric_curve.png` | 主指标 vs 类别平衡指标 |
| 混淆矩阵 | 4×4 归一化 | sklearn + matplotlib | `runs/<exp_id>/confusion_matrix.png` | 类别间混淆模式 |
| 学习率 | LR vs step | matplotlib | `runs/<exp_id>/lr_schedule.png` | warmup/衰减是否符合预期 |
| 类别分布 | 训练前 vs 训练后预测分布 | matplotlib | `runs/<exp_id>/pred_dist.png` | sampler 是否生效（如果引入） |
| 资源曲线 | VRAM / GPU util vs step | nvidia-smi 解析 | `runs/<exp_id>/resource.png` | 是否有内存泄漏 / 利用率 |

**图表规则**：
- 所有图必须有标题 + 轴标签 + 图例
- 颜色惯例：训练=蓝、验证=橙、测试=绿（项目惯例）
- DPI = 150，PNG，< 500KB
- 自动在 train loop 末尾生成，不手动画
```

#### 维度 5：日志与产物（Log & Artifact Layout）

```markdown
## 日志与产物

### 目录布局
runs/<exp_id>/
├── train.log              # 训练主日志，INFO 级别
├── monitor.jsonl          # exp-runner monitor 周期状态
├── metrics.jsonl          # 每 step/epoch 的指标（JSON Lines）
├── config.yaml            # 本次运行的完整 config（可复现）
├── env.json               # 硬件环境（GPU 型号、CUDA、torch 版本）
├── best.pt                # val_acc 最高 checkpoint
├── last.pt                # 最后一个 epoch 的 checkpoint
└── <charts from 图表设计节>

### 命名约定
- `<exp_id>` = `<YYYYMMDD>_<plan_NN>_<model>_<loss>_<short_hash>`
- 示例：`20260616_plan_03_dinov2_focal_a1b2c3`

### results.tsv 写入规则
- 由 exp-runner 自动写入，不在 exp-coder 范围
- 一行 = 一次实验
- 字段：`commit, plan_id, <metrics...>, peak_vram_gb, time_seconds, status, description`
```

设计原则：
- 目录结构必须可被脚本聚合（不要 ad-hoc 命名）
- `metrics.jsonl` 用 JSON Lines 便于后续 pandas 读取
- `env.json` 必须记录，否则后续无法复现

### Phase 3: 风险与验收（Risk & Acceptance）

**每一份 plan 必须有这一节**——否则视为不完整。

```markdown
## 风险与回滚

| 风险 | 触发条件 | 缓解 |
|------|---------|------|
| OOM | peak VRAM > 24GB | 降 batch_size 至 16，加 gradient checkpointing |
| 数据泄漏 | 验证集出现训练样本 | 立即终止，回滚 dataset.py 到已知 commit |
| 灾难性遗忘 | 训练后期 val_acc 下降 | 提前开 early_stopping（patience=20） |
| 数值爆炸 | loss > 1e6 | 加载上一个 checkpoint + 降 LR ×0.1 |

**回滚策略**：
- 代码回滚：`git revert <exp_commit>` 或 `git reset --hard <last_good_commit>`
- 数据回滚：dataset.py 只读，无需回滚
- 模型回滚：使用 `runs/<last_good_exp>/best.pt`

## 验收准则

**成功条件（全部满足）**：
- [ ] val_acc ≥ 0.92（baseline +0.5pp）
- [ ] val_macro_f1 ≥ 0.88（不平衡场景必须看这个）
- [ ] 训练无崩溃，< 5 次 NaN
- [ ] peak VRAM ≤ 18GB（program.md 软约束）
- [ ] 训练时长 ≤ 时间预算 × 1.05

**失败处理**：
- val_acc 提升 < 0.003：保留作为消融记录，状态 = `discard`
- 训练崩溃：状态 = `crash`，触发 self-debugger
- val_acc 退化 ≥ 0.01：状态 = `regression`，立即回滚
```

设计原则：
- 验收准则必须可机器验证（数字阈值，不是模糊描述）
- 回滚策略要写**具体命令**，不要只说「回滚」
- 失败 vs 退化 vs 崩溃要分开处理

### Phase 4: 写入文档（Persist）

#### 路径与命名

- 单实验规划：`docs/experiments/plan_<NN>_<slug>.md`
- 索引：`docs/experiments/INDEX.md`（自动维护）
- NN 从 01 起递增；slug 用 kebab-case 描述核心思路
- 若 `docs/experiments/` 不存在 → 自动创建

#### INDEX.md 格式

```markdown
# 实验规划索引

| # | Plan | 状态 | 主结果 | 日期 |
|---|------|------|-------|------|
| 01 | [plan_01_baseline_convnext](plan_01_baseline_convnext.md) | done | val_acc=0.87 | 2026-06-10 |
| 02 | [plan_02_dinov2_focal](plan_02_dinov2_focal.md) | ready | — | 2026-06-15 |
| 03 | [plan_03_swin_aug_ablation](plan_03_swin_aug_ablation.md) | proposed | — | 2026-06-16 |
```

**状态机**：`proposed` → `ready` → `running` → `done | aborted | superseded`

## 与其他 skill 的契约

| 上游 | 下游 |
|------|------|
| `program.md`（由 program-md-designer 输出） | `exp-coder`（读取 plan 实现代码） |
| `results.tsv`（避免重复实验） | `exp-runner`（读取 plan 跑实验） |
| `code_debug.md`（避免重蹈失败） | |

**handoff 协议**：
- exp-planner 完成后，把 plan 路径追加到 `docs/experiments/INDEX.md`
- exp-coder 必须先 grep `INDEX.md` 找到下一个 `ready` 状态的 plan
- exp-runner 必须只跑 `ready` 或 `running` 状态的 plan

## 输出的最小骨架模板

当用户说「帮我规划一个新实验」时，exp-planner 应能直接产出：

```markdown
# Plan NN: <一句话核心思路>

> 父协议: program.md
> 创建时间: YYYY-MM-DD
> 状态: proposed

## 目标
<一句话：本实验想验证什么假设>

## 模型组
<table as above>

## 数据集
<table as above>

## 代码架构
<checklist as above>

## 图表设计
<table as above>

## 日志与产物
<directory tree + naming>

## 风险与回滚
<table as above>

## 验收准则
<checklist as above>

## 备注
<任何偏离 program.md 的地方都必须在这里写>
```

## 反模式（Anti-Patterns）

- ❌ 一份 plan 包含 ≥ 3 个互不依赖的实验 → 应拆成多份 plan
- ❌ 没有对照组（baseline）的实验 → 不可比较
- ❌ 引用 program.md 之外的「规则」→ 规则冲突
- ❌ 没有验收准则 → 无法判断成败
- ❌ 模型选择不写理由 → 黑盒决策
- ❌ 图表清单照搬上次 → 没有诊断目的
- ❌ 跳过 Phase 1 直接写 plan → 可能重复已失败的实验

## 引用

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — 协议哲学
- 本 skill 设计参考 [program-md-designer](../program-md-designer/SKILL.md) 的三阶段工作流
- [knightli.com: Agent Loop Engineering](https://knightli.com/2026/06/10/loops-replace-prompts-agent-loop-engineering/) — Loop 替换 Prompt 的哲学基础
