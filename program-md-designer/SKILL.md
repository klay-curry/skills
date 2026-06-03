---
name: program-md-designer
description: "实验协议设计师。分析项目代码框架、目标和本地算力，为项目量身设计 autoresearch 风格的 program.md（实验编程协议）。让任何项目都能获得其专属的 agent 驱动实验循环。触发词：'设计program.md'、'创建实验协议'、'program design'、'程序化实验设计'、'autoresearch setup'、'编程实验循环'。"
user_invocable: true
version: "1.1.0"
---

# program-md-designer: 实验协议设计师

## 核心思想

本 skill 的灵感来自 [karpathy/autoresearch](https://github.com/karpathy/autoresearch) 的 `program.md` 设计哲学。

**program.md 不是说明书，是实验协议。**
- 说明书告诉 agent "怎么做"，实验协议定义"能做什么、不能做什么、怎么算赢"
- 它把人类从循环中踢出去——agent 自主实验、自主判断、自主迭代
- 它是可迭代的元代码——人类不调模型参数，调 program.md

**一份好的 program.md 让 agent 在无人干预的情况下自动跑完 100+ 轮实验。**
它的核心设计维度：

| 维度 | 问题 | 设计原则 |
|------|------|---------|
| **Scope** | agent 改什么？不改什么？ | 锁定一个可改文件，其余只读 |
| **Metric** | 什么叫变好了？ | 单一数字，无歧义，越低/越高为好 |
| **Budget** | 每轮跑多久？ | 固定 wall-clock，使实验可比 |
| **Loop** | agent 怎么迭代？ | 修改→跑→读结果→记录→前进/回退 |
| **Autonomy** | agent 何时需要 humans-in-loop？ | 永远不需要，或只在预设边界 |
| **Safety** | 跑炸了怎么办？ | OOM/崩溃的处理预案 |
| **Simplicity** | 复杂度和收益怎么权衡？ | 显式 criterion |

## 三阶段工作流

### 第一阶段：扫描解剖（Scaffold Scan）

目标：理解项目的骨架，识别 agent 的可操作空间。

#### 1.1 项目骨架识别

读取以下文件（按优先级，存在即读）：

| 文件 | 读取目的 |
|------|---------|
| `README.md` | 项目目标、使用方式、核心概念 |
| `pyproject.toml` / `Cargo.toml` / `package.json` | 依赖、项目元信息 |
| 所有 `.py` / `.rs` / `.ts` / `.js` 源文件 | 代码结构、入口点、关键函数 |
| `Makefile` / `Justfile` / `scripts/` | 构建和运行方式 |
| 任何已有 `.md` 文档 | 设计思路、约束 |

#### 1.1.5 实验蓝图确认 ⚠️

读完所有 `.md` 后，做一件事：**向用户展示发现，确认实验蓝图是谁。**

**为什么需要这一节**：项目可能有多份 `.md` 文档（README / 设计文档 / API 文档 / 笔记等）。其中哪一份是 agent 的实验蓝图——即描述「项目目标、模型选择、实验策略、评估方式」的核心文档——需要用户确认，不能全靠猜测。

**执行步骤**：

1. **列出所有找到的 `.md` 文件路径**
2. **分析每份文档的类型**：
   - README → 项目简介（通常不是实验蓝图）
   - 包含"模型梯队 / 实验顺序 / 策略 / 备赛 / Design / Roadmap"等关键词 → **可能是实验蓝图**
   - 行数多、提及代码结构/模型架构/训练策略 → **可能是实验蓝图**
   - 被其他 `.md` 文件显式引用（如 `program.md` 中说"详见 `docs/xxx.md`"）→ **高概率是实验蓝图**
3. **形成判断**：哪份或哪几份文档是实验蓝图
4. **向用户提问确认**：

   ```
   找到 N 份 Markdown 文档：
   - docs/README.md — 项目简介
   - docs/competition_roadmap.md — 包含模型梯队、实验顺序、防御策略 ← 我判断这是实验蓝图
   - docs/notes.md — 个人笔记
   
   我判断实验蓝图是：docs/competition_roadmap.md
   请问对吗？还是有其他文档才是？
   ```

5. **根据用户反馈修正**。如果用户说"对"，继续；如果用户说有另一份文档才是，去读取那份。

**万一所有 `.md` 都不是实验蓝图**（比如项目还没有写设计文档）→ 跳过确认，进入后续阶段从代码中提取目标。

#### 1.2 编辑边界分析

识别三类文件：

- **可修改文件（Mutable）**：agent 可以随意编辑。通常是且仅是一个文件——模型的架构文件、算法的核心实现等。
- **固定文件（Immutable）**：agent 不可修改。通常是数据准备、评估函数、基础设施代码。这些定义了下游无法篡改的 ground truth。
- **配置文件（Config）**：agent 可调整参数但不动逻辑的文件。

**判定标准**：可修改文件应该 1）是实验循环的核心杠杆点，2) 改动能直接影响目标指标。

