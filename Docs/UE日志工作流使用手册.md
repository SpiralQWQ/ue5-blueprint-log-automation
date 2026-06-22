# UE5 蓝图日志自动化工具链 — 完整使用手册

> 目标读者：Gemini（作为架构审查专家理解整个自动化流水线）
> 最后更新：2026-06-21 22:00 UTC+8 | 排版协议版本：v1.0.9（R3 终审。Demo01 9 子表已卡片化。全局脱表化：Demo01 + Demo02 共 18 子章 100% 完成）
> 项目：Demo02 (UE 5.7) @ `/Path/To/Your/UE_Project`

---

## 一、系统全景

### 1.1 这个系统做什么

用户在 UE5 中开发蓝图（26 个 Blueprint + WidgetBlueprint），每次修改后通过**一条 Python 命令**导出所有蓝图的完整节点拓扑（节点名、类型、引脚、连线、变量名、函数调用），然后对 Claude Code 说"更新UE日志"，系统自动执行：版本归档 ➔ 笔记+拓扑交叉比对 ➔ 结构化注入设计文档 ➔ Qwen 自动审阅。

### 1.2 核心价值

| 问题                                                   | 解决                                                                     |
| :----------------------------------------------------- | :----------------------------------------------------------------------- |
| UE5 Python API 只能读蓝图名称/路径，无法读内部节点图     | C++ 插件穿透 `UEdGraph` ➔ `UEdGraphNode` ➔ `UEdGraphPin` ➔ `LinkedTo` |
| 每次手动更新设计文档容易遗漏                             | 自动化 4 阶段流水线，JSON 拓扑为权威数据源                                 |
| Markdown 表格手动维护易出错                              | diff 验证 + Qwen 审阅双重保障                                            |
| 多人协作缺少统一命名/格式                                | 全链路英文命名 + 视觉排版协议                                             |

---

## 二、系统架构

### 2.1 文件地图

```
/Path/To/Your/UE_Project/
│
├── Demo02 5.7/                          ← UE5 项目本体
│   ├── Demo02.uproject                  ← 已声明 C++ Modules
│   ├── Content/MyMaps/BluePrint/        ← 蓝图资产
│   └── Source/Demo02/                   ← C++ 源码
│       ├── Demo02.Target.cs             ← Game 构建目标
│       ├── Demo02Editor.Target.cs       ← Editor 构建目标
│       └── Demo02/
│           ├── Demo02.Build.cs          ← 模块依赖
│           ├── Public/
│           │   ├── Demo02.h             ← 模块入口头文件
│           │   └── BlueprintTopologyExporter.h  ← 拓扑导出器头文件
│           └── Private/
│               ├── Demo02.cpp           ← IMPLEMENT_PRIMARY_GAME_MODULE
│               └── BlueprintTopologyExporter.cpp ← 拓扑导出器实现
│
├── tools/                               ← Python 工具脚本
│   ├── export_bp_metadata.py            ← UE5 内运行的导出脚本
│   ├── qwen_reviewer.py                 ← Qwen-Max 审阅脚本
│   ├── README_UE_Python.md              ← 用户操作指南
│   ├── GEMINI_CONTEXT_REPORT.md         ← Gemini 上下文报告
│   └── CPP_REFLECTION_DESIGN.md         ← C++ 反射设计文档
│
├── ue_blueprint_status.json             ← [自动生成] 蓝图拓扑 JSON（~1.2MB）
│
├── DemoMaterial_vX.X.X_YYYYMMDD_HH.md   ← [版本化] 设计日志（当前活跃版本）
├── DemoMaterial_VersionUpdating/        ← [归档] 历史版本
│   └── Old_DemoMateria_vX.X.X_时间戳.md
│
├── UENoteBook/                          ← 18 篇开发笔记
│   ├── INDEX.md                         ← 笔记结构化索引 + 蓝图覆盖矩阵
│   ├── 01、角色、坐标系与物理基石.md
│   ├── ...
│   └── 18、PlayerController的死亡UI...md
│
├── Review_Docs/                         ← Qwen/Gemini 审阅报告
│   └── NN_Qwen_Review_vX.X.X_YYYYMMDD_HH.md
│
└── Attachments/                         ← 本手册
    └── 工具链使用手册.md
```

### 2.2 组件拓扑

