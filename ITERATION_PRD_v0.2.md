# OfferPilot 迭代 PRD v0.2：投递池与简历池管理能力增强

> **文档版本**: v1.0
> **创建日期**: 2026-05-21
> **状态**: 待开发
> **关联文档**: PRODUCT_SPEC.md, README.md

---

## 1. 迭代背景

### 1.1 当前版本（v0.1 / MVP）状态

OfferPilot v0.1 已完成以下核心能力：

- **岗位管理**：JD 录入 + 规则/AI 双模式解析 + 岗位列表
- **简历管理**：多版本简历创建，关键词和项目亮点维护
- **投递追踪**：创建投递记录，9 状态看板，状态快速切换
- **AI 匹配分析**：规则/AI 双模式岗位-简历匹配评分
- **面试准备**：规则/AI 双模式面试准备包生成
- **求职周报**：规则/AI 双模式周报 + Markdown 导出
- **数据看板**：实时指标卡片 + AI 行动建议

### 1.2 当前版本的能力缺口

在种子用户（同学/校友）试用后，反馈集中在以下基础能力缺失：

| 问题 | 严重程度 | 影响 |
|------|---------|------|
| **投递记录无法编辑** | 高 | 状态选错后无法修正其他字段，只能删了重建 |
| **投递记录无法删除** | 高 | 测试数据、重复数据无法清理，数据越来越脏 |
| **缺少投递链接字段** | 中 | 每次查看进度要切回招聘网站，找不到原始投递页面 |
| **简历无法编辑** | 高 | 关键词/亮点需要修改时必须删除重建，数据丢失 |
| **简历无法删除** | 中 | 废弃的简历版本无法清理 |
| **简历无法预览** | 中 | 上传后看不到内容，不确定解析是否正确 |
| **状态定义不够细** | 中 | 缺少"简历评估"等中间状态，与实际求职流程不匹配 |
| **英文导航栏** | 低 | 中文用户对英文侧边栏名称理解有障碍 |

### 1.3 本轮迭代定位

**本轮定位为"基础能力补强"**，不新增 AI 功能，聚焦于让求职管理的核心闭环（投递池 + 简历池）完整可用。这是从"能用"到"好用"的关键一步。

---

## 2. 本次迭代目标

1. **投递池管理完整化**：支持编辑、删除投递记录，新增投递链接字段，细化投递状态
2. **简历池管理完整化**：支持编辑、删除、预览简历版本
3. **中文导航栏**：侧边栏导航和页面标题全面中文化
4. **数据安全**：删除操作有二次确认，简历删除有引用检查

---

## 3. 用户痛点

| 痛点 | 场景 | 当前状态 | 目标状态 |
|------|------|---------|---------|
| 投递后想补充信息 | 投递后收到内推链接，想补上投递链接 | 无法编辑，只能备注里记 | 编辑表单修改所有字段 |
| 测试数据堆积 | 开发时创建了大量测试投递记录 | 无法删除 | 二次确认后安全删除 |
| 状态不匹配实际流程 | 投了之后先"简历评估"才到"笔试"，当前没有这个状态 | 只有 9 个状态 | 细化为 9 个新状态 |
| 简历需要微调 | 面完一家发现简历少了某个关键词，想补上 | 删了重建 | 编辑表单修改 |
| 想确认上传的文件对不对 | 上传了 PDF 简历，不确定内容是否解析成功 | 看不到 | 预览/下载文件 |
| 英文导航找不到功能 | Dashboard、Job Tracker 需要想一想才明白 | 英文导航 | 中文导航 |

---

## 4. 功能需求详情

### 4.1 投递记录编辑（Application Edit）

**入口**：投递看板中每条记录的右上角增加"编辑"按钮（铅笔图标），或在卡片上增加编辑入口。

**编辑表单**：弹出 expander 或 dialog，包含以下可修改字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| 关联岗位 | selectbox（不可改） | 展示当前 job.company - job.title，只读 |
| 关联简历 | selectbox（不可改） | 展示当前 resume.version_name，只读 |
| 投递状态 | selectbox | 从新的 APPLICATION_STATUSES_V2 中选择 |
| 投递日期 | date_input | 可修改 |
| 投递渠道 | text_input | 当前通过 notes 字段存储，无独立字段；若有 channel 字段则编辑 |
| 投递链接 | text_input（**新增**） | application_url，录入招聘官网/Boss/内推链接 |
| 备注 | text_area | 可修改 |
| 终止原因 | text_area（**条件显示**） | 仅当状态为"终止"时显示 |

