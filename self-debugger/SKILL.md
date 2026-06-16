---
name: self-debugger
description: "自我 debug / 自我学习层。通过 hooks 监听所有 agent 的失败事件，统一维护 code_debug.md，在下次 exp-coder / exp-runner 启动时注入历史教训。触发：失败发生时（hook 自动），不需要用户主动调用。"
user_invocable: true
version: "1.0.0"
---

# self-debugger: 自我 debug / 自我学习

## 定位

```
所有 agent (exp-planner / exp-coder / exp-runner)
        ↓ 失败事件
   self-debugger (hook)
        ↓
   code_debug.md (项目级)
        ↓
   下次 agent 启动 → SessionStart hook 注入
```

**职责**：把分散在各 agent 里的失败经验，沉淀成可被未来 agent 重用的知识。

**不负责**：直接修代码。修代码是 exp-coder 的工作。self-debugger 只**记录 + 注入**。

## 架构：Hook 驱动

self-debugger **不是被主动调用的 skill**——它通过 `settings.json` 的 hooks 自动运行。

### 必须配置的 hook 事件

| 事件 | 触发时机 | self-debugger 动作 |
|------|---------|-----------------|
| `PostToolFailure` | 任何工具失败（Bash 非零退出、Edit 报错、Read 不存在） | 解析 + 分类 + 追加到 `code_debug.md` |
| `Stop` | session 结束 | 把本 session 最后 N 次失败写入 `code_debug.md` |
| `SessionStart` | session 开始 | 读 `code_debug.md`，注入 `open` 状态条目到 agent context |
| `UserPromptSubmit` | 用户输入时 | 关键词命中（如「又崩了」）→ 显示相关历史条目 |

### 完整 Hook 配置（粘贴到 `<项目>/.claude/settings.json`）

完整可用的 JSON 见本目录 `hooks.example.json`。最小骨架：

```json
{
  "hooks": {
    "PostToolFailure": [
      {
        "matcher": "*",
        "hooks": [
          { "type": "command", "command": "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/log-tool-failure.sh" }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          { "type": "command", "command": "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/inject-lessons.sh" }
        ]
      }
    ]
  }
}
```

> ⚠️ Hook 事件名和 JSON schema 以 Claude Code 官方文档为准。本 skill 设计基于通用 hook 机制，迁移到新版本时核对事件列表。

## 工作流

### 阶段 A: 失败捕获（Failure Capture）

#### A.1 工具失败的解析

Hook 脚本（`log-tool-failure.sh`）从 stdin 接收 JSON：

```json
{
  "tool_name": "Bash",
  "tool_input": { "command": "python -m src.train" },
  "error": "Traceback ... KeyError: 'val_macro_f1'",
  "session_id": "abc123"
}
```

脚本应做：
1. 解析字段
2. 分类（启发式）
3. 追加到 `code_debug.md`
4. 退出码 0（**不要阻塞** agent 流程）

#### A.2 分类启发式

| 错误关键词 | 分类 |
|-----------|------|
| `ImportError`, `ModuleNotFoundError` | `infra` |
| `CUDA out of memory`, `cuda OOM` | `infra` |
| `FileNotFoundError`, `yaml.YAMLError` | `config` |
| `KeyError`, `AttributeError`, `TypeError` | `code` |
| `RuntimeError: shape`, `size mismatch` | `model` |
| `DataLoader worker`, `BrokenPipeError` | `data` |
| `nan`, `inf` (in loss context) | `code` |
| `git`, `merge conflict` | `infra` |
| 自定义关键词 `simplified`, `TODO` | `simplification` |

完整规则见 `classify.sh` 片段（hooks.example.json 同目录）。

### 阶段 B: 经验沉淀（Lesson Distillation）

#### B.1 模式检测

每次追加新条目后，self-debugger 检查：

- 同一分类 ≥ 3 次 `open` → 标记 `recurring`
- 同一错误信息（hash）≥ 2 次 → 标记 `regression-candidate`

#### B.2 提示词补丁建议（Prompt Patch Suggestion）

当检测到 recurring pattern 时，self-debugger 写一条特殊条目：

