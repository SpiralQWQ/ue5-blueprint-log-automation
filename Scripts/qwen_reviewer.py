#!/usr/bin/env python3
"""
qwen_reviewer.py — Qwen-Max 自动审阅脚本
==========================================
调用阿里云 Qwen-Max 模型，对 UE5 蓝图设计文档进行架构审阅。

Usage（任选一种）:
  1. 审阅指定文件:
     python qwen_reviewer.py [Demo素材]_v1.0.1_20260621_16.md

  2. 审阅指定文件 + 上下文报告:
     python qwen_reviewer.py [Demo素材]_v1.0.1_20260621_16.md GEMINI_CONTEXT_REPORT.md

  3. 在 UE5 Python 控制台中:
     import subprocess
     subprocess.run(["python", r"/Path/To/Your/UE_Project/tools/qwen_reviewer.py",
                     r"/Path/To/Your/UE_Project/[Demo素材]_v1.0.1_20260621_16.md"])

前提条件:
  - QWEN_API_KEY 环境变量已设置
  - requests 库已安装 (pip install requests)

输出:
  - 终端打印审阅结果
  - 保存到 /Path/To/Your/UE_Project/Review_Docs/Qwen_Review_Report.md（后续由 Skill 重命名为 NN_ 前缀规范文件名）
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional

# ============================================================================
# 配置
# ============================================================================

QWEN_ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
QWEN_MODEL = "qwen-max"
REVIEW_OUTPUT_DIR = r"/Path/To/Your/UE_Project/Review_Docs"
REVIEW_OUTPUT_FILE = "Qwen_Review_Report.md"

# ============================================================================
# System Prompt — 审阅维度定义
# ============================================================================

SYSTEM_PROMPT = """【角色设定】
你是一位资深 Unreal Engine 5 技术架构师，精通蓝图系统、Chaos 物理引擎、
Gameplay 框架（PlayerController/Pawn/GameMode/PlayerState 的 MVC 分层）、
蓝图接口（BPI）多态解耦、增强输入系统（Enhanced Input）。
你擅长审查蓝图设计文档中的架构漏洞、命名污染、耦合越界和技术描述错误。

【任务】
深度阅读以下 UE5 蓝图设计文档，按照五个维度进行审查并输出结构化报告。

【审查维度】

### A. 架构合理性（BPI 接口设计）
- BPI_Interact / BPI_Deliver / BPI_ControllerCommands / BPI_PlayerState 是否严格遵循接口隔离原则？
- 有无函数职责越界？NotifyRespawnReady() 的位置是否合理？
- BPI_BallInteraction (EatFood) 和 BPI_Interact (BallAdventure) 能否合并？

### B. 技术准确性
- 向量叉乘扭矩计算的 A×B 顺序在 UE5 左手坐标系下是否正确？
- Teleport flag 与 Chaos 物理引擎的交互描述是否准确？
- 假死四步序列的顺序依赖有无逻辑漏洞？
- Function vs Event vs Macro 选型框架的技术描述是否准确？

### C. 文档覆盖率
- 对照 26 个蓝图清单，哪些蓝图完全未被文档提及？
- BP_Vehicle_Car01 需要补充什么？
- EatFood/HitCube 关卡的描述深度是否充分？

### D. 格式与结构
- Markdown 表格的 | 管道符是否对齐？
- <br> 标签使用是否正确？

### E. 改进建议
- 基于 UE5 专业知识，给 5 条具体可操作的改进建议（精确到节点名或接口名）

【输出格式要求】
请严格按以下 Markdown 结构输出审阅报告，不要添加无关内容：

## Qwen-Max 架构审阅报告
> 审阅时间: {timestamp} | 模型: qwen-max

### A. BPI 接口设计
[逐点分析 + 判定结论]

### B. 技术准确性
[逐点分析 + 判定结论]

### C. 文档覆盖率
[逐点分析 + 缺失清单]

### D. 格式问题
[逐点检查结果]

### E. 优先级改进清单
| 优先级 | 目标蓝图 | 问题描述 | 改进方案 | 理由 |
|--------|---------|---------|---------|------|
| 高/中/低 | ... | ... | ... | ... |

### F. 多人联网风险点
[列出存在网络竞态风险的蓝图和节点，如无则写"未发现"]"""


# ============================================================================
# 核心逻辑
# ============================================================================

def read_file(file_path: str) -> Optional[str]:
    """安全读取文件，UTF-8 编码。"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERR] 文件不存在: {file_path}")
        return None
    except Exception as exc:
        print(f"[ERR] 读取失败: {file_path} — {exc}")
        return None