**注意**：当前 `Application` 数据模型中 `channel` 字段已存在但创建表单中未使用（投递渠道实际记录在备注中）。编辑时应展示 channel 字段。

**提交后**：调用 `store.update_application()` 保存，看板即时刷新。

### 4.2 投递记录删除（Application Delete）

**入口**：编辑区域底部放置"删除投递记录"按钮（红色/警告样式）。

**交互流程**：
1. 用户点击"删除投递记录"
2. 弹出二次确认：`st.warning` 或 checkbox 确认，显示被删除记录的摘要（公司、岗位、状态）
3. 用户确认后执行删除
4. 删除成功提示，看板刷新

**安全约束**：
- 只删除 Application 记录本身
- **不删除**关联的 Job 岗位
- **不删除**关联的 ResumeVersion 简历
- **不删除**关联的 InterviewRecord 面试记录（如果已存在）；在 PRD 中标注为后续需要处理的遗留数据清理问题

**实现位置**：`core/data_store.py` 新增 `delete_application(app_id: str)` 方法。

### 4.3 投递链接字段（application_url）

**数据模型变更**：`Application` dataclass 新增字段：

```python
application_url: str = ""  # 投递链接（招聘官网/Boss/内推链接等）
```

**页面展示**：在看板卡片中，如果有 application_url，展示为可点击的链接图标或短链接文本。

**编辑支持**：在创建投递记录的表单和编辑表单中均增加该字段。

### 4.4 投递状态枚举重构

**当前状态**（v0.1，将废弃）：

```python
APPLICATION_STATUSES = [
    "待投递", "已投递", "笔试 / 测评",
    "一面", "二面", "HR 面",
    "Offer", "拒绝", "放弃",
]
```

**新状态**（v0.2）：

```python
APPLICATION_STATUSES_V2 = [
    "已投递",     # 已提交申请，等待反馈
    "简历评估",   # HR 正在评估简历（部分公司有明确通知）
    "笔试/测评",  # 收到笔试或在线测评
    "一面",       # 技术一面 / 群面
    "二面",       # 技术二面 / 经理面
    "HR面",       # HR 面试
    "Offer",      # 收到录用通知
    "终止",       # 流程终止（被拒/主动终止），需要填写终止原因
    "放弃",       # 用户自己放弃（主动放弃，区别于被动终止）
]
```

**变更对照**：

| v0.1 状态 | v0.2 状态 | 变更说明 |
|-----------|-----------|---------|
| 待投递 | — | 移除，此状态由"未创建 Application"来表达；用户在 Match Lab 分析完决定投递时才创建 Application |
| 已投递 | 已投递 | 保留 |
| — | 简历评估 | **新增**，部分大厂有明确的简历评估阶段通知 |
| 笔试 / 测评 | 笔试/测评 | 重命名（去掉空格） |
| 一面 | 一面 | 保留 |
| 二面 | 二面 | 保留 |
| HR 面 | HR面 | 重命名（去掉空格） |
| Offer | Offer | 保留 |
| 拒绝 | 终止 | 语义扩大：不只包含被拒，也包含流程中其他原因的终止 |
| 放弃 | 放弃 | 保留 |
| — | 终止原因 | **新增**：termination_reason 字段，状态为"终止"时必填 |

**迁移策略**：
- `APPLICATION_STATUSES` 保留但标记为 deprecated
- 新增 `APPLICATION_STATUSES_V2` 作为主枚举
- `action_planner.py` 需要更新状态匹配逻辑
- `weekly_review.py` 需要更新状态统计逻辑
- `pages/1_Dashboard.py` 需要更新状态过滤逻辑
- `pages/5_Interview_Prep.py` 需要更新面试状态判断
- `pages/6_Weekly_Review.py` 需要更新漏斗图状态列表
- 已有数据**不做自动迁移**（MVP 阶段数据量小，用户手动调整即可；如需迁移，可在 app 启动时做一次映射）
- 提供迁移映射表供手动修复参考

### 4.5 简历编辑（Resume Edit）

**入口**：每个简历卡片底部增加"编辑"按钮。

**编辑表单**：与创建表单基本一致，但预填现有值：