```markdown
## 🔴 Recurring Pattern Detected

- **分类**: `code`
- **出现次数**: 4 次 open
- **首次出现**: 2026-06-12
- **最近出现**: 2026-06-16
- **典型错误**: `KeyError: 'val_loss'` in src/train.py
- **建议**: 修改 exp-coder 提示词，加入「每次读取 metric key 必须先 assert key in metrics dict」

状态：`prompt-patch-pending`
```

下次 exp-coder 启动时，SessionStart hook 会注入这条建议到 agent context。

### 阶段 C: 修复验证（Fix Verification）

当 exp-coder 在后续 session 中报告「已修复」某条 `open` 条目：

1. exp-coder 在 `code_debug.md` 把条目从 `open` 改为 `resolved`，并写「修复手段」
2. self-debugger 在下一次 PostToolFailure 时扫描：
   - 同类错误 ≥ 7 天没出现 → 标记 `resolved-confirmed`
   - 再次出现 → 标记 `regression`（升级 severity）

### 阶段 D: 注入到下次 agent（Lesson Injection）

`SessionStart` hook 脚本（`inject-lessons.sh`）逻辑：

```bash
#!/usr/bin/env bash
CODE_DEBUG="${CLAUDE_PROJECT_DIR:-.}/code_debug.md"
[ -f "$CODE_DEBUG" ] || exit 0

# 提取 open + prompt-patch-pending 条目
OPEN=$(grep -B1 '\[open\]' "$CODE_DEBUG" | tail -20)
PATCH=$(grep -A6 'prompt-patch-pending' "$CODE_DEBUG" | tail -10)

if [ -z "$OPEN" ] && [ -z "$PATCH" ]; then exit 0; fi

cat <<EOF
## 🧠 self-debugger 提醒（自动注入）

以下问题在历史 session 中出现但未解决。请在本次工作中留意：

$OPEN

${PATCH:+### 提示词补丁建议
$PATCH}
EOF
```

**注入策略**：
- 最多注入最近 5 条 `open`
- 全部 `prompt-patch-pending` 都注入
- 总长度不超过 ~2000 字符（避免 context 噪声）

## code_debug.md 格式

项目根目录的 `code_debug.md`（自动生成 / 追加）：

```markdown
# code_debug: <项目名>

> 自动维护：self-debugger hook 写入 + exp-coder 主动记录
> 格式：[YYYY-MM-DD HH:MM] [分类] [状态] 描述

## 进行中（open）

### [2026-06-16 14:23] [code] [open]
- 工具: Bash
- 输入: `python -m src.train`
- 错误: `KeyError: 'val_macro_f1'`
- 上下文: src/train.py:142, compute_metrics() 访问 metrics['val_macro_f1']，但 evaluator 没返回这个 key
- 修复建议: 检查 src/evaluate.py 返回 dict 是否包含 val_macro_f1

### [2026-06-16 15:01] [infra] [open]
- 工具: Bash
- 输入: `python -m src.train training.epochs=100`
- 错误: `CUDA out of memory. Tried to allocate 1.5 GiB`
- 上下文: batch_size=32, image_size=224, swin_base
- 修复建议: batch_size → 16, 或加 gradient_checkpointing

## 已解决（resolved）

### [2026-06-12 09:14] [config] [resolved-confirmed]
- 错误: `yaml.YAMLError: expected mapping`
- 修复手段: configs/default.yaml 用了 tab 缩进，改成 2 空格
- 确认: 同类错误 7 天未再出现

## 🔴 Recurring Patterns

### [2026-06-16] [code] [prompt-patch-pending]
- 模式: KeyError on metric keys
- 出现次数: 4 次
- 建议: 修改 exp-coder 提示词，要求读取 metric 前 assert
```

## Hook 脚本实现

### `log-tool-failure.sh`（最小可用版）

```bash
#!/usr/bin/env bash
# Hook input (stdin): JSON {tool_name, tool_input, error}
set -e

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // "unknown"')
ERR=$(echo "$INPUT" | jq -r '.error // "unknown"' | head -c 500)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // .tool_input.file_path // ""' | head -c 200)
TS=$(date '+%Y-%m-%d %H:%M')

CODE_DEBUG="${CLAUDE_PROJECT_DIR:-.}/code_debug.md"

# 简易分类
CLASS="code"
echo "$ERR" | grep -qiE "OOM|cuda|import" && CLASS="infra"
echo "$ERR" | grep -qiE "yaml|FileNotFound|KeyError" && CLASS="config"
echo "$ERR" | grep -qiE "shape|size mismatch" && CLASS="model"
echo "$ERR" | grep -qiE "DataLoader|BrokenPipe" && CLASS="data"

cat >> "$CODE_DEBUG" <<EOF

### [${TS}] [${CLASS}] [open]
- 工具: ${TOOL}
- 输入: \`${CMD}\`
- 错误: \`${ERR}\`
EOF

exit 0
```

