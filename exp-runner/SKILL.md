---
name: exp-runner
description: "自动化实验执行者。两种模式：(1) monitor 监控训练进度、处理崩溃、确保实验继续；(2) tune 基于 results.tsv 自动调优超参数或模块替换。两种模式可组合成自主 loop。触发词：'跑实验'、'monitor'、'tune'、'自动跑实验'、'继续实验'。"
user_invocable: true
version: "1.0.0"
---

# exp-runner: 自动化实验执行者

## 定位

```
exp-coder  →  可运行代码 + plan_<NN>.md (状态: ready)
                       ↓
                    exp-runner           ← 你在这里
                  ↙         ↘
              monitor       tune
                  ↘         ↙
                  results.tsv 更新
                       ↓
                 self-debugger 持续观测
```

**职责**：让实验按 plan 跑起来，并在崩溃时恢复、在结果出来后决定下一步。

**不负责**：写代码、修改 plan、修改 program.md、做长期决策（stop / continue 边界由用户或更上层决定）。

## 何时调用

- 用户：「跑 plan_03」
- 用户：「开始 monitor」
- 用户：「基于 results 自动调优」
- 自我触发：exp-runner 启动一个 run 后自动进入 monitor 模式

## 两种模式

### 模式 A: monitor（监控模式）

**目标**：盯着训练，不让它悄悄死掉。

**循环**：

```
LOOP:
  1. 找到当前运行中的 exp
     - runs/<exp_id>/train.log 最近 mtime < 5 分钟前？
     - 否则认为进程已死 → 进入崩溃处理
  2. 解析最近 N 行日志
     - step X: loss=Y, val_acc=Z
     - 检查异常：
       * loss = nan/inf → 触发 NaN 恢复
       * loss 发散（最近 100 步 +50%）→ 触发 LR 降档
       * VRAM 接近上限 → 触发 OOM 预防
       * 重复相同 metric 超过 5 分钟 → 触发 stuck 检测
  3. 报告状态（每 5 分钟一次）
     - 写 runs/<exp_id>/monitor.jsonl
     - 或 stdout 输出
  4. SLEEP 5 分钟
```

#### 崩溃恢复协议

| 异常类型 | 检测信号 | 恢复动作 |
|---------|---------|---------|
| **NaN loss** | log 含 `loss=nan` 或 `loss=inf` | 加载 last.pt → 降 LR ×0.1 → 重启 |
| **OOM** | log 含 `CUDA out of memory` | batch_size ×0.5 → gradient_checkpointing=True → 重启 |
| **数据错误** | log 含 `RuntimeError: DataLoader` | 终止 → 通知 self-debugger → **不自动重启** |
| **进程消失** | mtime > 5 分钟 | 检查 PID → 已死则加载 last.pt → 重启 |
| **stuck** | 同 step 出现 > 10 分钟 | 终止 → 加载 last.pt → 跳到下一组参数 |
| **数值爆炸** | log 含 `loss=1e6` 或更大 | 加载 last.pt → LR ×0.5 → 重启 |

**重启次数上限**：同一 exp 重启 ≥ 3 次 → 标记为 `crash`，通知 self-debugger，**停止自动恢复**。

#### 监控的"不作为"边界

以下情况 monitor **不主动改**：
- 实验正常推进（即使指标难看）
- program.md 禁止的修改
- 需要人为判断的（数据泄漏嫌疑、loss 曲线形态异常等）