| 字段 | 类型 | 可编辑 |
|------|------|--------|
| 简历版本名称 | text_input | 是 |
| 适用岗位方向 | selectbox | 是 |
| 核心关键词 | text_input（逗号分隔） | 是 |
| 项目亮点 | text_area（每行一个） | 是 |
| 简历文件 | file_uploader | 是（可选，不上传新文件则保留旧文件） |

**提交后**：调用 `store.update_resume()` 保存，卡片即时刷新。

### 4.6 简历删除（Resume Delete）

**入口**：编辑区域底部放置"删除简历"按钮。

**交互流程**：
1. 用户点击"删除简历"
2. **引用检查**：检查该 resume_id 是否被任何 Application 引用
3. 如果存在引用 → **阻止删除**，提示"该简历被 X 条投递记录引用，无法删除。如需删除请先删除相关投递记录。"
4. 如果无引用 → 弹出二次确认
5. 确认后执行删除

**实现位置**：`core/data_store.py` 新增：

```python
def delete_resume(self, resume_id: str):
    """删除简历版本。调用前请先检查引用。"""
    # 删除文件系统中的简历文件
    # 从 self.resumes 中移除
    # 保存

def get_resume_application_count(self, resume_id: str) -> int:
    """返回引用该简历的 Application 数量。"""
```

**安全约束**：
- 被引用的简历**不允许直接删除**
- 删除时同时清理 `data/resumes/` 下的上传文件（如果存在）
- 不删除关联的 MatchResult（历史匹配记录保留，但会变成孤儿数据；后续迭代可做清理）

### 4.7 简历预览（Resume Preview）

**入口**：每个简历卡片上增加"预览"按钮。

**预览策略（按文件类型）**：

| 文件类型 | 预览方式 | 实现方案 |
|---------|---------|---------|
| **txt** | 直接展示文本内容 | `open(file_path).read()` → `st.code()` 或 `st.text_area()` |
| **pdf** | 尝试嵌入预览 | 使用 `PyPDF2` 或 `pdfplumber` 提取文本 → `st.text_area()` 展示；如果已安装 `pymupdf` 则优先使用。如文本提取失败，回退到文件下载 |
| **docx** | 提取文本预览 | 使用 `python-docx`（如已安装）提取段落文本 → `st.text_area()` 展示；如未安装依赖，提示安装或提供文件下载 |
| **无文件** | 提示未上传 | 显示"该简历未上传文件" |

**实现位置**：新增 `services/resume_viewer.py`，提供：

```python
def preview_resume_text(file_path: str) -> str | None:
    """提取简历文件的文本内容，用于预览。返回 None 表示无法提取。"""

def get_file_extension(file_path: str) -> str:
    """返回文件扩展名（小写）。"""
```

**依赖变更**（`requirements.txt`）：
- `PyPDF2>=3.0` 或 `pdfplumber>=0.10` — PDF 文本提取
- `python-docx>=1.0` — DOCX 文本提取（如果尚未依赖）

**页面交互**：
- 预览以 `st.expander` 或 modal 方式展开，不影响卡片列表布局
- 如果文本提取成功 → 展示文本内容
- 如果文本提取失败 → 提供文件路径和 `st.download_button` 下载原文件

---

## 5. 数据模型变更

### 5.1 Application 模型变更

```python
# core/models.py

@dataclass
class Application:
    """A job application record linking a Job to a ResumeVersion."""
    id: str
    job_id: str
    resume_id: str
    applied_date: Optional[datetime] = None
    channel: str = ""              # 投递渠道：内推 / 官网 / BOSS直聘
    application_url: str = ""      # [NEW] 投递链接
    current_stage: str = ""
    status: str = ""               # 使用 APPLICATION_STATUSES_V2
    termination_reason: str = ""   # [NEW] 终止原因，仅 status=="终止" 时有值
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
```

### 5.2 新增状态常量

```python
# core/models.py — 替代旧 APPLICATION_STATUSES

APPLICATION_STATUSES_V2 = [
    "已投递",
    "简历评估",
    "笔试/测评",
    "一面",
    "二面",
    "HR面",
    "Offer",
    "终止",
    "放弃",
]

# 旧常量保留但标记为 deprecated
APPLICATION_STATUSES = [...]  # deprecated, use APPLICATION_STATUSES_V2
```

### 5.3 NEXT_ACTION_MAP 更新