### `inject-lessons.sh`

```bash
#!/usr/bin/env bash
# SessionStart hook：把 code_debug.md 的 open 条目注入 agent context
CODE_DEBUG="${CLAUDE_PROJECT_DIR:-.}/code_debug.md"
[ -f "$CODE_DEBUG" ] || exit 0

# 取最近 5 条 open
LESSONS=$(grep -B1 '\[open\]' "$CODE_DEBUG" 2>/dev/null | tail -20)
[ -z "$LESSONS" ] && exit 0

cat <<EOF
## 🧠 self-debugger 提醒（自动注入）

历史未解决问题（最近 5 条）：

${LESSONS}
EOF
exit 0
```

完整版本（含 recurring 检测、prompt-patch 注入）见 `hooks.example.json` 注释。

## Hook 配置文件位置

### 项目级 hooks（**推荐**）

把 hooks 写到 `<项目>/.claude/settings.json`：

```json
{ "hooks": { ... } }
```

### 全局 hooks（慎用）

写到 `~/.claude/settings.json` 会影响**所有** session，可能误注入或拖慢。

**建议**：项目级启用，全局关闭。

### Hook 脚本位置约定

```
<项目>/
├── .claude/
│   ├── settings.json          # hooks 配置
│   └── hooks/
│       ├── log-tool-failure.sh
│       ├── inject-lessons.sh
│       └── classify.sh        # 错误分类规则
```

## 与其他 skill 的契约

| 触发源 | 读取方 |
|--------|--------|
| 所有 agent 的失败 | self-debugger（写） |
| exp-coder / exp-runner 下次启动 | self-debugger（读 + 注入） |
| exp-coder 修复后 | 自行更新 `code_debug.md` 状态 |

**与其他 skill 的关系**：
- self-debugger **不修代码**，只记录和注入
- exp-coder **必须**在 Phase 1 读 `code_debug.md` 再开工
- exp-runner 在 monitor 模式发现反复错误时，**主动**追加 `code_debug.md` 沉淀

## 反模式

- ❌ Hook 脚本太重（> 200ms 延迟）→ 用户体验差
- ❌ 静默吞错 → 必须在 `code_debug.md` 留痕
- ❌ 注入太多历史（> 20 条）→ agent context 被噪声淹没
- ❌ 自动修复 → 违反「self-debugger 只记录」的契约
- ❌ 跨项目共享 `code_debug.md` → 每个项目独立
- ❌ Hook 阻塞 agent（exit code != 0）→ 必须 fire-and-forget
- ❌ 在 hook 里读大文件 / 跑模型 → 拖慢每个 tool call

## 安装步骤

1. 本 skill 已在 `~/.claude/skills/self-debugger/`
2. 在项目 `.claude/settings.json` 添加 hooks 配置（参考 `hooks.example.json`）
3. 把 hook 脚本放到项目 `.claude/hooks/`
4. `chmod +x .claude/hooks/*.sh`
5. 验证：
   ```bash
   echo '{"tool_name":"Bash","tool_input":{"command":"false"},"error":"exit 1"}' | \
     bash .claude/hooks/log-tool-failure.sh
   cat code_debug.md  # 应有新条目
   ```

## 引用

- 本 skill 是 [program-md-designer](../program-md-designer/SKILL.md)、[exp-planner](../exp-planner/SKILL.md)、[exp-coder](../exp-coder/SKILL.md)、[exp-runner](../exp-runner/SKILL.md) 的横向支撑层
- Hook 机制参考 Claude Code 官方文档 [hooks](https://docs.claude.com/en/docs/claude-code/hooks)
- 自我学习循环设计灵感：[knightli.com: Agent Loop Engineering](https://knightli.com/2026/06/10/loops-replace-prompts-agent-loop-engineering/)