monitor 的**唯一权限**：调 launcher 脚本（如重置 LR、改 batch_size），**绝不修改 src/**。

### 模式 B: tune（调优模式）

**目标**：基于历史结果，自动提议下一组参数或模块。

**输入**：
- `results.tsv`（或项目对应 tsv）
- `code_debug.md`（已知简化 / 偏差）
- 当前 `plan_<NN>.md`

**决策循环**：

```
LOOP:
  1. 读 results.tsv 最近 N 行
  2. 提取 best_k = top-K（按 program.md 主指标）
  3. 分析 best_k 的共性：
     - 模型组倾向？
     - loss 倾向？
     - lr / batch_size 区间？
     - 数据增强组合？
  4. 提取 worst_k = bottom-K（不是 crashed 的）
  5. 提出下一步候选：
     - 在 best_k 邻域继续搜索（小步）
     - 跳出 best_k 做激进尝试（大幅）
     - 复现 worst_k 看是否可救
  6. 写入 docs/experiments/plan_<NN+1>.md（调用 exp-planner）
     - 或：直接修改 config（小幅修改时跳过新 plan）
  7. 启动 monitor 跑新实验
```

#### 调优策略库

| 策略 | 适用场景 | 风险 |
|------|---------|------|
| **Local search** | best_k 聚集在某超参数邻域 | 可能卡局部最优 |
| **Random restart** | best_k 多样，无明显聚集 | 计算开销大 |
| **Axis-aligned** | 单一超参数主导（lr / dropout） | 忽略交互 |
| **Population-based** | 多 exp 并行（如果算力允许） | 需要多 GPU |
| **Curriculum** | 指标停滞 ≥ K 轮时切换 loss 函数 | 复杂度跳变 |

#### 用户的"许可边界"读取

`program.md` 中通常有「可以做」的清单。tune **只能**在该清单内做选择：

- 如果用户允许「替换 model 名字」，则 tune 可以从 `{convnext, swin, dinov2, ...}` 中选
- 如果用户允许「调增强强度」，则 tune 可以改 `transforms.py` 里的强度参数
- 如果用户**没有**显式允许 → **不调**

**tune 永远不修改**：
- `evaluate.py` / 评估函数
- `dataset.py` / 数据切分
- `pyproject.toml` / 装新包
- 训练循环的核心结构（除非 plan 明确允许）

#### 调优的最小数据需求

启动 tune 之前必须满足：
- 至少 N=5 个**非崩溃**样本
- 至少 M=2 个不同的 `model.name`（避免单点）
- 最近 K=3 轮有结果可分析

否则 → 退出 tune，回到 monitor 等更多数据。

### Monitor + Tune 组合（自主 Loop）

```
[exp-planner: plan_01] → [exp-coder: 写代码] → [tune: 决定第一批参数]
       ↓
[monitor: 跑 plan_01] → 崩了就恢复，跑完出结果
       ↓
[tune: 读 results.tsv, 决定 plan_02 参数]
       ↓
[exp-planner: plan_02] → [exp-coder: 微调代码] → [monitor: 跑]
       ↓
LOOP UNTIL: 时间耗尽 / 用户中断 / 连续 K 轮无提升
```

**停止条件**（任一）：
- 总 wall-clock ≥ 用户预算
- 最近 K=3 轮 best 提升 < ε（program.md 定义的 ε）
- 用户手动中断
- self-debugger 报告 fatal pattern

## 输出协议

### 每次实验必须产出

```
runs/<exp_id>/
├── train.log              # monitor 持续 append
├── monitor.jsonl          # monitor 周期状态
├── metrics.jsonl          # 每 step 的 metric
├── best.pt / last.pt
├── config.yaml            # 本次运行完整 config
├── env.json               # 硬件环境
└── <charts from plan 图表设计节>
```

### results.tsv 写入

在实验**真正跑完**（不是崩溃）后追加一行：

```tsv
commit	plan_id	val_acc	val_macro_f1	val_loss	peak_vram_gb	time_seconds	status	description
a1b2c3d	plan_03	0.9284	0.8912	0.3412	14.3	723	keep	dinov2 + focal, 100ep
e4f5g6h	plan_03	0.0000	0.0000	0.0000	0.0	12	crash	OOM at step 50
i7j8k9l	plan_03	0.8500	0.7900	0.5200	10.1	600	discard	val_acc < baseline - 0.02
```

**status 枚举**：
- `keep` — 跑完且指标保留（优于或等于当前 best）
- `discard` — 跑完但被回滚
- `crash` — 失败，未跑完
- `regression` — 跑完但指标退化（自动回滚）

### monitor.jsonl 格式

```jsonl
{"ts": "2026-06-16T14:30:00", "exp_id": "...", "step": 1234, "loss": 0.234, "val_acc": 0.91, "vram_gb": 14.2, "status": "ok"}
{"ts": "2026-06-16T14:35:00", "exp_id": "...", "step": 1567, "loss": 0.221, "val_acc": 0.92, "vram_gb": 14.3, "status": "ok"}
{"ts": "2026-06-16T14:40:00", "exp_id": "...", "action": "lr_decay", "reason": "loss plateau 100 steps"}
```

## 与其他 skill 的契约

| 上游 | 下游 |
|------|------|
| `plan_<NN>.md`（ready 状态） | `self-debugger`（读 train.log） |
| `results.tsv`（历史） | `exp-planner`（下一轮 plan） |
| `program.md`（约束） | `exp-coder`（如果需要改代码） |

**与 self-debugger 的分工**：
- exp-runner 负责「让当前实验继续」
- self-debugger 负责「把失败经验沉淀给未来的 exp-coder/exp-runner」

**与 exp-planner 的分工**：
- 小幅调参（< 3 个参数变化）→ exp-runner 直接改 config
- 结构性变化（新模型、新 loss、新增文件）→ 回到 exp-planner 出新 plan

## 反模式

- ❌ monitor 跑 5 分钟没动就 panic → 应先看进程状态
- ❌ tune 在没有足够数据时随机搜索 → 至少 N=5 个非崩溃样本
- ❌ 自动重启无限循环 → 3 次上限
- ❌ tune 改了 program.md 禁止改的东西 → 永久黑名单
- ❌ monitor 修改了 src/ → 监控只能调 launcher
- ❌ 跑超过时间预算的实验 → 必须提前停止
- ❌ results.tsv 写重复行 → commit hash 唯一性检查

## 引用

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — 单文件 edit loop 哲学
- [knightli.com: Agent Loop Engineering](https://knightli.com/2026/06/10/loops-replace-prompts-agent-loop-engineering/) — Loops replace prompts 哲学
- 本 skill 设计参考 [exp-planner](../exp-planner/SKILL.md) 和 [exp-coder](../exp-coder/SKILL.md) 的 handoff 协议