```python
NEXT_ACTION_MAP_V2: dict[str, str] = {
    "已投递": "等待反馈，5-7 个工作日后可跟进",
    "简历评估": "简历已进入评估阶段，关注邮件/短信通知",
    "笔试/测评": "完成在线测评，注意截止时间",
    "一面": "准备技术基础、项目经验和算法题",
    "二面": "准备系统设计、项目深挖和行为面试",
    "HR面": "准备薪资期望、入职时间和职业规划",
    "Offer": "评估 Offer 条件，决定是否接受",
    "终止": "记录终止原因并复盘，为后续投递积累经验",
    "放弃": "归档该投递记录",
}
```

### 5.4 DataStore 新增方法

```python
# core/data_store.py

# Application
def delete_application(self, app_id: str):
    """删除一条投递记录，不删除关联的 Job 和 ResumeVersion。"""

# Resume
def delete_resume(self, resume_id: str):
    """删除简历版本，同时删除上传文件。调用前需检查引用。"""

def get_resume_application_count(self, resume_id: str) -> int:
    """返回引用该简历的 Application 数量。"""
```

### 5.5 数据兼容性

- 新增字段均有默认值（空字符串），**已有 store.json 数据无需手动迁移即可兼容**
- 旧状态字段值不变，用户在编辑时可以手动更新为新状态
- APPLICATION_STATUSES 常量保留但标记 deprecated，旧代码不强制修改
- `_deserialize_value` / `_model_from_dict` 自动忽略未使用的旧字段，向前兼容

---

## 6. 投递状态枚举定义

### 6.1 状态含义

| 状态 | 英文 key | 含义 | 典型触发条件 |
|------|---------|------|-------------|
| 已投递 | `applied` | 已提交申请，等待任何反馈 | 用户在招聘平台点击"投递"后 |
| 简历评估 | `resume_review` | HR 正在评估简历 | 收到公司通知"简历评估中" |
| 笔试/测评 | `exam` | 收到笔试或在线测评 | 收到笔试链接/测评邮件 |
| 一面 | `tech_1` | 第一轮面试（技术/群面） | 收到一面通知 |
| 二面 | `tech_2` | 第二轮面试（技术/经理） | 通过一面，收到二面通知 |
| HR面 | `hr` | HR 面试 | 通过技术面，进入 HR 面 |
| Offer | `offer` | 收到录用通知 | 收到 Offer 邮件/电话 |
| 终止 | `terminated` | 流程终止 | 被拒、超时无反馈、岗位关闭等 |
| 放弃 | `abandoned` | 用户主动放弃 | 用户自己决定不继续 |

### 6.2 状态流转图

```
                     ┌─────────┐
                     │  已投递  │
                     └────┬────┘
                          │
                    ┌─────▼─────┐
                    │  简历评估  │ (可选，部分公司有)
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │ 笔试/测评  │ (可选)
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │   一面    │
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │   二面    │ (可选)
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │   HR面    │ (可选)
                    └─────┬─────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
        ┌─────▼──┐  ┌─────▼──┐  ┌─────▼──┐
        │  Offer │  │  终止  │  │  放弃  │
        └────────┘  └────────┘  └────────┘
```

> 注：并非所有公司都遵循完整流转路径。简历评估、笔试/测评、二面、HR 面均为可选阶段。用户可以根据实际情况跳转。

---

## 7. 页面交互设计

### 7.1 投递看板卡片（增强后）

```
┌──────────────────────────────────────┐
│ 字节跳动                               ✏️ 编辑 │
│ 后端开发工程师（校招）                     │
│                                      │
│ 📄 后端开发-中文                       │
│ 🔗 内推链接 ← [NEW]                   │
│ 📅 2026-05-15 | 7天前                 │
│                                      │
│ 状态: [已投递 ▼]                      │
│                                      │
│ → 等待反馈，5-7 个工作日后可跟进          │
│ ● 中紧急                              │
└──────────────────────────────────────┘
```

### 7.2 编辑投递记录（Expander）

```
┌─ ✏️ 编辑投递记录 ────────────────────────┐
│                                      │
│ 岗位：字节跳动 — 后端开发工程师（只读）     │
│ 简历：后端开发-中文（只读）               │
│                                      │
│ 投递状态：[已投递 ▼]                    │
│ 投递日期：[2026-05-15]                 │
│ 投递渠道：[内推]                        │
│ 投递链接：[________________] ← [NEW]  │
│                                      │
│ 备注：                                │
│ [一面已过，等待二面通知...]             │
│                                      │
│ [保存修改] (primary)                   │
│                                      │
│ ───────────────                      │
│ ⚠️ 危险区域                           │
│ ☐ 我确认要删除此投递记录                 │
│ [🗑 删除投递记录] (red)                 │
└──────────────────────────────────────┘
```

