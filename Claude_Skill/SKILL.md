# 技能名称: UE 日志自动更新流水线 (ue-daily-logger)

## 触发条件
当用户在对话中提到"更新UE日志"、"更新demo版本素材"等字眼时，立即触发此技能。

## 交互流程（绝对遵守顺序）

### 阶段一：前置安全检查（询问并挂起）
1. 严禁立即修改文件。
2. 询问用户："检测到更新请求。请确认：1. 已提取最新 JSON？2. 已记录 UENoteBook？ 回复【确认】开始执行。"挂起等待。

### 阶段二：严格命名与版本归档（核心规范）
工作区路径设为：`/Path/To/Your/UE_Project`
1. **获取信息**：获取当前系统时间（格式 `YYYYMMDD_HH`）。找到当前最新日志，提取其版本号和旧时间戳，计算新版本号。
2. **创建归档与审阅目录**：
   - 回溯文件夹：`/Path/To/Your/UE_Project/DemoMaterial_VersionUpdating`
   - 审阅文件夹：`/Path/To/Your/UE_Project/Review_Docs`
3. **物理备份（严格命名）**：复制原日志到 `DemoMaterial_VersionUpdating`，头部写入 `> 备份文件`，重命名为 `Old_DemoMaterial_v旧版本号_旧时间戳.md`。
4. **激活新版（严格命名）**：原文件重命名为 `DemoMaterial_v新版本号_当前时间戳.md`。

### 阶段三：卡片化层级标题注入 — 废除表格塞长文，对标 Knope / keepachangelog / Good Docs Project

#### 1. 写作原则
- 以**资深引擎开发者**的第一人称视角记录，绝不暴露"JSON、拓扑、脚本、C++导出"等自动化工具痕迹。
- 每条记录回答"对项目架构有什么影响"——而非"我用了什么工具提取了数据"。
- 新版本内容在卡片的 C 位，旧版本用 `<span style="color:gray">` 灰色降级为"归档参考"。

#### 2. ⚠️ 绝对数据守恒定律
- **禁止删减、缩写、概括、总结。**
- 笔记中的每个节点名（`VLerp`, `Timeline`）、每个参数值（0.033s）、每步数学推导——**100% 一字不落保留**。
- 破解"文字墙"的正道：用 `- ` 列表拆分 + `<br>` 呼吸间距 + 灰色历史降级——**字数只增不减**。

#### 3. ⛔ 废除表格塞长文（核心架构决策）

**严禁将上百字的版本迭代、树形逻辑链、灰度历史塞进 Markdown 表格单元格**。这会导致单元格被无限拉长、读者丢失表头视野、`|` 管道符解析风险极高。

**正确做法**：
- **表格仅保留轻量概览**：`| 蓝图 | 父类 | 功能定位 |` 三列，每列不超过 15 字。
- **蓝图详细逻辑独立为 `####` 卡片区块**：每个核心蓝图一个 `####` 标题块，内嵌完整的版本卡片 + 历史溯源。
- 对标 Knope 格式——简单项用 bullets，复杂项用 `####` 子标题 + 正文。
- 对标 Good Docs Project——每个 Feature 自己的标题 + 描述。

#### 4. `####` 卡片化区块模板（每个核心蓝图一个独立标题块）

**【布局规则】**：
- 使用 `####` 作为蓝图级别标题（如一粒宝石的标题）。
- 卡片主体用 `> ` 引用块包裹，生成左侧灰色竖线，形成"容器封装感"（对标 Stripe 卡片美学 — Gemini 建议）。
- 新版本卡片紧贴标题下方，是读者的第一视觉落点。
- 历史版本依次堆叠在下方，`<span style="color:gray">` 灰色弱化。
- 卡片底部保留该蓝图的原始纯文本记录（版本 0，殿后）。

**【卡片模板 — 严格原封不动使用】**：

```markdown
#### 💠 BP_BlueprintName `(ParentClass)`
> **功能定位**：[一句话描述，15 字以内]
>
> ────────────────────────────────────────
>
> 🚀 **[最新 v新版本号 | YYYY-MM-DD HH:MM] — [核心标题]**
>
> **[执行链路]**
> - [一字不减地提取笔记连线逻辑，UE5 节点名用反引号包围，流向用 ➔ 串联]
> - [继续拆分，直到链路完整]
>
> **[关键细节与设计哲学]**
> - [一字不减地提取所有参数配置、防呆机制、物理规则、架构推演]
> - [多长都写，不缩写，直到所有要点被覆盖]
>
> 📦 <span style="color:gray">*[v旧版本号 — 旧版标题]*  \> *[无损详述旧逻辑，灰色降级]*</span>
>
> ────────────────────────────────────────
>
> [原始纯文本记录 — 版本 0]
```

