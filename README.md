# UE5 Blueprint Log Automation Toolchain

<p align="center">
  <img src="https://img.shields.io/badge/UE-5.7-blue?logo=unrealengine" alt="UE 5.7">
  <img src="https://img.shields.io/badge/Python-3.12+-green?logo=python" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/C++-Plugin-orange?logo=cplusplus" alt="C++ Plugin">
  <img src="https://img.shields.io/badge/AI_Review-Qwen_Max-purple?logo=alibabacloud" alt="Qwen Max">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT">
</p>

<p align="center"><b>一条命令，从 UE5 蓝图到结构化设计文档，全自动 AI 审阅。</b></p>

---

## 📖 这是什么？

一个专为 **Unreal Engine 5 蓝图开发者** 设计的自动化工具链。你在 UE5 中修改蓝图后，只需一行命令，系统自动完成：

1. **C++ 插件穿透蓝图节点图** — 提取每个节点的类型、引脚、连线、变量名
2. **Python 脚本导出为结构化 JSON** — 26 个蓝图的完整拓扑，约 1.2MB
3. **Claude Code Skill 五阶段自动化流水线** — 版本归档 → 笔记+拓扑交叉比对 → 结构化注入设计文档 → diff 验证 → AI 审阅
4. **Qwen-Max 自动审阅** — 架构合理性、技术准确性、文档覆盖率三重检查

**核心理念**：让你的设计文档成为"单一事实来源（Single Source of Truth）"，内容是蓝图节点图的真实投影，格式遵循 Knope + keepachangelog + Apple HIG 排版美学。

---

## ✨ Feature Highlights

| 特性 | 说明 |
|------|------|
| 🔬 **C++ 节点穿透** | 13 种 `K2Node_*` Cast 链，从 `UEdGraph` → `UEdGraphNode` → `UEdGraphPin` → `LinkedTo[]`，完整还原连线拓扑 |
| 🤖 **AI 双重审查** | 每次更新自动调 Qwen-Max 审阅架构/准确性/覆盖率；支持 Gemini 3.5 Flash 手动审阅 |
| 📝 **版本化管理** | 每次更新自动归档旧版 (`Old_DemoMateria_vX.X.X`)、生成新版 (`DemoMaterial_vX.X.X`)，全程无删减 |
| 🎨 **工业级排版** | 对标 Knope Changelog、keepachangelog、UE5 Release Notes、Apple HIG、Stripe 文档美学 |
| 🔗 **Obsidian 协同** | 与 Obsidian + RealClaudian 插件无缝联动，笔记 ↔ Agent 双向驱动 |
| 🛡️ **安全红线** | 词汇禁忌（禁止 JSON/拓扑确认/脚本提取 等泄露工具链痕迹）、数据守恒（只增不删） |

---

## 📁 仓库结构

```
UE日志工作流开源/
├── README.md                       ← 本文件
├── Claude_Skill/
│   └── SKILL.md                    ← Claude Code Skill 定义（五阶段流水线）
├── Scripts/
│   ├── export_bp_metadata.py       ← UE5 Python 导出脚本（370+ 行）
│   └── qwen_reviewer.py            ← Qwen-Max AI 审阅脚本
├── UE_CPP_Plugin/
│   ├── BlueprintTopologyExporter.h ← C++ 蓝图拓扑导出器头文件
│   └── BlueprintTopologyExporter.cpp ← C++ 蓝图拓扑导出器实现
└── Docs/
    ├── 工具链使用手册.md            ← 完整工具链使用手册（中文）
    └── Obsidian_Integration.md     ← Obsidian + RealClaudian 协同指南
```

---

## 🚀 环境要求

| 组件 | 版本要求 | 用途 |
|------|---------|------|
| **Unreal Engine** | 5.7 | 蓝图开发 + 运行 Python 导出脚本 |
| **Python** | 3.12+ | 导出脚本运行环境（UE5 内嵌 Python） |
| **Claude Code** | Latest | AI Agent，驱动自动化流水线 |
| **Obsidian** (可选) | 1.x+ | 笔记编写 + RealClaudian 会话同步 |
| **RealClaudian Plugin** (可选) | Latest | Obsidian 社区插件，管理 Claude Code 会话 |

> **硬件要求**: UE5 编辑器可正常运行即可。C++ 插件编译需要 Visual Studio 2022 + Windows SDK。

---

## 📦 安装

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/UE5-Blueprint-Log-Automation.git
cd UE5-Blueprint-Log-Automation
```

### 2. 安装 C++ 插件

将 `UE_CPP_Plugin/` 中的文件复制到你的 UE5 项目的 `Source/` 目录下：

```
Your_UE_Project/
└── Source/
    └── YourModule/
        ├── YourModule.Build.cs       ← 添加 Json, JsonUtilities, BlueprintGraph 等依赖
        ├── Public/
        │   └── BlueprintTopologyExporter.h
        └── Private/
            └── BlueprintTopologyExporter.cpp