### 7.3 简历卡片（增强后）

```
┌──────────────────────────────────────┐
│ 后端开发-中文                          │
│ 📎 resume_backend_cn.pdf · 更新于05-15 │
│ 📌 后端                               │
│                                      │
│ 📊 投递 4 次 | 🎤 面试 2 次           │
│                                      │
│ 🔑 核心关键词                          │
│ [Python] [Java] [Go] [MySQL] [Redis]  │
│                                      │
│ 🚀 项目亮点                           │
│ │ 分布式KV存储系统 · 支持10万QPS       │
│ │ 基于Go的微服务网关 · 日均千万请求     │
│                                      │
│ [👁 预览] [✏️ 编辑] ← [NEW]           │
└──────────────────────────────────────┘
```

### 7.4 简历预览（Expander）

```
┌─ 👁 简历预览：后端开发-中文 ──────────────┐
│                                      │
│ 文件：resume_backend_cn.pdf           │
│ 类型：PDF                             │
│                                      │
│ ── 文本预览 ─────────────────────────  │
│                                      │
│ 教育背景                              │
│ 北京大学 计算机科学与技术 硕士...        │
│                                      │
│ 技能                                 │
│ Python, Java, Go, MySQL, Redis...     │
│                                      │
│ 实习经历                              │
│ 字节跳动 后端开发实习生...              │
│                                      │
│ [⬇ 下载原文件]                        │
└──────────────────────────────────────┘
```

---

## 8. 删除和编辑的安全约束

### 8.1 投递记录删除

| 约束 | 规则 |
|------|------|
| 二次确认 | 删除前需要用户勾选 checkbox 确认 |
| 关联 Job | 不删除，保留 |
| 关联 ResumeVersion | 不删除，保留 |
| 关联 InterviewRecord | 不删除（标记为未来需处理的孤儿数据） |
| 关联 MatchResult | 不删除（历史匹配结果保留） |
| 不可逆 | 删除后不可恢复，确认 prompt 中明确告知 |

### 8.2 简历版本删除

| 约束 | 规则 |
|------|------|
| 引用检查 | 检查 Application 表中 resume_id 的引用次数 |
| 有引用 | **阻止删除**，提示引用数量和建议操作 |
| 无引用 | 允许删除，二次确认 |
| 关联文件 | 删除 `data/resumes/{resume_id}_*` 下的上传文件 |
| 关联 MatchResult | 不删除（标记为未来需处理的孤儿数据） |
| 不可逆 | 删除后不可恢复 |

### 8.3 编辑约束

| 约束 | 规则 |
|------|------|
| 岗位/简历关联 | 投递记录的 job_id 和 resume_id 不可修改（架构约束） |
| 状态变更 | 投递状态可自由切换，无流转限制（MVP 不做强制流转） |
| 并发 | MVP 单用户场景，不做并发锁 |

---

## 9. 简历预览策略

### 9.1 技术方案选择

| 方案 | 优点 | 缺点 | 采用 |
|------|------|------|------|
| PyPDF2 | 轻量，纯 Python，无系统依赖 | 对复杂排版 PDF 提取效果一般 | ✅ 首选 |
| pdfplumber | 提取效果好，支持表格 | 略重 | ✅ 备选 |
| pdf.js 嵌入 | 完美的渲染效果 | 需要前端 iframe + CDN，Streamlit 支持有限 | ❌ 不采用 |
| 系统 PDF 阅读器 | 效果最好 | 无法在 Web 中直接展示 | ❌ 不采用 |
| python-docx | 标准方案 | 无法处理复杂格式 | ✅ |

### 9.2 降级策略

```
尝试 PDF 文本提取
    ├── 成功 → 展示文本内容
    └── 失败 → 提供文件下载按钮 + 文件路径
```

### 9.3 依赖管理

在 `requirements.txt` 中新增（或确认已有）：

```
PyPDF2>=3.0.0
pdfplumber>=0.10.0
python-docx>=1.0.0
```

如果用户未安装这些依赖，导入失败时 graceful degradation：提示"需要安装 PyPDF2 以支持 PDF 预览：pip install PyPDF2"，同时提供文件下载。

---

