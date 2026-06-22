# Obsidian 协同工作流集成指南

> **适用版本**: Obsidian 1.x + | **依赖插件**: RealClaudian (Community Plugin)  
> **协同对象**: Claude Code + UE5 蓝图日志自动化工具链

---

## 一、核心理念

本工具链假设你的开发笔记存储在 Obsidian 仓库中，并通过 RealClaudian 插件与 Claude Code Agent 实现双向联动：

```
UE5 编辑器 (改蓝图) → Python 导出 JSON → Obsidian 笔记记录
                                            ↓
            Claude Code Agent ← RealClaudian 会话同步 ← Obsidian 仓库
                   ↓
            自动化流水线: 版本归档 → 拓扑注入 → 排版 → AI 审阅
                   ↓
            最终设计文档 + 审阅报告 写入 Obsidian 仓库
```

---

## 二、Obsidian 仓库目录结构规范

建议在你的 UE 项目根目录下初始化 Obsidian Vault，采用以下结构：

```
Your_UE_Project/                      ← Obsidian Vault 根目录
├── .obsidian/                         ← Obsidian 配置（自动生成）
│   ├── plugins/realclaudian/          ← RealClaudian 插件
│   └── workspace.json
├── UENoteBook/                        ← 📒 UE 开发笔记（核心知识库）
│   ├── INDEX.md                       ← 笔记索引 + 蓝图覆盖矩阵
│   ├── 01、角色、坐标系与物理基石.md
│   ├── 02、Gameplay 框架与数据解耦.md
│   ├── ...                            ← 按课程/模块编号
│   └── NN、某某主题.md
├── Review_Docs/                       ← 🤖 AI 审阅报告（自动生成）
│   ├── NN_Qwen_Review_vX.X.X_时间戳.md
│   └── NN_Gemini_Review_vX.X.X_时间戳.md
├── Attachments/                       ← 📎 附件（工具手册、目录清单）
├── DemoMaterial_vX.X.X_时间戳.md      ← 📋 当前活跃版本设计文档
└── DemoMaterial_VersionUpdating/      ← 🗄️ 历史版本归档
```

### 目录职责

| 目录 | 谁写入 | 写入时机 | 内容 |
|------|--------|----------|------|
| `UENoteBook/` | **你**（手动） | 每次学习/开发后 | 知识点、推导过程、蓝图连线思路 |
| `Review_Docs/` | **Claude Code Agent**（自动） | 每次"更新UE日志"后 | AI 审阅报告 |
| `Attachments/` | **你** + Agent | 按需 | 工具手册、目录清单、参考文档 |
| `DemoMaterial_vX.X.X_*.md` | **Claude Code Agent**（自动） | 每次"更新UE日志"后 | 结构化的蓝图设计清单 |
| `DemoMaterial_VersionUpdating/` | **Claude Code Agent**（自动） | 每次版本迭代前 | 旧版本文档归档 |

---

## 三、RealClaudian 插件配置

### 3.1 安装

1. Obsidian → Settings → Community Plugins → 搜索 `RealClaudian`
2. 安装并启用
3. 在插件设置中配置 Claude Code 的连接参数

### 3.2 会话管理

RealClaudian 会在 `.claudian/sessions/` 下保存每次 Claude Code 对话的元数据（会话 ID、时间戳、摘要）。这些会话记录帮助你：

- **回溯上下文**：查看某次蓝图修改对应哪次 Agent 会话
- **增量笔记**：结合会话摘要，在 Obsidian 中补充开发笔记
- **审计追踪**：了解设计文档的每次变更来源

### 3.3 工作流联动

