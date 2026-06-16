---
name: latex-experiment-report
description: "LaTeX 实验报告专用 skill。仅在用户撰写/编译 LaTeX 实验报告或遇到实验报告编译错误时触发。对于其他类型 LaTeX 文档（论文、简历、幻灯片等）不适用。"
user_invocable: true
version: "1.0.0"
---

# LaTeX 中文报告撰写规范

本 skill 提供用 LaTeX 撰写中文报告（实验报告、课程报告、技术报告等）的通用规范。下面所有示例信息需基于实际任务内容替换，不能照搬。重要的是**格式与结构**。

## 0. 原始文档处理流程（当提供 .doc/.docx 时）

### 0.1 原则

若用户提供了原始实验报告文档（.doc 或 .docx），必须遵循以下优先级：

> **封面格式与字体格式** — 优先从原文档提取并还原。
> **正文内容** — 原封不动复制，不允许删减、概括、改写。

### 0.2 操作流程

**Step 1：读取原始文档**

用 Python 从 .docx 中提取全部内容（包括封面信息、章节标题、正文、表格等）：
- 封面：学校名称、报告标题、学生信息、日期等。
- 正文：所有章节的完整文本，逐一保留。

**Step 2：优先还原原文档格式**

- 封面：提取原文档封面的布局、字体、字号，尽量在 LaTeX 中还原，而非套用通用封面模板。
- 字体：查看原文档使用的字体（宋体、黑体、楷体等），LaTeX 的 `ctex` 宏包有对应的 `\songti`、`\heiti`、`\kaishu` 命令。
- 字号：对照原文档正文和各级标题的实际字号，调整 `\ctexset` 和 `\zihao` 参数，使之匹配原文档。
- 行距：读取原文档行距设置，用 `\linespread{因子}` 还原。

> **提示**：`.docx` 本质是 ZIP 压缩包，内部的 `word/document.xml` 包含所有文本和格式信息。可用 `zipfile` + `xml.etree.ElementTree` 提取；字体、字号、行距等信息在 `word/styles.xml` 中。

**Step 3：向用户确认**

在生成 `.tex` 之前，向用户展示确认清单，等待用户确认后再继续：

```
请确认以下信息：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
封面内容：
  学校名称：    <提取到的值>        [正确/需修改]
  报告题目：    <提取到的值>        [正确/需修改]
  姓名/学号等：  <提取到的值>        [正确/需修改]

字体格式（若未从原文档提取到，则使用以下默认值）：
  一级标题：    黑体 加粗 小二       [确认/调整]
  二级标题：    黑体 加粗 四号       [确认/调整]
  正文：        宋体 小四           [确认/调整]
  行距：        1.5 倍              [确认/调整]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 0.3 内容完整性的硬性约束

当用户提供了原始文档时，以下部分**必须逐字复制**，不可改写：

| 部分 | 约束 |
|------|------|
| 封面信息 | 学校名称、报告标题、学生姓名学号等所有字段 |
| 实验目的/任务 | 一字不差复制原文档原文 |
| 实验内容与要求 | 一字不差复制原文档原文 |
| 实验步骤 | 一字不差复制，仅可在末尾补充说明 |
| 原理说明 | 不可删减，仅可修正明显的排版错误（如多余空格、换行） |

### 0.4 无原始文档时的默认行为

若用户**未提供**原始文档，则走默认流程：使用本 skill 第 1–7 节的通用模板和格式规范（封面模板、字体字号默认值等），并直接询问用户填写封面信息即可。

---

## 1. 文档导言区（Preamble）

### 文档类与基础宏包

```latex
\documentclass[UTF8]{ctexart}
\usepackage{geometry}
\usepackage{listings}
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{amsmath}
\usepackage{longtable}
\usepackage{float}      % 提供 [H] 强制图片定位
\usepackage{subcaption} % 子图排版
\usepackage{caption}    % 图表标题格式控制
\usepackage{tabularx}   % 弹性表格
\usepackage{enumitem}   % 列表格式控制
\usepackage{fancyhdr}   % 页眉页脚

\geometry{a4paper, margin=1in}
```

### 中文标题与编号设置

```latex
% ——— 章标题（一级标题） ———
% 格式：一、二、三（中文数字），黑体加粗，小二号字
\ctexset{
  section={
    number={\chinese{section}},
    format={\raggedright\heiti\zihao{-2}\bfseries},
    aftername={\hspace{1em}},
    beforeskip={3ex plus 0.2ex minus 0.2ex},
    afterskip={2ex plus 0.1ex minus 0.1ex},
  }
}