## 10. 中文导航调整方案

### 10.1 当前导航机制

OfferPilot 使用 **Streamlit pages 自动导航**。侧边栏导航由 `pages/` 目录下的文件自动生成：
- 文件名格式：`{number}_{English_Name}.py`
- Streamlit 自动将文件名转换为导航条目（去掉数字前缀和下划线）

当前 pages 文件命名：
```
pages/
├── 1_Dashboard.py        → 侧边栏显示 "Dashboard"
├── 2_Job_Tracker.py      → 侧边栏显示 "Job Tracker"
├── 3_Resume_Vault.py     → 侧边栏显示 "Resume Vault"
├── 4_Match_Lab.py        → 侧边栏显示 "Match Lab"
├── 5_Interview_Prep.py   → 侧边栏显示 "Interview Prep"
└── 6_Weekly_Review.py    → 侧边栏显示 "Weekly Review"
```

### 10.2 目标导航

侧边栏映射关系：

| 当前文件名 | 当前显示 | 目标显示 |
|-----------|---------|---------|
| 1_Dashboard.py | Dashboard | **概览** |
| 2_Job_Tracker.py | Job Tracker | **投递池** |
| 3_Resume_Vault.py | Resume Vault | **简历池** |
| 4_Match_Lab.py | Match Lab | **匹配分析** |
| 5_Interview_Prep.py | Interview Prep | **面试准备** |
| 6_Weekly_Review.py | Weekly Review | **求职复盘** |

**app.py**（入口/首页）保持显示 "OfferPilot" 或设定为 "**首页**"。

### 10.3 实现方案

**方案 A：重命名文件（推荐）**

将 pages 目录下的 `.py` 文件重命名为中文：

```
pages/
├── 1_概览.py
├── 2_投递池.py
├── 3_简历池.py
├── 4_匹配分析.py
├── 5_面试准备.py
└── 6_求职复盘.py
```

Streamlit 会自动将文件名（去掉 `N_` 前缀和 `.py` 后缀）显示为侧边栏导航条目。

**优点**：零代码改动，Streamlit 原生支持。
**风险**：Windows 中文文件名可能在某些 CI/CD 环境中有编码问题。本地开发完全可用。
**验证**：Streamlit ≥ 1.28 版本已完全支持 Unicode 文件名。

**方案 B：使用 page_title 参数**

在每个页面的 `st.set_page_config()` 中设置 `page_title` 参数。但这只改变浏览器标签页标题，**不影响侧边栏导航条目**。Streamlit 侧边栏条目始终使用文件名。

**结论**：采用方案 A，直接重命名页面文件。

### 10.4 同步修改

重命名文件后，以下位置需要同步更新：

1. **`app.py`**：`st.page_link()` 中的路径引用（如果使用了 page_link）
2. **`pages/1_概览.py`（原 Dashboard）**：`st.page_link()` 引用
3. **页面内部标题**：每个页面内的 `st.title()` 改为中文
4. **页面内部 `st.set_page_config(page_title=...)`**：改为中文

### 10.5 页面内部标题同步

| 页面 | 当前 st.title() | 目标 st.title() |
|------|----------------|-----------------|
| app.py | OfferPilot | 首页 |
| 1_Dashboard.py | Dashboard | 求职概览 |
| 2_Job_Tracker.py | Job Tracker | 投递池 |
| 3_Resume_Vault.py | Resume Vault | 简历池 |
| 4_Match_Lab.py | Match Lab | 匹配分析 |
| 5_Interview_Prep.py | Interview Prep | 面试准备 |
| 6_Weekly_Review.py | Weekly Review | 求职复盘 |

---

## 11. 非本次迭代范围

以下功能**不在**本轮迭代中：

- ❌ 新增 AI 功能或 LLM 调用
- ❌ 多用户/登录/权限系统
- ❌ 数据库迁移（仍使用 JSON 文件存储）
- ❌ 移动端适配
- ❌ 邮件/日历/招聘平台 API 集成
- ❌ 批量操作（批量删除、批量状态变更）
- ❌ 数据导入导出（v0.1 已有 Markdown 导出，不扩展）
- ❌ 面试记录编辑/删除（本次只做 Application 和 Resume 的 CRUD）
- ❌ 岗位编辑/删除（本次聚焦投递和简历，岗位管理已有基本能力）
- ❌ 简历版本历史/差异对比
- ❌ 自动清理孤儿数据（被删除 Resume 关联的 MatchResult 等）
- ❌ 投递状态流转限制（MVP 不做强制流转校验）