```
你 在 UE5 中改了 BP_Crystal 蓝图
  │
你 在 Obsidian 写了笔记: "BP_Crystal 新增 VLerp 吸收动画"
  │
你 在 UE5 中运行 py "export_bp_metadata.py"
  │
你 对 Claude Code 说: "更新UE日志"
  │
Claude Code Agent:
  ├─ 读取 AssessStatus_Json/ue_blueprint_status_<项目名>.json (最新蓝图拓扑)
  ├─ 读取 UENoteBook/ 中相关笔记 (理解设计意图)
  ├─ 交叉比对 → 注入 DemoMaterial_v1.0.7.md
  ├─ 调用 Qwen 审阅 → Review_Docs/NN_Qwen_Review_v1.0.7.md
  └─ 同步更新 Attachments/日志更新工作流使用手册.md
  │
RealClaudian:
  └─ 自动保存本次会话元数据到 .claudian/sessions/
```

---

## 四、笔记编写规范

### 4.1 命名规范

```
UENoteBook/
├── INDEX.md                           ← 必须：目录索引
├── 01、主题名.md                       ← 编号从 01 开始，两位数字
├── 02、主题名.md
└── ...
```

### 4.2 笔记模板

每篇笔记建议包含以下结构：

```markdown
# 笔记标题

> 日期: YYYY-MM-DD | 关联关卡: XXXMap | 关联蓝图: BP_XXX

## 一、核心概念
[用通俗语言解释今天学到的核心概念]

## 二、蓝图实现
[蓝图连线逻辑、节点选择原因、引脚配置]

### 蓝图节点拆解
| 节点名 | 类型 | 输入引脚 | 输出引脚 | 作用 |
|--------|------|---------|---------|------|
| XXX | K2Node_XXX | exec: ... | then: ... | ... |

## 三、C++ 底层映射 (可选)
[如果有对应的 C++ 概念，记录在这里]

## 四、踩坑记录
[遇到的问题和解决方案]
```

### 4.3 INDEX.md 规范

`INDEX.md` 是 Agent 了解全局笔记结构的关键入口，必须包含：

- **笔记列表**：每篇笔记的文件名 + 一句话主题
- **蓝图覆盖矩阵**：哪些笔记涉及哪些蓝图（Agent 据此判断要读取哪些笔记）
- **知识模块标签**：碰撞检测、UI通信、AI行为树 等

---

## 五、最佳实践

### 5.1 笔记节奏

- **每改完一个功能**，立即在 UE5 中导出 JSON
- **对 Claude Code 说"更新UE日志"前**，先在 Obsidian 写好对应笔记
- Agent 会交叉比对 JSON 拓扑和你的笔记，确保设计文档有"设计意图"而不仅是"节点列表"

### 5.2 笔记粒度

- 太细：每个蓝图节点写一篇 → 笔记爆炸
- 太粗：整个项目写一篇 → 没有索引价值
- **推荐**：每个核心玩法系统一篇（如"小球移动力学"、"门交互系统"、"死亡复活流水线"）

### 5.3 不要手动修改设计文档

`DemoMaterial_vX.X.X_*.md` 是 Agent 自动生成的"单一事实来源"，**禁止手动编辑**。你应该通过以下方式影响它：

1. 修改蓝图（在 UE5 中）
2. 导出 JSON（运行 Python 脚本）
3. 更新笔记（在 Obsidian 中）
4. 触发流水线（对 Claude Code 说"更新UE日志"）

---

## 六、常见问题

| 问题 | 解答 |
|------|------|
| Q: 笔记写在 Obsidian 里，Agent 怎么读到？ | Agent 通过文件系统直接读取 `UENoteBook/` 目录，无需额外配置 |
| Q: RealClaudian 会同步我的笔记到云端吗？ | 不会。它只管理 Claude Code 的会话元数据，你的笔记始终在本地 |
| Q: 可以不用 Obsidian，用其他笔记软件吗？ | 可以。只要笔记存放在 `UENoteBook/` 目录下，Agent 就能读取。Obsidian 只是推荐的 Markdown 编辑器 |
| Q: 笔记是中文还是英文？ | 都可以。Agent 支持中英文混合内容。建议技术术语保留英文 |