```
┌──────────────────────────────────────────────────────────┐
│                    用户操作层                              │
│                                                          │
│  [UE5编辑器] 改蓝图 → py "export_bp_metadata.py"         │
│  [Claude Code] 说 "更新UE日志"                            │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                    自动化流水线层                          │
│                                                          │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────┐  │
│  │ 阶段一       │   │ 阶段二        │   │ 阶段三         │  │
│  │ 询问确认     │──>│ 版本归档      │──>│ 排版注入       │  │
│  │ (安全挂起)   │   │ (Old_+New_)   │   │ (➔┈┈✨格式)   │  │
│  └─────────────┘   └──────────────┘   └───────┬───────┘  │
│                                                │          │
│                              ┌─────────────────┘          │
│                              ▼                            │
│  ┌─────────────┐   ┌──────────────┐                      │
│  │ 阶段四       │   │ 阶段五        │                      │
│  │ diff 验证    │──>│ Qwen 审阅     │──> 汇报摘要          │
│  │ (表格完整性) │   │ (API 自动调)  │                      │
│  └─────────────┘   └──────────────┘                      │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                    数据提取层                              │
│                                                          │
│  ┌──────────────────────────────────────┐                │
│  │ C++ BlueprintTopologyExporter        │                │
│  │ ├─ 遍历 UbergraphPages + FunctionGraphs               │
│  │ ├─ 13 种 K2Node_* Cast 链           │                │
│  │ ├─ TSet 连线去重                      │                │
│  │ └─ FJsonObject → TJsonWriter → JSON  │                │
│  └──────────────┬───────────────────────┘                │
│                 │ Python unreal.Class.dump_...()          │
│                 ▼                                         │
│  ┌──────────────────────────────────────┐                │
│  │ export_bp_metadata.py                │                │
│  │ ├─ AssetRegistry 扫描 /Game/         │                │
│  │ ├─ 过滤 Blueprint/WidgetBlueprint    │                │
│  │ ├─ 调 C++ 拓扑 → bp_entry["topology"]│               │
│  │ └─ 输出 1.2MB JSON                   │                │
│  └──────────────────────────────────────┘                │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                    审阅层                                  │
│                                                          │
│  ┌────────────────┐  ┌─────────────────┐                 │
│  │ Qwen-Max (自动) │  │ Gemini 3.5 Flash │                │
│  │ 审阅报告自动保存 │  │ (用户明确要求时)  │                │
│  └────────────────┘  └─────────────────┘                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 三、工具详解

### 3.1 export_bp_metadata.py — UE5 Python 导出脚本

**位置**：`tools/export_bp_metadata.py`（~370 行）

**运行方式**（必须在 UE5 编辑器内）：

```
Window → Output Log → 底部切换 Python → 输入：
py "/Path/To/Your/UE_Project/tools/export_bp_metadata.py"
```

**功能**：
1. 调用 `unreal.AssetRegistryHelpers.get_asset_registry()` 扫描 `/Game/` 下所有资产
2. 过滤 `Blueprint` / `WidgetBlueprint` / `AnimBlueprint` 类型
3. 排除 `/Engine/`、`/Game/StarterContent/`、`/Game/FirstPerson/` 等官方路径
4. 每个蓝图调用 C++ `unreal.BlueprintTopologyExporter.dump_blueprint_logic_to_json(bp)` 提取拓扑
5. 输出 `ue_blueprint_status.json`（26 蓝图 × 完整节点图 ≈ 1.2MB）

**输出 JSON 结构**：

```json
{
  "metadata": {
    "generated_at": "2026-06-21T...",
    "project": "Demo02",
    "total_blueprints": 26,
    "stats": { "by_type": {...}, "by_parent_class": {...} }
  },
  "blueprints": [
    {
      "name": "BP_Door01",
      "path": "/Game/MyMaps/BluePrint/BP_BallAdventure_Level1/BP_Door01",
      "type": "Blueprint",
      "parent_class": "Actor",
      "file_size_kb": 76.86,
      "last_modified": "2026-06-15T...",
      "topology": {
        "blueprint_name": "BP_Door01",
        "graphs": [
          {
            "graph_name": "EventGraph",
            "graph_type": "EventGraph",
            "nodes": [{
              "node_class": "K2Node_Timeline",
              "node_id": "K2Node_Timeline_0",
              "node_title": "Timeline",
              "function_name": "",
              "event_name": "ExecuteInteract",
              "variable_name": "",
              "pos_x": 512, "pos_y": 256,
              "pins": [{ "pin_id": "A1B2...", "pin_name": "exec", "direction": "Input", ... }]
            }],
            "connections": [{ "from_pin": "A1B2...", "to_pin": "C3D4...", ... }]
          }
        ]
      }
    }
  ]
}
```

### 3.2 BlueprintTopologyExporter — C++ 蓝图拓扑导出插件

**位置**：`Demo02 5.7/Source/Demo02/Public/Private/`

**核心函数**：`DumpBlueprintLogicToJson(UBlueprint* TargetBP) ➔ FString`

**穿透链路**：

```
UBlueprint
  ├─ UbergraphPages[]          ← 事件图 (EventGraph / BeginPlay / Tick)
  └─ FunctionGraphs[]          ← 自定义函数图 (BPI 实现 / 纯函数)
        │
        ▼
      UEdGraph                 ← 单个图表
        └─ Nodes[]             ← UEdGraphNode 数组
              ├─ GetClass() ➔ K2Node_CallFunction / K2Node_Event / ...
              ├─ GetNodeTitle() ➔ "Add Torque (In Radians)"
              └─ Pins[]       ← UEdGraphPin 数组
                    ├─ PinId ➔ FGuid 全局唯一标识
                    ├─ PinName ➔ "exec" / "then" / "ReturnValue"
                    ├─ Direction ➔ EGPD_Input / EGPD_Output
                    ├─ PinType ➔ FEdGraphPinType (exec/bool/float/struct...)
                    └─ LinkedTo[] ➔ TArray<UEdGraphPin*> ★ 连线目标