```

**Build.cs 必需依赖**（添加到你的模块构建文件）：

```csharp
PrivateDependencyModuleNames.AddRange(new string[] {
    "UnrealEd",
    "BlueprintGraph",
    "KismetCompiler",
    "Kismet",
    "Json",
    "JsonUtilities"
});
```

编译前**关闭 UE5 编辑器**，然后执行：

```bash
# Windows (UE 5.7 示例)
E:\UE_5.7\Engine\Build\BatchFiles\Build.bat YourProjectEditor Win64 Development "YourProject.uproject"
```

### 3. 配置环境变量

在 Claude Code 的 `settings.json` 中配置 AI 审阅所需的 API Key：

```json
{
  "env": {
    "QWEN_API_KEY": "your-qwen-api-key",
    "GEMINI_API_KEY": "your-gemini-api-key"
  }
}
```

### 4. 安装 Claude Code Skill

将 `Claude_Skill/SKILL.md` 复制到以下任一位置：

- **项目级**: `Your_UE_Project/.claude/skills/ue-daily-logger/SKILL.md`
- **全局**: `~/.claude/skills/ue-daily-logger/SKILL.md`

### 5. 设置 Obsidian (可选)

1. 在 UE 项目根目录初始化 Obsidian Vault
2. 创建 `UENoteBook/` 目录存放开发笔记
3. 安装 RealClaudian 社区插件实现会话同步
4. 详细配置见 [`Docs/Obsidian_Integration.md`](Docs/Obsidian_Integration.md)

---

## 🎮 使用方法

### 日常工作流

```
步骤 1: 在 UE5 中修改蓝图
        │
步骤 2: 导出蓝图拓扑 JSON
        UE5 → Window → Output Log → 切换 Python → 输入：
        py "/Path/To/Your/UE_Project/tools/export_bp_metadata.py"
        │  输出: 26 蓝图已导出，1.2MB JSON 生成 ✅
        │
步骤 3: 在 Obsidian 中记录开发笔记
        写入 UENoteBook/ 对应笔记文件
        │
步骤 4: 对 Claude Code 说
        "更新UE日志"
        │
        ▼ 自动化流水线自动执行:
        ├─ 阶段一: 询问确认（回复"确认"继续）
        ├─ 阶段二: 版本归档（旧版 → Old_DemoMateria_vX.X.X.md）
        ├─ 阶段三: 排版注入（JSON 拓扑 + 笔记 → 卡片化设计文档）
        ├─ 阶段四: diff 验证（表格完整性检查）
        └─ 阶段五: Qwen-Max 审阅（报告存 Review_Docs/）
```

### 命令速查

| 操作 | 命令/触发词 |
|------|------------|
| 导出 JSON | `py "/Path/To/Your/UE_Project/tools/export_bp_metadata.py"`（UE5 Python 模式） |
| 更新日志 | 对 Claude Code 说 "更新UE日志" |
| Qwen 审阅 | "发给 Qwen 审阅" |
| Gemini 审阅 | "发给 Gemini 审阅" |
| 编译 C++ 插件 | `Build.bat YourProjectEditor Win64 Development "项目.uproject"` |

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────┐
│                    UE5 编辑器                          │
│                                                      │
│  [蓝图资产] → C++ BlueprintTopologyExporter           │
│              → Python export_bp_metadata.py           │
│              → ue_blueprint_status.json (1.2MB)       │
└─────────────────────┬────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────┐
│               Claude Code 自动化层                     │
│                                                      │
│  1. JSON 拓扑解析 (13种 K2Node, 完整引脚+连线)        │
│  2. UENoteBook 笔记读取 (理解设计意图)                │
│  3. 交叉比对 (JSON 数据 vs 文档现有内容 → 差异清单)    │
│  4. 结构化注入 (Knope 卡片化区块 + Apple HIG 排版)     │
│  5. diff 验证 (管道符对齐 + 零删减检查)               │
│  6. Qwen-Max API 审阅 (架构/准确性/覆盖率)            │
└─────────────────────┬────────────────────────────────┘
                      │
                      ▼
            DemoMaterial_vX.X.X_时间戳.md  (设计文档)
            Review_Docs/NN_Qwen_Review_*.md    (审阅报告)
```

### C++ 节点穿透链路