% ——— 节标题（二级标题） ———
% 格式：1.1、1.2（阿拉伯数字 + 章号前缀），黑体加粗，四号字
\ctexset{
  subsection={
    name={},
    number={\arabic{section}.\arabic{subsection}},
    format={\raggedright\heiti\zihao{4}\bfseries},
    aftername={\hspace{1em}},
    beforeskip={2ex plus 0.1ex minus 0.1ex},
    afterskip={1.5ex plus 0.1ex minus 0.1ex},
  }
}

% ——— 子节标题（三级标题） ———
% 格式：1.1.1（阿拉伯数字 + 完整前缀），黑体，小四号字
\ctexset{
  subsubsection={
    number={\arabic{section}.\arabic{subsection}.\arabic{subsubsection}},
    format={\raggedright\heiti\zihao{-4}},
    aftername={\hspace{0.5em}},
    beforeskip={1.5ex plus 0.1ex minus 0.1ex},
    afterskip={1ex plus 0.1ex minus 0.1ex},
  }
}
```

### 页眉页脚设置（可选）

```latex
\pagestyle{fancy}
\fancyhf{}
\fancyhead[C]{\heiti\zihao{-5} 报告标题}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0.4pt}
```

### 标题——封面页

```latex
\title{
    \vspace{-1cm}
    {\zihao{-0} \heiti \textbf{学校名称}} \\
    \vspace{1.5cm}
    {\zihao{-0} \songti \textbf{报告类型（如：课程报告/实验报告）}} \\
    \vspace{2.5cm}
    {\Large \textbf{报告题目：<REPORT_TITLE>}}
    \vspace{3cm}
}

\date{}
\author{
    \heiti \zihao{3}
    \begin{tabular}{ll}
    姓\quad\quad 名： & \underline{\makebox[5cm]{<NAME>}} \\
    学\quad\quad 号： & \underline{\makebox[5cm]{<ID>}} \\
    学\quad\quad 院： & \underline{\makebox[5cm]{<SCHOOL>}} \\
    专\quad\quad 业： & \underline{\makebox[5cm]{<MAJOR>}} \\
    指导老师： & \underline{\makebox[5cm]{<TEACHER>}} \\
    完成日期： & \underline{\makebox[5cm]{<DATE>}}
    \end{tabular}
}
```

---

## 2. 正文结构

### 文档正文起始

```latex
\begin{document}
\maketitle
\newpage
```

### 一级标题（章）

- 使用 `\section{一、xxx}`，注意章编号已自动为中文数字，标题前**不再加数字**。
- 格式：黑体、加粗、小二号。
- 示例：`\section{引言}` `\section{实验方法}` `\section{结果与分析}`

### 二级标题（节）

- 使用 `\subsection{xxx}`，编号自动为 `1.1` `1.2` 形式（章号.节号）。
- 格式：黑体、加粗、四号。

### 三级标题（子节）

- 使用 `\subsubsection{xxx}`，编号自动为 `1.1.1` `1.1.2` 形式。
- 格式：黑体、小四号。

### 正文文字

- 中文字体：宋体（`\songti`），小四号（`\zihao{-4}`）。
- 行距：1.5 倍行距（通过 `\linespread{1.5}` 或在导言区设置）。
- 英文/数字字体：Times New Roman（由 ctex 自动处理）。

---

## 3. 图表与代码

### 图片插入

```latex
% 单图：推荐 [H] 强制定位
\begin{figure}[H]
    \centering
    \includegraphics[width=0.7\textwidth]{图片文件名.png}
    \caption{图标题（宋体五号加粗，居中）}
    \label{fig:label}
\end{figure}

% 多子图
\begin{figure}[H]
    \centering
    \begin{subfigure}{0.45\textwidth}
        \centering
        \includegraphics[width=\textwidth]{图1.png}
        \caption{子图1}
    \end{subfigure}
    \hfill
    \begin{subfigure}{0.45\textwidth}
        \centering
        \includegraphics[width=\textwidth]{图2.png}
        \caption{子图2}
    \end{subfigure}
    \caption{总图标题}
    \label{fig:two}
\end{figure}
```

**图片注意事项：**
- 图片宽度通常取 `0.6\textwidth` ~ `0.85\textwidth`，大图可占满 `0.95\textwidth`。
- 图片文件放在 `.tex` 同级目录，**避免路径中含有空格或中文**。
- 推荐格式：PDF（矢量图）、PNG（截图）、JPG（照片）。
- 图片居中、有图号、有图标题。

### 表格

```latex
% 三线表（推荐用于正式表格）
\begin{table}[H]
    \centering
    \caption{表标题（宋体五号加粗，居中）}
    \label{tab:label}
    \begin{tabular}{lcccc}
        \toprule
        列名1 & 列名2 & 列名3 & 列名4 & 列名5 \\
        \midrule
        数据   & 数据   & 数据   & 数据   & 数据   \\
        \bottomrule
    \end{tabular}