```

**13 种 K2Node Cast 链**：

| K2Node 子类 | 提取信息 | 成员/方法 |
|-------------|---------|----------|
| `K2Node_CallFunction` | 被调用函数名 | `FunctionReference.GetMemberName()` |
| `K2Node_Event` | 引擎原生事件 | `EventReference.GetMemberName()` |
| `K2Node_CustomEvent` | 自定义事件 | `CustomFunctionName` |
| `K2Node_VariableGet` | 读取变量名 | `VariableReference.GetMemberName()` |
| `K2Node_VariableSet` | 写入变量名 | `VariableReference.GetMemberName()` |
| `K2Node_FunctionEntry` | 函数入口 | `FunctionReference.GetMemberName()` |
| `K2Node_MacroInstance` | 宏名 | `GetMacroGraph()->GetName()` |
| `K2Node_Timeline` | 时间线名 | `TimelineName` |
| `K2Node_DynamicCast` | 转换目标类 | `TargetType->GetName()` |
| `K2Node_IfThenElse` | Branch 分支 | (无专属数据) |
| `K2Node_Knot` | 重路由节点 | (无专属数据) |
| `K2Node_Tunnel` | 图表出入口 | (无专属数据) |
| `K2Node_Self` | Self 引用 | (无专属数据) |

**Build.cs 模块依赖**：

```csharp
PublicDependencyModuleNames: Core, CoreUObject, Engine
PrivateDependencyModuleNames: UnrealEd, BlueprintGraph, KismetCompiler, Kismet,
                               Json, JsonUtilities, Slate, SlateCore
```

**UE 5.7 API 差异（已修复）**：

| 问题 | 修复 |
|------|------|
| `GetFunctionName()` 返回 `FName` 非 `FString` | 加 `.ToString()` |
| `IsNodePure()` 在 `UK2Node` 上不在 `UEdGraphNode` | `Cast<UK2Node>(Node)` |
| `IMPLEMENT_MODULE` 已弃用 | 改用 `IMPLEMENT_PRIMARY_GAME_MODULE` |

**Target.cs 固定配置**：

```csharp
DefaultBuildSettings = BuildSettingsVersion.V6;
IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_7;
bOverrideBuildEnvironment = true; // Installed Engine 不支持 Unique
```

### 3.3 ue-daily-logger Skill — 自动化流水线

**位置**：`~/.claude/skills\ue-daily-logger\SKILL.md`

**全局注册**：`/Path/To/Your/GlobalConfig/.claude\shared\common_workflows.md` §六

**触发词**："更新UE日志"、"更新demo版本素材"、"记录UE进度"

**五阶段流程**：

| 阶段 | 名称 | 做什么 |
| :--- | :--- | :----- |
| 一 | 询问确认 | 挂起，确认用户已运行导出脚本 + 已记录笔记 |
| 二 | 版本归档 | 旧版 ➔ `Old_DemoMateria_vX.X.X_时间戳.md`，新版 `DemoMaterial_v新版本号_时间戳.md` |
| 三 | 排版注入 | 全局扫描 ➔ 脱表化（轻量索引 + `####` 卡片） ➔ 遵守词汇禁忌和排版协议 |
| 四 | Qwen 审阅 | 自动调用 `qwen_reviewer.py`，报告存 `Review_Docs/` |
| 五 | 同步手册 | **自动**更新本手册（头部版本、排版协议、项目统计、实战示例） |