#### 1.3 核心组件映射

识别项目中的这些关键接口：

| 组件 | 必须存在？ | 说明 |
|------|-----------|------|
| 入口执行方式 | 是 | `uv run train.py` / `cargo run` / `npm start` |
| 目标指标 | 是 | val_loss / accuracy / throughput / latency |
| 评估函数 | 强推荐 | 一个不可篡改的评估调用 |
| 数据准备 | 推荐 | 一次性的数据下载和预处理 |
| 配置文件/常量区 | 推荐 | agent 可以调整的超参数区域 |

#### 1.4 目标函数提取

在一份好的 program.md 中，目标函数必须是：

1. **单一数字** —— 不是多个指标的加权和
2. **无歧义方向** —— lower is better 或 higher is better
3. **不可篡改** —— 评估代码在不可修改的文件中
4. **可比性** —— 不受硬件变化影响（或做了归一化）

如果项目本身没有清晰的单一指标，设计一个代理指标（proxy metric）。例如：
- 训练时间固定时 → val_loss / throughput
- 无监督任务 → 重构误差 / 熵
- 系统优化 → P99 latency / 内存峰值

---

### 第二阶段：算力评估（Compute Survey）

目标：摸清本地硬件，设计合适的时间预算和资源约束。

#### 2.1 硬件探测

执行一系列探测命令获取本地算力信息：

```bash
# GPU 探测
python -c "import torch; print(torch.cuda.get_device_properties(0)); print(torch.cuda.get_device_capability())"

# CPU 探测
python -c "import os; print(os.cpu_count())"

# 内存探测
python -c "import psutil; print(f'{psutil.virtual_memory().total / 1024**3:.1f} GB')"
```

记录：GPU 型号、VRAM、CUDA capability、CPU 核心数、系统内存。

#### 2.2 时间预算设计

时间预算决定了：
- 每轮实验的粒度
- 一晚上能跑多少轮（≈ 睡眠时间 / 时间预算）
- 实验可比性的锚点

**经验法则**：
- ML 训练任务：5-10 分钟是 sweet spot（≈ 12-6 轮/小时，~100 轮/晚）
- 编译型任务（Rust/C++）：考虑编译时间，预算需包含编译
- 数据/系统任务：1-3 分钟足够
- 如果项目有 checkpoint/预热期，预算需覆盖预热

**一定要用 wall-clock time，不用 step count。** 这样 agent 改架构（变大/变小）后实验结果仍然可比。

#### 2.3 资源约束推算

基于探测到的硬件，估算：

- **最大模型尺寸**（ML 项目）：VRAM 决定模型能多大、batch size 能多大
- **并行度**：CPU 核心数决定 data loading 和预处理能多快
- **内存墙**：系统内存决定数据集能多大
- **精度选择**：CUDA capability >= 8.0 可用 bf16，否则 fp16

---

### 第三阶段：协议生成（Protocol Synthesis）

目标：将前两阶段的发现合成为一份完整的 `program.md`。

#### 3.1 协议模板

生成的 `program.md` 遵循以下结构（每节说明 + 填充内容）：