\end{table}

% 长表格（跨页）
\begin{longtable}{|c|c|c|c|}
    \caption{跨页长表标题} \\
    \toprule
    列1 & 列2 & 列3 & 列4 \\
    \midrule
    \endfirsthead
    \multicolumn{4}{c}{\small 续表：表标题} \\
    \toprule
    列1 & 列2 & 列3 & 列4 \\
    \midrule
    \endhead
    \bottomrule
    \endfoot
    % 数据行...
\end{longtable}
```

**表格注意事项：**
- 表格标题在上，图标题在下（中文规范）。
- 正式表格优先用 `booktabs` 三线表。
- 过程性或数据量大的表可用 `|c|c|` 样式 + `\hline`。

### 代码列表

```latex
\lstset{
    language=Python,
    basicstyle=\ttfamily\small,           % 等宽字体，小号
    keywordstyle=\color{blue},
    stringstyle=\color{orange},
    commentstyle=\color{gray},
    numbers=left,                         % 行号
    numberstyle=\tiny\color{gray},
    stepnumber=1,
    numbersep=5pt,
    backgroundcolor=\color{white},
    showspaces=false,
    showstringspaces=false,
    showtabs=false,
    frame=single,
    rulecolor=\color{black},
    tabsize=4,
    captionpos=b,
    breaklines=true,
    breakatwhitespace=false,
    title=\lstname,
}

% 使用示例
\begin{lstlisting}[caption={代码说明}]
def hello():
    print("Hello, world!")
\end{lstlisting}
```

**代码注意事项：**
- 每段代码块不超过 30 行，过长时拆分为多个 `lstlisting`。
- 使用 `caption` 标注代码功能。
- 代码块内的 LaTeX 特殊字符不用转义。

---

## 4. 字体规范汇总

| 用途 | 字体 | 字号 | 加粗 |
|------|------|------|------|
| 封面学校名称 | 黑体 | 小初（`\zihao{-0}`） | 是 |
| 封面报告类型 | 宋体 | 小初（`\zihao{-0}`） | 是 |
| 封面信息栏 | 黑体 | 三号（`\zihao{3}`） | 否 |
| 一级标题（章） | 黑体 | 小二（`\zihao{-2}`） | 是 |
| 二级标题（节，编号 1.1/1.2） | 黑体 | 四号（`\zihao{4}`） | 是 |
| 三级标题（子节，编号 1.1.1） | 黑体 | 小四（`\zihao{-4}`） | 否 |
| 正文中文 | 宋体 | 小四（`\zihao{-4}`） | 否 |
| 正文英文/数字 | Times New Roman | 小四 | 按需 |
| 图/表标题 | 宋体 | 五号（`\zihao{5}`） | 是 |
| 代码 | 等宽字体（`\ttfamily`） | `\small` | 按语法 |

---

## 5. 编译指南

### 路径处理（最大错误来源）

**绝对不能**将含中文的路径直接传给 xelatex：

```powershell
# 错误 —— 反斜杠 + 中文 = LaTeX 转义灾难
xelatex "g:\code\homework\实验报告\report.tex"
```

**正确做法**：先 cd 到目录，再用文件名编译：

```powershell
cd "g:/code/homework/实验报告"
xelatex -interaction=nonstopmode report.tex
```

- 路径中使用正斜杠 `/`，不要用反斜杠 `\`。
- 始终使用 `-interaction=nonstopmode`，防止编译卡死在错误处。
- 编译两次以解析交叉引用。

### LaTeX 常见错误

| 错误 | 原因 | 修复 |
|------|------|------|
| `! Undefined control sequence` with path | 路径反斜杠被当作 LaTeX 命令 | 先 cd 再编译 |
| `! Missing $ inserted` | 下划线 `_` 出现在数学模式外 | 用 `\_` 或包在 `$...$` 中 |
| `! Missing } inserted` | 花括号不匹配 | 检查所有 `{}` 是否成对 |
| `! LaTeX Error: File not found` | 工作目录错误 | cd 到 .tex 文件所在目录 |
| `! Too many }'s` | lstlisting 内多余花括号 | 检查代码块中的大括号 |
| `! Package graphics Error: Cannot infer` | 图片格式/路径不对 | 确认图片存在且扩展名正确 |
| `Font shape undefined` 警告 | 字体不可用 | 可忽略，LaTeX 会替补 |
| `float specifier changed` 警告 | `[H]` 定位无效 | 可忽略，LaTeX 会自动调整 |

### 特殊字符转义

在 `lstlisting` 环境外：