def build_user_message(design_doc: str, context_report: Optional[str] = None) -> str:
    """构建发送给 Qwen 的用户消息。"""
    parts = [
        "【待审阅的 UE5 蓝图设计文档】",
        "=" * 60,
        design_doc,
    ]
    if context_report:
        parts.extend([
            "",
            "【系统上下文报告（辅助理解）】",
            "=" * 60,
            context_report,
        ])
    parts.append("请按 System Prompt 的要求输出结构化审阅报告。")
    return "\n".join(parts)


def call_qwen(system_prompt: str, user_message: str) -> Optional[str]:
    """调用 Qwen-Max API 并返回响应文本。"""
    api_key = os.environ.get("QWEN_API_KEY")
    if not api_key:
        print("[ERR] QWEN_API_KEY 环境变量未设置", file=sys.stderr)
        print("  请设置: set QWEN_API_KEY=your-key  (PowerShell)", file=sys.stderr)
        print("  或: export QWEN_API_KEY=your-key    (Bash)", file=sys.stderr)
        print("[ERR] 程序终止：缺少必需的 API Key", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens": 8192,
    }

    try:
        import requests
        print(f"[...] 正在调用 {QWEN_MODEL} ...")
        resp = requests.post(
            QWEN_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        print(f"[OK] 收到响应 ({len(content)} 字符)")
        return content
    except ImportError:
        print("[ERR] 缺少 requests 库，请执行: pip install requests")
        return None
    except requests.exceptions.Timeout:
        print("[ERR] API 请求超时 (>120s)")
        return None
    except Exception as exc:
        print(f"[ERR] API 调用失败: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(f"  响应体: {exc.response.text[:500]}")
        return None


def save_report(content: str) -> str:
    """保存审阅报告到文件。"""
    os.makedirs(REVIEW_OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(REVIEW_OUTPUT_DIR, REVIEW_OUTPUT_FILE)

    timestamp = datetime.now(timezone.utc).isoformat()
    full_content = content.replace("{timestamp}", timestamp)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_content)

    return output_path


# ============================================================================
# 入口
# ============================================================================

def main() -> None:
    """主入口 — 解析参数、调用 Qwen、输出结果。"""
    if len(sys.argv) < 2:
        print("用法: python qwen_reviewer.py <设计文档.md> [上下文报告.md]")
        print("示例: python qwen_reviewer.py [Demo素材]_v1.0.1_20260621_16.md")
        print("      python qwen_reviewer.py 设计文档.md GEMINI_CONTEXT_REPORT.md")
        sys.exit(1)

    design_doc_path = sys.argv[1]
    context_report_path = sys.argv[2] if len(sys.argv) > 2 else None

    # 如果是相对路径，尝试在 Mydemo 目录解析
    if not os.path.isabs(design_doc_path):
        base = r"/Path/To/Your/UE_Project"
        design_doc_path = os.path.join(base, design_doc_path)

    print("=" * 60)
    print("Qwen-Max 蓝图架构审阅工具")
    print("=" * 60)
    print(f"  设计文档: {design_doc_path}")
    if context_report_path:
        if not os.path.isabs(context_report_path):
            context_report_path = os.path.join(
                r"/Path/To/Your/UE_Project/tools", context_report_path
            )
        print(f"  上下文报告: {context_report_path}")
    print()

    # 1. 读取输入文件
    design_doc = read_file(design_doc_path)
    if design_doc is None:
        sys.exit(1)

    context_report = None
    if context_report_path:
        context_report = read_file(context_report_path)

    # 2. 构建消息
    user_message = build_user_message(design_doc, context_report)
    print(f"[DOC] 设计文档: {len(design_doc)} 字符")
    if context_report:
        print(f"[DOC] 上下文报告: {len(context_report)} 字符")
    print(f"[MSG] 总消息长度: {len(user_message)} 字符")
    print()

    # 3. 调用 Qwen
    review_content = call_qwen(SYSTEM_PROMPT, user_message)
    if review_content is None:
        sys.exit(1)

    # 4. 终端输出
    print()
    print("=" * 60)
    print("审阅报告")
    print("=" * 60)
    print(review_content)

    # 5. 保存到文件
    output_path = save_report(review_content)
    print()
    print(f"[OK] 报告已保存: {output_path}")


if __name__ == "__main__":
    main()