**阶段三词汇禁忌（核心红线）**：

绝对禁止在最终设计文档中出现：JSON、拓扑确认、脚本提取、C++ 导出、AssetRegistry、dump_blueprint_logic_to_json

**阶段三排版协议（v1.0.6 — 卡片化层级标题，对标 Knope / keepachangelog / Good Docs Project）**：

**⛔ 废除表格塞长文（核心架构决策）**
- 表格仅做**轻量索引**（`| 蓝图 | 父类 | 功能定位 |` 三列，每列不超过 15 字）
- 蓝图详细逻辑**独立为 `####` 标题块**，使用卡片式版本展开
- 对标 Knope 格式：简单项用 bullets，复杂项用 `####` 子标题

**`####` 卡片化区块模板**（每个核心蓝图一个独立标题块 — 对标 Stripe 卡片美学）：

```
#### 💠 BP_BlueprintName `(ParentClass)`
> **功能定位**：[一句话，15 字以内]
>
> <hr style="border:none;border-top:1px solid rgba(0,0,0,0.06);margin:24px 0">
>
> 🚀 **[最新 v1.0.x | YYYY-MM-DD HH:MM] — [核心标题]**
>
> **[执行链路]**
> - 链路要点1，节点名用反引号，➔ 串联流向
> - 链路要点2
>
> **[关键细节与设计哲学]**
> - 参数配置、防呆机制、物理规则、架构推演（完整保留）
> - 继续直到所有要点被覆盖
>
> 📦 <span style="color:gray">*[v过去版本号]  — [旧逻辑详述，灰色降级]*</span>
>
> <hr style="border:none;border-top:1px solid rgba(0,0,0,0.06);margin:24px 0">
>
> [原始纯文本记录 — 版本 0]
```

**排版美学叠代史**（R1 + R2 三方审阅融合）：
- `> ` 引用块包裹 = 左侧灰色竖线，卡片容器感（对标 Stripe）
- `<hr style="border:none;border-top:1px solid rgba(0,0,0,0.06);margin:24px 0">` = 1px 半透明分割线（Apple 无边界美学）
- `<span style="color:gray">` 灰化历史（对标 UE5 Legacy 降级）
- `<pre style="font-family:...monospace;...">` 包裹 ASCII 图（Stripe 等宽容器美学）
- `<ul style="line-height:1.8;letter-spacing:-0.01em">` 列表呼吸感（Apple 排版微调）
- 父类名用反引号 `` ` `` 包围 + 中英文"盘古之白" + 表格源码物理对齐 `|`

**卡片内部顺序**：🚀 最新 → 📦 历史（按版本倒序依次堆叠） → 原始文本（殿后）

**轻量概览表**（卡片上方快速索引，每列不超过 15 字）：
`| 蓝图 | 父类 | 功能定位 |`

**段落级排版**：
- 核心原理用 `> ` blockquote 包裹
- Emoji 锚点克制使用（仅导航）：📐数学 🔌通信 🛡️安全 ⚙️物理 📌铁律
- 所有 UE5 类名/函数名/节点名用反引号 `` ` `` 包围
- 长段落用 `- ` 列表拆分

**全局铁律**：
- `➔` 替代 `->`（箭头语义）
- `<span style="color:gray">` 灰化历史（对标 UE5 Legacy）
- `<hr style="border:none;border-top:1px solid rgba(0,0,0,0.06);margin:32px 0">` 弱化分割（Apple 1px 半透明美学 — Gemini R2 建议）
- `<pre style="font-family:'SF Mono',Monaco,monospace;...">` 包裹 ASCII 图（Stripe 等宽容器美学 — Gemini R2 建议）
- `<ul style="line-height:1.8;letter-spacing:-0.01em">` 列表呼吸感 + `<li style="margin-bottom:8px">`（Apple 排版微调 — Gemini R2 建议）
- ⚠️ 数据守恒：字数只增不减，通过拆分消灭文字墙