**排版美学要点**（Gemini + Qwen 融合建议）：
- `> ` 引用块包裹 = 左侧灰色竖线，卡片容器感（对标 Stripe 卡片设计）
- 父类名用反引号 `` ` `` 包围（如 `` `Actor` ``）
- 中英文之间保留半角空格（"盘古之白"，如 `UE5 节点名` 而非 `UE5节点名`）
- `<span style="color:gray">` 灰化历史（对标 UE5 Legacy 降级，保留不删除）
- 表格源码物理对齐管道符 `|`（"连源码都美观"原则）

**卡片内部顺序**（从上到下）：🚀 最新卡片 ➔ 📦 历史版本卡片（按版本倒序依次堆叠） ➔ 原始纯文本（殿后）

#### 5. 轻量概览表格（仅在卡片上方作为快速索引）

每个蓝图大类（如"交互机制"）前保留一个**极简概览表**：

```markdown
| 蓝图 | 父类 | 功能定位 |
|------|------|----------|
| BP_Crystal | Actor | 可收集水晶 — 拾取吸收动画 |
| BP_Door01 | Actor | 可开关门 — Timeline 旋转 |
```

**表格铁律**：每列不超过 15 字！详细逻辑全部在下方 `####` 卡片中展开。

#### 6. 顶级排版美学注入（R2 三方审阅融合 — Apple / Stripe 级细节）

**6a. 分隔线弱化（Gemini + Qwen 一致建议）**
- **禁止**使用原生 `---` 或 `────────` 粗重分割线。
- **统一使用**：`<hr style="border: none; border-top: 1px solid rgba(0,0,0,0.06); margin: 32px 0;">`
  - 1 像素半透明线 + 上下 32px 留白 = Apple 级"无边界呼吸感"。

**6b. ASCII 架构图容器化（Gemini 建议）**
- 所有 `┌──┐` ASCII 框图必须用 `<pre>` 标签包裹，声明等宽字体：
  ```html
  <pre style="font-family: 'SF Mono', Monaco, Consolas, monospace; font-size: 12px; line-height: 1.4; background: #f8f9fa; border-radius: 8px; padding: 16px; overflow-x: auto;">
  [原 ASCII 图]
  </pre>
  ```

**6c. 列表呼吸感（Gemini 建议 — Apple 排版细节）**
- 密集列表项（超过 3 条）用 `<ul style="line-height: 1.8; letter-spacing: -0.01em;">` 包裹。
- 每个 `<li>` 加 `style="margin-bottom: 8px;"` 撑开纵向间距。
- `letter-spacing: -0.01em` 是 Apple 经典排版微调，使中英文混排更紧凑优雅。

**6d. 段落级排版（对标 UE5 RelNotes 深度章节）**
- 核心原理段落用 `> ` 引用框包裹，形成"深度阅读区"。
- Emoji 锚点**极度克制**使用：每张卡片不超过 2 个 Emoji（🚀 最新版本标记 + 💡 设计哲学标记）——对标 Epic 官方 Release Notes 的严肃学术风格，拒绝自媒体感。
- 父类名用 Apple Badge 胶囊样式：`<span style="font-size:12px;background-color:rgba(59,130,246,0.1);color:#3b82f6;padding:2px 8px;border-radius:12px;margin-left:8px;font-weight:600">Pawn</span>`（Interface 用 `#10b981` 绿色，UserWidget 用 `#8b5cf6` 紫色，Actor 用 `#3b82f6` 蓝色）。
- 所有 UE5 类名/函数名/节点名用反引号 `` ` `` 包围。
- 长段落必须用 `- ` 无序列表拆分，每行不超过约 120 字符。

#### 7. 全局排版铁律
- `➔` 替代 `->`（箭头语义）。
- `<br>` 单换行撑开呼吸区（对标 Apple RelNotes 留白）。
- `- ` 列表替代长段落（对标 Node.js Notable Changes）。
- `<span style="color:gray">` 灰化历史（对标 UE5 Legacy 降级）。
- `<hr style="...">` 弱化分割线（对标 Apple 1px 半透明美学）。
- `<pre>` + 等宽字体包裹 ASCII 图（对标 Stripe 代码块美学）。
- `<ul style="line-height:1.8">` 列表呼吸感（对标 Apple 排版微调）。
- 表格仅做索引，蓝图详细逻辑独立为 `####` 卡片。
- **Apple Badge 短码**：父类名统一用 `{TypeName}` 短码替代原始 HTML（如 `{Pawn}`、`{Actor}`、`{Interface}`），文档顶部附短码→色值映射表。颜色约定：蓝 `#3b82f6`=Actor/Pawn/Controller/GameMode，绿 `#10b981`=Interface，紫 `#8b5cf6`=UserWidget，青 `#06b6d4`=Input Action/IMC，琥珀 `#f59e0b`=Enum。
1. 自动调用 `/Path/To/Your/UE_Project/tools\qwen_reviewer.py`。
2. 将 `v新版本号` 和 `当前时间戳` 传给 Python 脚本。
3. 验证报告生成在 `/Path/To/Your/UE_Project/Review_Docs\NN_Qwen_Review_v新版本号_当前时间戳.md`（`NN_` 为递增序号，扫描目录最大编号 +1，确保最新报告排在最末）。完成后输出执行摘要。

### 阶段五：强制同步使用手册（每次更新后自动执行）
1. **自动更新**：日志注入 + Qwen 审阅完成后，**必须自动**同步更新 `/Path/To/Your/UE_Project/Attachments\日志更新工作流使用手册.md`。
2. 更新内容：头部版本号/时间戳、排版协议版本、设计文档版本号、新增实战验证示例、项目统计数据。
3. **严禁跳过此步骤**——这是确保 Gemini 审阅时拿到的是最新完整上下文的关键。