| 字符 | 转义 |
|------|------|
| `_` | `\_` |
| `%` | `\%` |
| `&` | `\&` |
| `#` | `\#` |
| `$` | `\$` |
| `{` / `}` | `\{` / `\}` |
| `~` | `\textasciitilde{}` |
| `^` | `\textasciicircum{}` |

### 编译流程

```powershell
cd "<.tex 所在目录>"
xelatex -interaction=nonstopmode <文件名>.tex
xelatex -interaction=nonstopmode <文件名>.tex
```

检查输出：
- `Output written on <文件名>.pdf (N pages).` → 成功
- `!` 开头 → 错误，需修复
- `Warning` 开头 → 通常可忽略

---

## 6. 报告通用章节模板

不同报告类型推荐以下章节结构（可根据需求调整）：

### 实验报告

1. **一、实验目的与任务**
2. **二、实验内容与要求**
3. **三、实验原理与方法**
4. **四、实验步骤与代码实现**
5. **五、实验结果与分析**
6. **六、实验总结与心得体会**

### 课程报告 / 技术报告

1. **一、引言**（背景与问题）
2. **二、相关理论/技术概述**
3. **三、方案设计/方法论**
4. **四、实现与实验结果**
5. **五、讨论与分析**
6. **六、结论**

---

## 7. 常用条目

### 图片定位

- `\usepackage{float}` 提供 `[H]` 强制当前位置。
- 若无强制需求，可用 `[htbp]` 允许 LaTeX 自动优化位置。
- 封面页图片示例：

```latex
\begin{figure}[H]
    \centering
    \includegraphics[width=0.3\textwidth]{校徽.png}
\end{figure}
```

### 列表

**选择规则：**
- 条目数 $\le$ 3 时，用 `itemize`（圆点无序号）
- 条目数 $>$ 3 时，用 `enumerate`（数字 1. 2. 3. 罗列）
- 带标签的字段列表（如 原句/实体对/结果等）不受此限，始终用 `itemize`

```latex
% 无序列表（<=3项）
\begin{itemize}[leftmargin=2em]
    \item 要点一
    \item 要点二
    \item 要点三
\end{itemize}

% 有序列表（>3项）
\begin{enumerate}[leftmargin=2em]
    \item 第一步
    \item 第二步
    \item 第三步
    \item 第四步
\end{enumerate}
```

### 公式

```latex
% 行内公式
爱因斯坦的 $E=mc^2$ 是质能方程。

% 行间公式（编号）
\begin{equation}
    \sum_{i=1}^{n} i = \frac{n(n+1)}{2}
\end{equation}

% 行间公式（无编号）
\[
    f(x) = \int_{-\infty}^{\infty} \hat{f}(\xi) e^{2\pi i \xi x} \, d\xi
\]
```



## 8. 数据/代码示例框

当正文中需要展示数据格式示例、模型架构流程图、命令行输出等多行结构化内容时，不要仅用普通段落文本，应使用带背景色的边框框，与正文形成视觉区分。

### 基本用法

依赖 `xcolor` 宏包（preamble 中已含），使用 `\fcolorbox` + `minipage`：

```latex
\begin{center}
\fcolorbox{gray}{black!3}{\begin{minipage}{0.88\textwidth}
\ttfamily\small
数据行 1\
数据行 2\
...
\end{minipage}}
\end{center}
```

| 参数 | 含义 |
|------|------|
| 边框色 `gray` | 灰色细线 |
| 背景色 `black!3` | 3% 黑色 = 极浅灰底 |
| `0.88\textwidth` | 留出两侧间距 |
| `\ttfamily\small` | 等宽小号字（代码/数据） |

### 应用场景

| 场景 | 说明 | 字体 |
|------|------|------|
| 数据格式示例 | 行式数据格式 + 例句 | `\ttfamily\small` |
| 模型架构数据流 | 输入→层→输出的流程 | `\ttfamily\small` |
| 命令行操作步骤 | 多行命令序列 | `\ttfamily\small` |
| 简短代码片段 | 不适合独立 lstlisting 的短代码 | `\ttfamily\small` |
| 重要注释/说明 | 需要视觉突出的文字块 | 默认字体 |

### 完整示例

```latex
\begin{center}
\fcolorbox{gray}{black!3}{\begin{minipage}{0.88\textwidth}
\ttfamily\small
输入：sentence (B,L) + pos1 (B,L) + pos2 (B,L) \
$\downarrow$ 嵌入层 \
word\_embed(E=100) $\oplus$ pos1\_embed(P=25) $\oplus$ pos2\_embed(P=25) \
$\downarrow$ BiLSTM \
context = $\sum \alpha_i \cdot H_i$ $\rightarrow$ (B,200) \
$\downarrow$ \
Linear(200, num\_relations) $\rightarrow$ Softmax $\rightarrow$ (B, 11)
\end{minipage}}
\end{center}
```