```
UBlueprint
  ├─ UbergraphPages[]          ← 事件图 (EventGraph, BeginPlay, Tick)
  └─ FunctionGraphs[]          ← 自定义函数图 (BPI 实现, 纯函数)
        │
        ▼
      UEdGraph                 ← 单个图表
        └─ Nodes[]             ← UEdGraphNode 数组
              ├─ K2Node_CallFunction   → 函数调用 → FunctionReference
              ├─ K2Node_Event         → 引擎事件 → EventReference
              ├─ K2Node_CustomEvent   → 自定义事件 → CustomFunctionName
              ├─ K2Node_VariableGet   → 读变量 → VariableReference
              ├─ K2Node_VariableSet   → 写变量 → VariableReference
              ├─ K2Node_Timeline      → 时间线 → TimelineName
              ├─ K2Node_DynamicCast   → Cast → TargetType
              ├─ K2Node_IfThenElse    → Branch
              └─ ... (共 13 种)
              └─ Pins[]       ← UEdGraphPin 数组
                    ├─ PinId → FGuid 全局唯一标识
                    ├─ PinName → "exec" / "then" / "ReturnValue"
                    ├─ Direction → EGPD_Input / EGPD_Output
                    └─ LinkedTo[] → ★ 连线目标
```

---

## 🔒 隐私与安全

### 脱敏声明

本项目所有示例文件已完成隐私脱敏：

- 绝对路径 → 通用占位符 (`/Path/To/Your/UE_Project/`)
- Windows 用户名 → `YourUsername`
- API Key → `YOUR_API_KEY_HERE`

**开始使用前，请务必设置你自己的路径和 API Key。**

### ⚠️ 知识产权保护（重要）

本工具链导出的 `ue_blueprint_status.json` 包含完整的蓝图节点拓扑——即你的**核心游戏逻辑**。请严格遵守以下规则：

- 🚫 **禁止提交** `ue_blueprint_status.json` 到公共 Git 仓库
- 🚫 **禁止提交** `Saved/BlueprintTopology/` 目录
- ✅ 使用仓库自带的 `.gitignore` 文件自动排除敏感输出
- ✅ 将 `.gitignore` 复制到你的 UE 项目根目录

### API Key 安全

- 所有 API Key 通过**环境变量**读取，不硬编码在源码中
- 未配置环境变量时脚本立即终止 (`sys.exit(1)`) ，不会回退到任何硬编码值
- 推荐使用 `.env` 文件管理 Key（`.gitignore` 已排除 `*.env`）

---

## 📄 文件命名规范

### 设计文档

| 类型 | 格式 | 示例 |
|------|------|------|
| 活跃版本 | `DemoMaterial_vX.X.X_YYYYMMDD_HH.md` | `DemoMaterial_v1.0.6_20260621_21.md` |
| 归档版本 | `Old_DemoMateria_vX.X.X_YYYYMMDD_HH.md` | `Old_DemoMateria_v1.0.5_20260621_20.md` |
| Qwen 审阅 | `NN_Qwen_Review_vX.X.X_YYYYMMDD_HH.md` | `15_Qwen_Review_v1.0.6_20260621-2219.md` |
| Gemini 审阅 | `NN_Gemini_Review_vX.X.X_YYYYMMDD_HH.md` | `14_Gemini_Review_v1.0.6_20260621-2219.md` |

### 蓝图资产

| 前缀 | 类型 | 示例 |
|------|------|------|
| `BP_` | Blueprint Actor | `BP_Door01`, `BP_Crystal` |
| `BPI_` | Blueprint Interface | `BPI_Interact` |
| `WBP_` | Widget Blueprint | `WBP_DeathScreen` |
| `IA_` | Input Action | `IA_Jump` |
| `IMC_` | Input Mapping Context | `IMC_Ball` |
| `E_` | Enum | `E_PlayerAttributes` |

---

## 📊 项目统计 (参考数据)

以下数据来自本工具链的实际生产部署（26 个蓝图项目）：

| 指标 | 数值 |
|------|------|
| 蓝图总数 | 26 (22 Blueprint + 4 WidgetBlueprint) |
| BPI 接口 | 5 套 |
| 最大蓝图 | `BP_BallAdventurePlayerPawn` (227 节点 / 175 连线 / 43 函数 / 10 事件 / 15 变量) |
| JSON 大小 | ~1.2MB / 次导出 |
| C++ 导出器 | 370 行 Python + 400 行 C++ |

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request。在提交前请确保：

1. 代码符合 UE5 C++ 编码标准
2. Python 脚本通过 PEP 8 检查
3. 文档更新与代码变更同步

---

## 📜 许可

MIT License — 详见 [LICENSE](LICENSE) 文件。

---

<p align="center">
  <sub>Built with ❤️ by a UE5 developer who hates manually updating design docs.</sub>
</p>