---

## 12. 验收标准

### 12.1 投递池

- [ ] 投递看板每条记录有编辑入口，点击后展开编辑表单
- [ ] 编辑表单预填所有当前值，可修改状态、日期、渠道、链接、备注
- [ ] 状态为"终止"时，显示并必填终止原因字段
- [ ] 编辑保存后，看板即时刷新
- [ ] 投递记录可删除，删除前有 checkbox 二次确认
- [ ] 删除投递记录后，关联的 Job 和 ResumeVersion 不受影响
- [ ] 创建投递记录时可填写投递链接
- [ ] 看板卡片上可看到投递链接（如有）
- [ ] 新状态枚举 `APPLICATION_STATUSES_V2` 在创建、编辑、看板、统计中一致使用

### 12.2 简历池

- [ ] 简历卡片有编辑按钮，点击后展开编辑表单
- [ ] 编辑表单预填所有当前值
- [ ] 编辑保存后，卡片即时刷新
- [ ] 简历可删除，删除前有二次确认
- [ ] 被投递记录引用的简历不允许删除，有明确提示
- [ ] 简历卡片有预览按钮
- [ ] txt 文件可正确展示文本内容
- [ ] pdf 文件可提取文本展示，或至少提供下载按钮
- [ ] docx 文件可提取文本展示，或至少提供下载按钮
- [ ] 预览不影响卡片列表布局

### 12.3 中文导航

- [ ] 侧边栏导航条目全部为中文（概览/投递池/简历池/匹配分析/面试准备/求职复盘）
- [ ] 每个页面内部 `st.title()` 为中文
- [ ] 浏览器标签页标题为中文
- [ ] `app.py` 中 `st.page_link()` 路径正确指向重命名后的文件

### 12.4 全局

- [ ] 已有功能不受影响：JD 解析、匹配分析、面试准备、周报生成、导出均可正常使用
- [ ] 已有 store.json 数据在新版本中可正常加载（向前兼容）
- [ ] 无 import 错误，无 500 错误
- [ ] 二次确认删除机制有效防止误删

---

## 13. 开发任务拆解

以下为 Claude Code 可直接按序执行的开发任务。

### Task 1: 数据模型更新

**文件**：`core/models.py`

- [ ] 新增 `application_url` 字段到 `Application` dataclass
- [ ] 新增 `termination_reason` 字段到 `Application` dataclass
- [ ] 新增 `APPLICATION_STATUSES_V2` 常量
- [ ] 新增 `NEXT_ACTION_MAP_V2` 常量
- [ ] 标记旧 `APPLICATION_STATUSES` 和 `NEXT_ACTION_MAP` 为 deprecated（添加注释）

### Task 2: DataStore CRUD 增强

**文件**：`core/data_store.py`

- [ ] 新增 `delete_application(app_id: str)` 方法
- [ ] 新增 `delete_resume(resume_id: str)` 方法（含文件清理逻辑）
- [ ] 新增 `get_resume_application_count(resume_id: str) -> int` 方法

### Task 3: 简历预览服务

**文件**：`services/resume_viewer.py`（新建）

- [ ] 实现 `extract_text(file_path: str) -> str | None`
  - txt: `open().read()`
  - pdf: `PyPDF2.PdfReader()` 逐页提取文本
  - docx: `python-docx.Document()` 逐段提取文本
- [ ] 实现 `get_file_type(file_path: str) -> str`（返回 "txt" / "pdf" / "docx" / "unknown"）
- [ ] 异常处理：文件不存在、格式错误、依赖缺失时 graceful degradation

### Task 4: 依赖更新

**文件**：`requirements.txt`

- [ ] 添加 `PyPDF2>=3.0.0`
- [ ] 添加 `pdfplumber>=0.10.0`（可选，作为 PyPDF2 的增强备选）
- [ ] 添加 `python-docx>=1.0.0`（或确认已存在）

### Task 5: 投递池页面更新

**文件**：`pages/2_Job_Tracker.py`（重命名后为 `2_投递池.py`）

