---
name: exp-coder
description: "代码撰写者。读取 exp-planner 产出的 plan_<NN>.md 与 program.md，按规划撰写/修改实验代码，严格实现提到的技术，简化任何框架必须在 plan 文档里显式声明，维护 code_debug.md 记录问题与修复。触发词：'写代码'、'实现 plan'、'implement plan'、'写实验代码'。"
user_invocable: true
version: "1.0.0"
---

# exp-coder: 实验代码撰写者

## 定位

```
exp-planner  →  docs/experiments/plan_<NN>.md (状态: ready)
                       ↓
                    exp-coder            ← 你在这里
                       ↓
                 src/ 变更 + code_debug.md 更新
                       ↓
                    exp-runner
```

**职责**：把规划文档翻译成可运行的代码，且不超出 program.md 约束。

**不负责**：跑训练、调参、修改 program.md、修改 plan（plan 修改需回到 exp-planner）。

## 何时调用

- 用户：「按这份 plan 把代码写出来」
- 用户：「实现 DINOv2 + focal loss」
- exp-runner：「code 还没准备好」

## 工作流（5 阶段）

### Phase 1: 双向读取（Dual-Read Context）

读取以下文件，构建实施依据：

| 文件 | 目的 | 必读？ |
|------|------|------|
| `docs/experiments/plan_<NN>.md` | 要实现什么 | ✅ |
| `program.md` | 约束（可改/不可改、依赖、时间预算） | ✅ |
| `code_debug.md`（如存在） | 历史失败模式，避免重蹈 | ✅ |
| 当前 `src/` 布局 | 找到正确的插入点 | ✅ |
| 引用的论文 / 仓库 | 技术保真度 | 如有引用则必读 |

**关键判断**：
- plan 里提到的「严格实现」技术是什么？读了原始论文/源码没有？
- 现有代码结构和 plan 的「代码架构」一节是否一致？
- code_debug.md 里有反复失败的模式吗？

### Phase 2: 实施前确认（Pre-Implementation Confirmation）

在动键盘前，**先回答以下 4 个问题**——任何一项没答案都不能写代码：

1. **修改边界**：哪些文件修改 / 哪些新增 / 哪些**绝对不动**？
2. **依赖检查**：是否需要新包？检查 `pyproject.toml` / `requirements.txt`，**没有就不要装**
3. **简化预案**：plan 里有没有提到要简化某个框架？（如「基于 timm 但只取 encoder」）→ **必须先在 plan 文档追加「Simplifications」节**
4. **技术保真度**：plan 引用的关键技术（如 DINOv2 的 register tokens、focal loss 的 α）是否需要重读原始实现？

### Phase 3: 分块实施（Chunked Implementation）

#### 3.1 单次只改一个文件

每次 Edit/Write 只针对一个文件，改完做：
- 语法检查：`python -m py_compile <file>`
- 导入检查：`python -c "import <module>"`（确保没有 ImportError）

通过再做下一个文件。

#### 3.2 实施顺序（推荐）

1. **常量 / 配置先行**：先改 `configs/default.yaml` 或 config 区
2. **数据层**：`dataset.py` 只读；`transforms.py` 可调 → 修改
3. **模型层**：`models/__init__.py` 注册表不动；`models/<name>.py` 可读不可改 forward
4. **训练循环**：`train.py` 是主战场
5. **可视化 / 日志**：在 train loop 末尾挂上 chart 生成

#### 3.3 严格保真度（Strict Fidelity）

如果 plan 提到「严格按论文实现」或「复现 X 仓库」：

- **必须**重读原始仓库 / 论文，不能凭印象写
- 关键超参数（学习率、warmup、weight decay、α、γ）从原仓库抄
- 如果原仓库用 Apex / 旧 API → 在 `code_debug.md` 记录
- 简化必须**显式声明**：

```markdown
## ⚠️ Simplifications（必须追加在 plan 文档末尾）

| 原版组件 | 本次实现 | 影响评估 |
|----------|---------|---------|
| Apex FusedAdam | torch.optim.AdamW | 收敛速度可能略慢 |
| DINOv2 registers (4) | 关闭 | 分类头不依赖 register tokens |
| CosineAnnealingWarmRestarts | CosineAnnealingLR | 无重启，可能影响最终精度 |
```

**写代码前先动 plan 文档**——这是承诺，不能事后补。

#### 3.4 日志模块验证（Logger Contract）

每写完一个文件，问自己：「如果训练在这里崩了，日志能告诉我什么？」

**最小日志契约**：

```python
import logging
logger = logging.getLogger(__name__)  # NOT root logger

# 关键事件必须记录
logger.info(f"Config: {cfg}")                          # 启动时
logger.info(f"Model params: {sum(p.numel() for p in model.parameters()) / 1e6:.2f}M")
logger.warning(f"NaN loss at step {step}")              # 异常
logger.error(f"Checkpoint failed: {e}")                 # 失败
logger.info(f"Exp dir: {exp_dir}")                      # 输出路径
```