**参考来源**：
- [Knope Changelog Format](https://github.com/knope-dev/knope) — `####` 子标题处理复杂变更
- [The Good Docs Project](https://gitlab.com/tgdp/templates/-/blob/main/release-notes/template_release-notes.md) — 每 Feature 独立标题
- [keepachangelog.com](https://keepachangelog.com) — 6 标准类别 + SemVer
- [UE5.0 Release Notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5.0-release-notes) — 深度章节 + Legacy 灰化
- [GitScrum Release Notes Best Practices](https://docs.gitscrum.com/en/best-practices/release-notes-best-practices) — Per-category `###` + per-feature entries
- Apple Human Interface Guidelines — 1px 半透明分割线 + 32px 留白 + letter-spacing 微调
- Stripe 文档美学 — 等宽容器 + 圆角 + 浅灰背景

### 3.4 qwen_reviewer.py — Qwen-Max 自动审阅

**位置**：`tools/qwen_reviewer.py`

**调用方式**：

```bash
python qwen_reviewer.py <设计文档.md> [上下文报告.md]
```

**API 规范**：

| 参数 | 值 |
|------|-----|
| 端点 | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` |
| 模型 | `qwen-max` |
| 认证 | `Authorization: Bearer $QWEN_API_KEY` |
| 温度 | 0.3 |
| 最大 Token | 4096 |
| 输出路径 | `Review_Docs/NN_Qwen_Review_vX.X.X_YYYYMMDD_HH.md`（`NN_` 为递增序号，如 `07_`） |

**Gemini 审阅规则**：默认不自动触发，仅用户明确说"发给 Gemini"时才调用。API 规范：

| 参数 | 值 |
|------|-----|
| 端点 | `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent` |
| 认证 | `x-goog-api-key: $GEMINI_API_KEY` |
| 配置 | `thinkingBudget=0`, `maxOutputTokens=4096` |

---

## 四、完整操作流程

### 4.1 日常使用（每次改完蓝图后）

```
步骤 1：在 UE5 中改蓝图
        │
步骤 2：导出 JSON
        Window → Output Log → 切换 Python → 输入：
        py "/Path/To/Your/UE_Project/tools/export_bp_metadata.py"
        │  输出：26 蓝图已导出，1.2MB JSON 生成
        │
步骤 3：对 Claude Code 说
        "更新UE日志"
        │
        ▼
        [Skill 自动执行]
        ├─ 询问确认（你回复"确认"）
        ├─ 版本归档（Old_DemoMateria_v1.0.3 → DemoMaterial_v1.0.4）
        ├─ 排版注入（JSON + 笔记 → 表格追加）
        ├─ diff 验证（表格完整性检查）
        └─ Qwen 审阅（自动调 API，存 Review_Docs/）
```

### 4.2 C++ 插件编译（首次或修改 C++ 后）

```bash
# 关闭 UE5 编辑器
# 命令行执行：
E:\AAA.Program\UEStudy\UE_5.7\Engine\Build\BatchFiles\Build.bat ^
  Demo02Editor Win64 Development ^
  "/Path/To/Your/UE_Project/Demo02 5.7\Demo02.uproject"

# 编译成功后双击 Demo02.uproject 打开项目测试
```

### 4.3 命令速查表

| 操作 | 命令/触发词 |
|------|------------|
| 导出 JSON | `py "/Path/To/Your/UE_Project/tools/export_bp_metadata.py"`（在 UE5 Python 模式） |
| 更新日志 | "更新UE日志" |
| Qwen 审阅 | "发给 Qwen 审阅" |
| Gemini 审阅 | "发给 Gemini 审阅" |
| 记录到记忆 | "记录" |
| 编译 C++ | `Build.bat Demo02Editor Win64 Development "项目.uproject"` |
| 查看蓝图节点 | `unreal.BlueprintTopologyExporter.dump_blueprint_logic_to_json(bp)`（UE5 Python） |

---

## 五、文件命名规范

### 5.1 设计文档

| 文件 | 格式 | 示例 |
|------|------|------|
| 活跃版本 | `DemoMaterial_vX.X.X_YYYYMMDD_HH.md` | `DemoMaterial_v1.0.4_20260621_20.md` |
| 归档版本 | `Old_DemoMateria_vX.X.X_YYYYMMDD_HH.md` | `Old_DemoMateria_v1.0.3_20260621_20.md` |
| 归档目录 | `DemoMaterial_VersionUpdating/` | — |

### 5.2 审阅报告

| 文件 | 格式 |
|------|------|
| Qwen 审阅 | `NN_Qwen_Review_vX.X.X_YYYYMMDD_HH.md` |
| Gemini 审阅 | `NN_Gemini_Review_vX.X.X_YYYYMMDD_HH.md` |

### 5.3 蓝图资产命名前缀

| 前缀 | 类型 | 示例 |
|------|------|------|
| `BP_` | Blueprint Actor | `BP_Door01`, `BP_Crystal` |
| `BPI_` | Blueprint Interface | `BPI_Interact`, `BPI_ControllerCommands` |
| `WBP_` | Widget Blueprint | `WBP_DeathScreen`, `WBP_BallHealthBar` |
| `IA_` | Input Action | `IA_Jump`, `IA_Interact` |
| `IMC_` | Input Mapping Context | `IMC_Ball` |
| `E_` | Enum | `E_PlayerAttributes` |
| `SM_` | Static Mesh | `SM_Torch`, `SM_Floor_01` |
| `M_` | Material | `M_Crystal` |

---

## 六、数据流完整链路

```
┌─────────────────────────────────────────────────────────────────┐
│                        UE5 编辑器内部                             │
│                                                                 │
│  [蓝图资产]                                                      │
│     │                                                            │
│     ├── AssetRegistry.get_assets_by_path("/Game/")               │
│     │   └── 26 蓝图名称/路径/父类/文件时间                        │
│     │                                                            │
│     └── C++ BlueprintTopologyExporter::DumpBlueprintLogicToJson  │
│         └── UEdGraph ➔ Nodes[] ➔ Pins[] ➔ LinkedTo[] ➔ JSON    │
│                                                                 │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
         ue_blueprint_status.json  (1.2MB, 26 蓝图 x 完整节点拓扑)
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code 自动化层                          │
│                                                                 │
│  1. JSON 拓扑解析                                                │
│     └── 函数名/事件名/变量名/节点类名/连线关系                     │
│                                                                 │
│  2. UENoteBook 笔记读取                                          │
│     └── 18 篇笔记全量内容（设计意图 + 推导过程）                  │
│                                                                 │
│  3. 交叉比对                                                     │
│     └── JSON 数据 vs 设计文档现有内容 ➔ 差异清单                  │
│                                                                 │
│  4. 结构化注入                                                   │
│     └── 排版协议 (➔ ┈┈ ✨ 🎯 💡 📦)                             │
│                                                                 │
│  5. diff 验证                                                    │
│     └── 表格 | 管道符对齐性 + 零删减检查                          │
│                                                                 │
│  6. Qwen-Max API 审阅                                            │
│     └── 架构合理性 / 技术准确性 / 文档覆盖率 / 格式               │
│                                                                 │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
            DemoMaterial_vX.X.X_YYYYMMDD_HH.md
            Review_Docs/NN_Qwen_Review_vX.X.X_YYYYMMDD_HH.md
```

---

## 七、当前项目统计

| 指标 | 数值 |
|------|------|
| 蓝图总数 | 26（22 Blueprint + 4 WidgetBlueprint） |
| BPI 接口 | 5 套（Interact / Deliver / ControllerCommands / PlayerState / BallInteraction） |
| 最大蓝图 | `BP_BallAdventurePlayerPawn`（227 节点 / 175 连线 / 43 函数 / 10 事件 / 15 变量） |
| 开发笔记 | 18 篇（01-18，笔记覆盖 17/18，Note 17 为教育笔记） |
| 设计文档版本 | v1.0.6（`####` 卡片化区块 + `<hr>` 弱化分割 + `>` 容器包裹，实战验证通过 — Qwen 三判定全过） |
| JSON 大小 | ~1.2MB / 次导出 |
| 编译时间 | ~3-8 秒（增量编译 ~2 秒） |

---

## 八、维护与故障排查

| 问题 | 排查步骤 |
|------|---------|
| `ModuleNotFoundError: unreal` | 在外部终端运行了脚本。必须在 UE5 编辑器内执行。 |
| Python 下拉不显示 | 启用 `Python Editor Script Plugin`（Edit ➔ Plugins ➔ 搜索 Python） |
| 编译失败 `Cannot build with installed engine` | `BuildEnvironment.Unique` 改为 `bOverrideBuildEnvironment = true` |
| `AttributeError: no attribute 'DumpBlueprintLogicToJson'` | 类缺少 `DEMO02_API` 导出宏，或函数名需用蛇形 `dump_blueprint_logic_to_json` |
| Live Coding 阻止编译 | 关闭 UE5 编辑器后再编译 |
| Qwen API 调用失败 | 用 Python `requests` 库（非 PowerShell），检查 `QWEN_API_KEY` 环境变量 |
| 终端输出乱码 | PowerShell GBK 编码问题，文件保存的 UTF-8 内容正确，`chcp 65001` 可临时切换 |
| Consolidation 失败 | agentmemory LLM API 免费额度耗尽，手动 `memory_save` 不受影响 |

---

## 九、排版协议版本进化史

| 版本 | 核心升级 | 对标规范 |
|------|---------|---------|
| v1.0.0 | 原始 3 列表格，几百字塞进单元格 | — |
| v1.0.4 | ➔ 箭头 + `>` blockquote + ┈┈ 粗分割线 | — |
| v1.0.5 | 🆕/📦 版本卡片 + `<ul><li>` + `<span>` 灰化 | keepachangelog + UE5 RelNotes |
| v1.0.6 | ⛔ 废除表格塞长文 → `####` 卡片化区块 + 轻量索引表 | Knope + Good Docs Project |
| v1.0.7 | `>` 容器包裹卡片 + 盘古之白 + 源码物理对齐 `\|` | Stripe + Apple HIG |
| v1.0.8 | `<hr>` 1px 半透明分割 + `<pre>` ASCII 容器 + `<ul>` 呼吸感 | Apple 排版微调 + Stripe 代码块美学 |
| v1.0.9 | Apple Badge 胶囊父类标识 + Emoji 克制（≤2/卡）+ 场景表卡片化 | Stripe API 文档 + Epic 严肃学术风格 |

**v1.0.9 新增 — Apple Badge 父类胶囊标识**（Gemini R3 建议）：

```html
<!-- Pawn 用蓝色 -->
<span style="font-size:12px;background-color:rgba(59,130,246,0.1);color:#3b82f6;padding:2px 8px;border-radius:12px;margin-left:8px;font-weight:600">Pawn</span>

<!-- Interface 用绿色 -->
<span style="...color:#10b981;background-color:rgba(16,185,129,0.1)...">Interface</span>

<!-- UserWidget 用紫色 -->
<span style="...color:#8b5cf6;background-color:rgba(139,92,246,0.1)...">UserWidget</span>

<!-- Actor 用蓝色 -->
<span style="...color:#3b82f6;background-color:rgba(59,130,246,0.1)...">Actor</span>
```

## 十、v1.0.6 实战验证 — 交互机制章节卡片示例

以下为 `DemoMaterial_v1.0.6_20260621_20.md` 中交互机制的实际渲染片段：

```markdown
| 蓝图 | 父类 | 功能定位 |          ← 轻量索引表，每列 ≤15 字
| :--- | :--- | :------- |

#### 💠 BP_Crystal `(Actor)`
> **功能定位**：可收集水晶 — VLerp 吸收动画 + Timeline 防抖
>
> <hr style="border:none;border-top:1px solid rgba(0,0,0,0.06);margin:24px 0">
>
> 🚀 [最新 v1.0.6 | ...] — VLerp 吸收动画完整节点链
>
> [执行链路]
> - Timeline ➔ VLerp ➔ K2_SetActorLocation（逐帧移动）
> - SetActorScale3D ➔ SetCollisionEnabled(NoCollision)（防抖）
>
> [关键细节与设计哲学]
> - Timeline 防抖原理：首帧关闭碰撞，防鬼畜抽搐
> - VLerp 起点缓存 CrystalLocation，终点 PlayerPawn 实时位置
>
> 📦 [v1.0.3] — 旧版灰化溯源
>
> <hr style="border:none;border-top:1px solid rgba(0,0,0,0.06);margin:24px 0">
>
> 原始纯文本 — 版本 0

#### 💠 BP_Vehicle_Car01 `(Pawn)`
> ...
```

> **Qwen 审阅结论**：交互机制表 → 轻量索引 + `####` 卡片 ✅ / `>` 容器 + `<hr>` 弱化分割 ✅ / 内容完整零删减 ✅