- [ ] 创建投递记录表单增加"投递链接"字段
- [ ] 状态 selectbox 使用 `APPLICATION_STATUSES_V2`
- [ ] 看板卡片增加编辑按钮（或点击卡片展开编辑）
- [ ] 编辑 expander：预填当前值，展示可修改字段
- [ ] 终止原因字段：条件显示（仅 status=="终止"）
- [ ] 删除按钮 + checkbox 二次确认
- [ ] 投递链接在看板卡片上展示（可点击）
- [ ] 状态统计栏使用 `APPLICATION_STATUSES_V2`

### Task 6: 简历池页面更新

**文件**：`pages/3_Resume_Vault.py`（重命名后为 `3_简历池.py`）

- [ ] 每个简历卡片增加"编辑"按钮
- [ ] 编辑 expander：预填当前值
- [ ] 每个简历卡片增加"预览"按钮
- [ ] 预览 expander：根据文件类型展示文本或下载按钮
- [ ] 编辑区域底部"删除简历"按钮
- [ ] 删除前引用检查 + 二次确认
- [ ] 被引用时的阻止删除提示

### Task 7: 状态枚举迁移（全局）

**影响文件**：

- [ ] `services/action_planner.py` — 更新状态判断逻辑，新增"简历评估"和"终止"的处理分支
- [ ] `services/weekly_review.py` — 更新状态统计和漏斗图状态列表
- [ ] `pages/1_Dashboard.py` — 更新指标统计和面试状态过滤
- [ ] `pages/5_Interview_Prep.py` — 更新面试阶段状态判断
- [ ] `pages/6_Weekly_Review.py` — 更新投递漏斗状态列表
- [ ] `core/mock_data.py` — 更新 mock Application 数据的状态值

### Task 8: 中文导航重命名

**操作**：重命名 `pages/` 目录下的文件

```bash
# 在项目根目录执行
cd pages
mv 1_Dashboard.py      1_概览.py
mv 2_Job_Tracker.py    2_投递池.py
mv 3_Resume_Vault.py   3_简历池.py
mv 4_Match_Lab.py      4_匹配分析.py
mv 5_Interview_Prep.py 5_面试准备.py
mv 6_Weekly_Review.py  6_求职复盘.py
```

**同步更新**：

- [ ] `app.py` — 更新页面标题和 page_link 引用
- [ ] 所有页面的 `st.set_page_config(page_title=...)` 改为中文
- [ ] 所有页面的 `st.title()` 改为中文
- [ ] 所有页面的 `st.caption()` 改为中文说明
- [ ] `1_概览.py` 中的 `st.page_link()` 路径引用更新

### Task 9: 兼容性验证与收尾

- [ ] 启动 app，加载已有 `data/store.json`
- [ ] 验证已有数据正常显示
- [ ] 遍历所有 6 个页面，确认无 import 错误
- [ ] 验证创建→编辑→删除的完整闭环
- [ ] 验证简历预览功能
- [ ] 验证中文导航栏显示正确

---

## 附录 A：文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `core/models.py` | 修改 | 新增字段 + 状态常量 |
| `core/data_store.py` | 修改 | 新增 delete 方法 + 引用查询 |
| `core/mock_data.py` | 修改 | Mock 数据状态值更新 |
| `services/resume_viewer.py` | **新建** | 简历文本提取 |
| `services/action_planner.py` | 修改 | 状态枚举迁移 |
| `services/weekly_review.py` | 修改 | 状态枚举迁移 |
| `pages/1_Dashboard.py` → `1_概览.py` | 重命名 + 修改 | 中文导航 + 状态迁移 |
| `pages/2_Job_Tracker.py` → `2_投递池.py` | 重命名 + 修改 | 编辑/删除/链接/状态迁移 |
| `pages/3_Resume_Vault.py` → `3_简历池.py` | 重命名 + 修改 | 编辑/删除/预览 |
| `pages/4_Match_Lab.py` → `4_匹配分析.py` | 重命名 + 修改 | 中文导航 |
| `pages/5_Interview_Prep.py` → `5_面试准备.py` | 重命名 + 修改 | 中文导航 + 状态迁移 |
| `pages/6_Weekly_Review.py` → `6_求职复盘.py` | 重命名 + 修改 | 中文导航 + 状态迁移 |
| `app.py` | 修改 | page_link 路径更新 + 中文标题 |
| `requirements.txt` | 修改 | 新增 PDF/DOCX 依赖 |
| `ITERATION_PRD_v0.2.md` | **新建** | 本文档 |

---

*本 PRD 不涉及新增 AI 功能，重点为求职管理基础能力的完整化。所有变更向后兼容，已有数据无需手动迁移。*