**反模式**：
- ❌ 用 `print()` 而不是 `logger`
- ❌ 异常路径不打日志
- ❌ 日志写到 stdout（应同时写文件 + stdout）

**验证方法**：写一个最小脚本触发各分支，确认日志输出能被 self-debugger 解析。

### Phase 4: smoke test（冒烟测试）

实施完成后、交给 exp-runner 前，**必须**通过：

#### 4.1 静态检查

```bash
python -c "import src.train"           # 导入无错
python -m py_compile src/train.py      # 语法无错
```

#### 4.2 单步 dry-run（如适用）

```bash
# 1 epoch + 1 batch + 强制早停
python -m src.train training.epochs=1 training.max_steps=5 \
    training.dry_run=true 2>&1 | tee /tmp/dryrun.log
```

**必须满足**：
- 无 Traceback
- train.log 写到 `runs/<exp_id>/train.log`
- metrics.jsonl 至少 5 行
- best.pt 路径正确（dry-run 模式下不保存也可，但路径必须存在）

#### 4.3 检查清单

- [ ] 导入全部 OK
- [ ] 1 个 epoch 跑通（即使是 dummy 数据）
- [ ] 日志写到正确路径
- [ ] checkpoints 路径正确
- [ ] 配置文件解析无误
- [ ] 无 warning 升级为 error
- [ ] code_debug.md 已更新本轮实施记录

### Phase 5: 更新 code_debug.md

无论成功失败，**必须**更新 `code_debug.md`（项目根目录）。

**条目格式**：

```markdown
### [YYYY-MM-DD HH:MM] [<分类>] [<状态>]
- 工具/模块: <哪个文件>
- 输入: <触发命令或代码>
- 错误: `<错误摘要>`
- 上下文: <文件:行号 + 场景>
- 修复手段: <做了什么修复，或 wontfix 的理由>
```

**分类枚举**：

| 分类 | 触发场景 |
|------|---------|
| `config` | YAML / argparse / 环境变量问题 |
| `code` | Python 语法、API 误用、版本不兼容 |
| `data` | 数据路径、shape、dtype 不匹配 |
| `model` | 前向维度、参数加载 |
| `infra` | GPU/CUDA/磁盘/权限 |
| `simplification` | 框架简化引入的偏差 |

**状态枚举**：
- `open` — 未解决
- `resolved` — 已解决，记录修复手段
- `wontfix` — 决定不修（写明理由）
- `superseded` — 被后续实验取代

**完整示例**：

```markdown
### [2026-06-15 10:11] [config] [resolved]
- 工具: Bash
- 输入: `python -m src.train training.epochs=100`
- 错误: `KeyError: 'data_dir'`
- 上下文: src/train.py:42, cfg.data 是 None
- 修复手段: configs/default.yaml 缺 `data:` 段，补全后正常

### [2026-06-16 14:23] [simplification] [open]
- 工具: Edit
- 输入: src/models/dinov2_model.py
- 错误: 简化了 register tokens
- 上下文: 原 DINOv2-vitb14 有 4 个 register tokens，本次实现未加
- 影响: 分类精度可能下降 0.5-1pp，未量化
- 修复手段: 暂未修
```

## 输出清单

完成时，exp-coder 必须产出/更新：

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/...` | 修改/新增 | 按 plan 的代码架构节 |
| `docs/experiments/plan_<NN>.md` | 追加「Simplifications」节 | 如有框架简化 |
| `code_debug.md` | 追加 | 实施过程的问题 |
| `docs/experiments/INDEX.md` | 状态置为 `ready` | 通知 exp-runner |

## 与其他 skill 的契约

| 上游 | 下游 |
|------|------|
| `docs/experiments/plan_<NN>.md` | `exp-runner`（按 plan 跑实验） |
| `program.md`（约束） | `self-debugger`（读 train.log + code_debug.md） |
| `code_debug.md`（既有记录） | |

**handoff 协议**：
- exp-coder 完成 → 把 plan 状态改为 `ready`
- exp-runner 检测到 `ready` 状态 → 启动实验
- 实验失败 → self-debugger 读 train.log → 追加 code_debug.md → 下次 exp-coder 启动时通过 SessionStart hook 读

## 反模式

- ❌ 凭印象实现论文细节 → 必须重读原仓库
- ❌ 简化框架不写 plan → 失信，事后补不算
- ❌ 一次 Edit 多个文件 → 难以回滚
- ❌ 不做 smoke test 就交付 → exp-runner 必然崩溃
- ❌ 把所有日志用 `print()` 而不是 `logger` → self-debugger 无法解析
- ❌ code_debug.md 不更新 → self-debugger 失忆
- ❌ 修改 plan 文档（除追加 Simplifications 外）→ 越权，应回到 exp-planner
- ❌ 跳过 Phase 1 直接写 → 重蹈已记录的失败

## 引用

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — 编辑边界哲学
- 本 skill 设计参考 [exp-planner](../exp-planner/SKILL.md) 的 handoff 协议
- 配合 [self-debugger](../self-debugger/SKILL.md) 形成「失败→记录→下次避免」闭环