```markdown
# <项目名>: 自主实验协议

## Setup

[如何初始化实验环境]

### 前置条件
- 需要运行的依赖安装命令
- 需要执行的数据准备
- 验证 setup 成功的 smoke test 命令

### 文件清单
- **可修改**：`train.py`（或等）—— agent 可随意编辑
- **只读**：`prepare.py`, `evaluate.py`（或等）—— 固定不变
- **配置**：（可选）

### 首次运行
先跑一遍 baseline，建立基准指标。

## 实验规则

### 时间预算
每轮实验固定 wall-clock 时间：<N> 分钟。

### 可以做
- 修改可修改文件的一切：架构、超参数、训练循环、批处理大小、模型尺寸等
- 添加/移除代码模块
- 拆解和重构代码

### 不可以做
- 修改只读文件
- 安装新的依赖包
- 修改评估函数
- 更改数据预处理流程
- 超出 <X> GB VRAM

### 目标指标
- 主指标：<metric_name>（<lower/higher> is better）
- 辅助指标：（可选）

### 复杂度准则
[显式写出 how to trade off complexity vs improvement]
例如："0.01 val_bpb improvement 但增加 20 行难读代码？不值得。0.001 改善但删了代码？保留。改简单了指标不变？保留。"

## 实验循环

LOOP FOREVER:

1. 读取当前 git 状态（分支/commit）
2. 修改可修改文件，实现一个实验想法
3. git commit
4. 运行实验（重定向输出到 run.log）
5. 读取结果指标
6. 如果跑炸了：检查日志 -> 修 bug -> 重试；如果想法本身有问题 -> 跳过
7. 记录到 results.tsv
8. 如果指标变好 -> advance branch（保留 commit）
9. 如果指标变差/持平 -> git reset 回退
10. 如果超时 -> 杀掉进程，视为失败并回退
11. 如果卡住 -> 重新读代码，找新角度，组合之前的 near-misses

## 输出格式

[定义实验运行结束后打印的 summary 格式]
[需要包含：目标指标值、时间消耗、资源消耗、关键 config]

## 日志格式

results.tsv 格式：
| commit | <metric> | <resource> | status | description |
|--------|----------|------------|--------|-------------|
| abc1234 | 0.9979 | 44.0 | keep | baseline |

## 自主规则
- 永远不询问"还要继续吗"
- 永远不询问"这样可以吗"
- 直到被人为中断才停止
- 想不出新主意时：重读代码、读引用论文、组合之前的 near-misses、做更激进的改动
```

#### 3.2 定制要点

生成时，根据项目类型调整协议细节：

**ML 训练项目**：
- 时间预算聚焦训练时间（不含启动/编译）
- autotune batch size / checkpointing
- 模型架构、优化器、学习率是主要杠杆
- 关注 VRAM 墙

**编译型项目（Rust/C++）**：
- 时间预算包含编译时间
- 编译缓存策略
- 关注编译错误和链接错误处理
- benchmark 作为评估函数

**数据处理/ETL 项目**：
- 时间预算较短（1-3 分钟）
- 关注吞吐量和资源使用
- 输入数据可重复性好

**系统/网络项目**：
- 时间预算包含 warmup 和 cooldown
- 关注 P99 / 吞吐量 / 错误率
- 可能需要多轮取稳定值

**通用优化项目**：
- 定义清晰的可复现 benchmark
- 关注 wall-clock time 和资源使用
- 可能需要预热轮

#### 3.3 安全护栏

生成的 program.md 应始终包含这些安全条款：

- **崩溃处理**：OOM 等资源异常 → 尝试下一组更保守的参数
- **超时处理**：超过 N 倍时间预算 → kill，标记为失败
- **发散检测**：loss exploding / 数值异常 → 提前终止
- **资源监控**：VRAM / 内存使用不应无限增长
- **回滚机制**：git reset 保证失败实验不影响分支

---

## 输出交付

生成后：

1. 将完整 `program.md` 写入项目根目录
2. 同时生成 `results.tsv` 模板（仅含 header）
3. 报告协议要点总结：

```
项目:          <项目名>
可修改文件:    <文件名>
固定文件:     <文件名>
目标指标:     <指标名> (<方向>)
时间预算:     <N> 秒
算力配置:     <GPU 型号 / CPU 核心数 / 内存>
预期轮次:     <X 轮/小时>
```

---

## 引用

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — 设计哲学来源
- [karpathy/nanochat](https://github.com/karpathy/nanochat) — 上游训练代码
- Karpathy 推文：[autoresearch 源起](https://x.com/karpathy/status/2029701092347630069)
