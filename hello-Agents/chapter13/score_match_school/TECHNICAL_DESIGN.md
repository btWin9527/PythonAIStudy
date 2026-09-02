# 技术方案文档 - 高考志愿填报助手

## 一、项目概述

### 1.1 项目定位

基于大模型 + 联网搜索的高考志愿填报 AI 助手。用户输入报考省份、高考分数、报考类别和意向专业，系统通过 LangChain Agent 调用 DuckDuckGo 联网搜索近 3 年分数线数据，由通义千问大模型生成冲/稳/保三档志愿方案。

### 1.2 核心约束

- **无数据库**：所有数据通过大模型联网搜索获取，不做持久化存储
- **一次性操作**：无记忆功能，每次查询独立
- **省份硬约束**：只推荐报考目标省份内的学校

---

## 二、技术栈

### 2.1 后端技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Web 框架 | FastAPI | >=0.115.0 | RESTful API 服务 |
| ASGI 服务器 | Uvicorn | >=0.32.0 | 异步 HTTP 服务器 |
| Agent 框架 | LangChain | >=1.3.0 | `create_agent` ReAct 模式 |
| LLM 接口 | langchain-openai | >=1.3.0 | ChatOpenAI（OpenAI 兼容协议） |
| 联网搜索 | langchain-community + duckduckgo-search | >=0.4.0 / >=6.0.0 | DuckDuckGo 免费搜索 |
| LLM 模型 | qwen-max | - | 阿里云 DashScope，OpenAI 兼容模式 |
| 数据校验 | Pydantic | >=2.0.0 | 请求/响应数据模型 |
| 配置管理 | pydantic-settings + python-dotenv | >=2.0.0 | 环境变量管理 |
| 跨域支持 | python-multipart | >=0.0.9 | CORS 中间件依赖 |

### 2.2 前端技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | Vue 3 | ^3.5.13 | Composition API SPA |
| 语言 | TypeScript | ^5.7.3 | 类型安全 |
| 构建 | Vite | ^6.0.7 | 开发服务器 + 生产构建 |
| UI 库 | Ant Design Vue | ^4.2.6 | 表单/卡片/选择器 |
| 图标 | @ant-design/icons-vue | ^7.0.1 | 加载/箭头图标 |
| 路由 | Vue Router | ^4.5.0 | SPA 路由 |
| HTTP | Axios | ^1.7.9 | API 调用 |
| 图片导出 | html2canvas | ^1.4.1 | DOM → Canvas → 图片 |
| PDF 导出 | jsPDF | ^3.0.3 | Canvas → PDF |

### 2.3 外部服务

| 服务 | 提供方 | 费用 | 用途 |
|------|--------|------|------|
| qwen-max LLM | 阿里云 DashScope | 按量计费 | 志愿方案生成 |
| DuckDuckGo 搜索 | DuckDuckGo | 免费 | 联网搜索分数线 |

---

## 三、系统架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Vue 3 SPA)                      │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Home.vue    │    │ Result.vue   │    │  export.ts    │  │
│  │  填报表单    │───→│ 冲稳保+筛选   │    │ 图片/PDF导出  │  │
│  └──────┬───────┘    └──────┬───────┘    └───────────────┘  │
│         │ Axios POST         │ sessionStorage               │
└─────────┼────────────────────┼─────────────────────────────┘
          │                    │
          ▼                    │
┌─────────────────────────────┼─────────────────────────────┐
│                     后端 (FastAPI)                        │
│  ┌──────────────────────────┴────────────────────────┐   │
│  │              /api/volunteer/generate               │   │
│  │              (volunteer.py 路由层)                  │   │
│  └──────────────────────┬────────────────────────────┘   │
│                         │                                  │
│  ┌──────────────────────▼────────────────────────────┐   │
│  │           volunteer_agent.py (编排层)              │   │
│  │   build_prompt → invoke → extract → parse          │   │
│  └──┬────────────┬──────────────┬──────────────┬────┘   │
│     │            │              │              │         │
│     ▼            ▼              ▼              ▼         │
│  prompt_loader  parsers.py   constants.py  ChatOpenAI   │
│  (读txt+填充)   (过滤/去重)   (枚举常量)        │         │
│                                                │         │
└────────────────────────────────────────────────┼─────────┘
                                                 │
                              ┌──────────────────┼──────────┐
                              │                  │          │
                              ▼                  ▼          │
                    ┌──────────────┐  ┌──────────────┐     │
                    │  qwen-max    │  │  DuckDuckGo  │     │
                    │  (DashScope) │  │  Search API  │     │
                    └──────────────┘  └──────────────┘     │
                                                       │     │
                                              ┌─────────────┘
                                              ▼
                                     ┌─────────────────┐
                                     │  搜索结果网页     │
                                     │  (教育考试院等)   │
                                     └─────────────────┘
```

### 3.2 后端 Agent 分层架构

```
backend/app/agents/
│
├── volunteer_agent.py          ← 编排层（薄入口，仅流程编排）
│   ├── _get_llm()              ← 构建 ChatOpenAI 实例
│   ├── _build_tools()          ← 构建 DuckDuckGo 工具列表
│   ├── VolunteerAgent 类        ← Agent 封装
│   │   ├── initialize()        ← create_agent(model, tools, system_prompt)
│   │   ├── generate()          ← 主入口：构建prompt → invoke → 解析 → 过滤 → 返回
│   │   ├── _invoke_with_system()← system+user 消息注入
│   │   ├── _extract_final_output() ← 从 messages 提取 AIMessage.content
│   │   └── _parse_output_to_plan()← JSON解析 → plan_from_dict → 省份过滤 → 去重
│   └── get_volunteer_agent()   ← 单例入口
│
├── prompt_loader.py            ← Prompt 加载层
│   ├── _load_template()        ← 读取 txt 模板（带缓存）
│   ├── build_system_prompt()   ← 填充 {province}/{year-1}/{score} 等变量
│   └── build_human_prompt()    ← 填充 {province}/{score}/{subject_label}
│
├── prompts/                    ← Prompt 模板文件（与代码解耦）
│   ├── volunteer_system.txt    ← 系统提示词（省份约束+搜索工作流+填报策略+JSON格式）
│   └── volunteer_user.txt      ← 用户提示词（省份+分数+类别+专业）
│
├── parsers.py                  ← 工具函数集（纯函数，可独立测试）
│   ├── extract_json()          ← 从 LLM 输出提取 JSON（3 种策略）
│   ├── parse_confidence()      ← 安全解析 confidence（钳位 0-100）
│   ├── validate_school_name()   ← 校验学校名真实性（后缀+长度）
│   ├── check_province_match()  ← 省份归属检查（3 条规则）
│   ├── filter_schools_by_province() ← 方案整体省份过滤
│   ├── deduplicate_across_tiers()   ← 跨档位去重
│   ├── plan_from_dict()        ← JSON dict → VolunteerPlan 对象
│   └── build_fallback_plan()   ← 降级占位方案
│
└── constants.py                ← 枚举/常量
    ├── SUBJECT_CATEGORY_LABELS ← 报考类别映射
    ├── SCHOOL_TYPE_VALUES      ← 院校类型枚举
    ├── SCHOOL_LEVEL_VALUES     ← 院校层级枚举
    ├── TIER_LABELS             ← 冲稳保档位标签
    ├── TIER_STRATEGIES         ← 冲稳保分数偏移策略
    ├── SCHOOL_SUFFIXES         ← 学校后缀关键词
    ├── PROVINCE_KEYWORDS       ← 省份→关键词映射（含省会/中心城市）
    └── DEFAULT_DISCLAIMER      ← 免责声明
```

---

## 四、数据流转处理

### 4.1 完整数据流

```
用户操作                    前端                      后端                      外部
─────────────────────────────────────────────────────────────────────────────────────

[填写表单]                  │                         │                         │
 省份+分数+类别+专业         │                         │                         │
      │                      │                         │                         │
      ▼                      │                         │                         │
[点击生成] ─────────────→  POST /api/volunteer/generate │                         │
                            │      (Axios, 3min超时)    │                         │
                            │                         │                         │
                            │              [构建 Prompt]                         │
                            │              build_system_prompt()                 │
                            │              build_human_prompt()                  │
                            │                         │                         │
                            │              [Agent invoke]                       │
                            │              agent.invoke({                       │
                            │                messages: [                        │
                            │                  ("system", system_prompt),      │
                            │                  ("user", human_prompt)          │
                            │                ]                                  │
                            │              })                                    │
                            │                         │                         │
                            │                         │  [LLM 决策: 需要搜索] ──→ DuckDuckGo
                            │                         │                         │  搜索:
                            │                         │  ←──────────────────── 返回结果
                            │                         │                         │
                            │                         │  [LLM 决策: 再搜索] ──→ DuckDuckGo
                            │                         │  ←──────────────────── 返回结果
                            │                         │                         │
                            │                         │  [LLM 生成最终 JSON] ──→ qwen-max
                            │                         │  ←──────────────────── 返回 JSON
                            │                         │                         │
                            │              [提取输出]                          │
                            │              _extract_final_output()              │
                            │              → AIMessage.content                 │
                            │                         │                         │
                            │              [解析 JSON]                          │
                            │              extract_json() → json.loads()       │
                            │              → plan_from_dict()                  │
                            │                         │                         │
                            │              [省份过滤]                          │
                            │              filter_schools_by_province()         │
                            │              → 过滤掉含他省关键词的学校            │
                            │                         │                         │
                            │              [跨档位去重]                        │
                            │              deduplicate_across_tiers()          │
                            │              → 同校只保留首次出现的档位            │
                            │                         │                         │
                            │              [返回 VolunteerPlan]               │
                            │  ←──────────────────── JSON Response               │
                            │                         │                         │
[sessionStorage 存储]       │                         │                         │
      │                      │                         │                         │
      ▼                      │                         │                         │
[路由跳转 /result]           │                         │                         │
      │                      │                         │                         │
      ▼                      │                         │                         │
[结果展示]                  │                         │                         │
 冲稳保 Tabs                 │                         │                         │
 筛选/导出                   │                         │                         │
```

### 4.2 前端页面间数据流向

```
首页填写条件 → POST /api/volunteer/generate → 后端 Agent 生成 JSON
    ↓
前端 sessionStorage 存储（volunteerPlan + volunteerProfile）
    ↓
路由跳转到 /result
    ↓
结果页读取 sessionStorage → 二次条件筛选 → 展示冲/稳/保三档
    ↓
可选：导出图片/PDF
```

### 4.3 请求/响应数据模型

#### 请求（VolunteerRequest）

```json
{
  "province": "山西",
  "score": 580,
  "subject_category": "science",
  "target_major": "计算机"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| province | string | 是 | 报考目标省份 |
| score | int (100-750) | 是 | 高考分数 |
| subject_category | string | 是 | `science` / `arts` / `art` |
| target_major | string | 否 | 意向专业，空则不限 |

#### 响应（VolunteerPlanResponse）

```json
{
  "success": true,
  "plan": {
    "summary": "总体策略建议...",
    "tiers": [
      {
        "tier_type": "chong",
        "tier_label": "冲刺院校",
        "description": "...",
        "schools": [
          {
            "school_name": "太原理工大学",
            "major_name": "计算机科学与技术",
            "confidence": 65,
            "reason": "...",
            "reference_score": 590,
            "school_type": "理工类",
            "school_level": "211",
            "reference_sources": ["https://..."]
          }
        ]
      }
    ],
    "disclaimer": "⚠️ 以上推荐仅供参考..."
  }
}
```

### 4.4 LLM 输出解析容错链

```
agent.invoke()
    │
    ▼
_extract_final_output()      ← 从 messages 列表取最后一个 AIMessage.content
    │                         ← 失败 → str(result) 兜底
    ▼
extract_json()               ← 3 种策略提取 JSON：
    │                         ① 首尾花括号 → 直接返回
    │                         ② ```json``` 代码块 → 正则提取
    │                         ③ 第一个{ 到最后一个} → 截取
    │                         ← 全部失败 → 降级方案
    ▼
json.loads()                 ← 标准 JSON 解析
    │                         ← 失败 → 降级方案
    ▼
plan_from_dict()             ← dict → VolunteerPlan 对象
    │                         ← 跳过无效学校条目，容错
    │                         ← tiers 为空 → 降级方案
    ▼
filter_schools_by_province() ← 省份过滤（含他省关键词的学校移除）
    │
    ▼
deduplicate_across_tiers()   ← 跨档位去重（同校只保留首次出现）
    │
    ▼
返回 VolunteerPlan
```

---

## 五、核心算法设计

### 5.1 省份过滤规则（check_province_match）

| 规则 | 条件 | 结果 | 示例 |
|------|------|------|------|
| 1 | 校名含目标省关键词（省名/省会/中心城市） | 保留 | 目标=山西，"太原理工大学"含"太原" → 保留 |
| 2 | 校名含**其他省**关键词 | 过滤 | 目标=山西，"北京大学"含"北京" → 过滤 |
| 3 | 校名不含任何省关键词 | 保留 | "清华大学"无省名 → 保留（Prompt 兜底） |

### 5.2 跨档位去重规则（deduplicate_across_tiers）

| 规则 | 说明 |
|------|------|
| 遍历顺序 | 冲 → 稳 → 保（首次出现保留） |
| 去重键 | `学校名 + 专业名`；专业为"不限"时仅按学校名 |
| 例外 | 同校不同专业（如天津大学计算机 + 天津大学软件工程）不算重复 |

### 5.3 冲稳保分档策略

| 档位 | 分数条件 | 推荐数量 | 配置位置 |
|------|---------|---------|---------|
| 冲档 (chong) | 参考线 ≥ 考生分数 + 10 | 5-8 所 | `prompts/volunteer_system.txt` |
| 稳档 (wen) | 考生分数 - 5 ≤ 参考线 ≤ 考生分数 + 5 | 6-10 所 | 同上 |
| 保档 (bao) | 参考线 ≤ 考生分数 - 10 | 5-8 所 | 同上 |

---

## 六、功能产出

### 6.1 首页（条件筛选输入）

- **报考省份**：34 个省/直辖市/自治区下拉选择
- **高考分数**：100-750 分数字输入框
- **意向专业**（可选）：自由输入
- **报考类别**：理科/物理类、文科/历史类、艺术类 三选一卡片式按钮
- **提交按钮**："计算冲、稳、保最佳方案" → 带进度条动画

### 6.2 结果页（展示 + 二次筛选 + 导出）

**条件筛选栏**：
- 按院校类型筛选：综合类/理工类/财经类/师范类/医药类/艺术类/语言类/政法类/农林类
- 按院校层级筛选：985工程/211工程/双一流/普通本科
- 按专业关键词搜索：实时过滤专业名称
- 按信心度滑动筛选：滑块调节最低信心度阈值
- 重置筛选 + 实时统计符合条件的院校数量

**结果展示区**：
- 考生画像卡片：省份、分数、报考类别、意向专业 + 总体策略建议
- 冲/稳/保 三档 Tab 切换（Tab 标签实时显示各档筛选后的院校数量）
- 学校卡片列表：序号 + 学校名 + 专业标签 + 参考分数线 + 信心度徽章（按档位颜色区分：冲=橙/稳=蓝/保=绿）+ 推荐理由
- 底部免责声明

**导出功能**：
- 导出为图片（PNG 格式，2 倍清晰度）
- 导出为 PDF（A4 规格，自动分页）
- 文件名自动包含：志愿方案_省份_分数_时间戳

---

## 七、API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/volunteer/generate` | 生成志愿方案（3 分钟超时） |
| GET | `/api/volunteer/provinces` | 获取 34 个省份列表 |
| GET | `/api/volunteer/health` | Agent 健康检查 |
| GET | `/health` | 服务状态 |
| GET | `/docs` | Swagger API 文档 |

---

## 八、部署架构

### 8.1 开发环境

```
前端: http://localhost:5173 (Vite dev server)
      └── proxy /api → http://localhost:8000

后端: http://localhost:8000 (Uvicorn)
      ├── .env (LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_ID)
      └── DuckDuckGo → 外部搜索
```

### 8.2 生产环境

```
Nginx (443/80)
  ├── / → 前端静态文件 (dist/)
  └── /api → 反向代理 → Uvicorn (localhost:8000)

后端:
  ├── Uvicorn (gunicorn -k uvicorn.workers.UvicornWorker)
  ├── .env 配置
  └── 无数据库依赖
```

### 8.3 部署清单

| 步骤 | 命令/操作 |
|------|----------|
| 1. 后端安装 | `cd backend && pip install -r requirements.txt` |
| 2. 后端配置 | 编辑 `backend/.env` 填入 LLM_API_KEY |
| 3. 后端启动 | `gunicorn app.api.main:app -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000` |
| 4. 前端构建 | `cd frontend && npm install && npm run build` |
| 5. 前端部署 | 将 `frontend/dist/` 放到 Nginx 静态目录 |
| 6. Nginx 配置 | `/api` 反向代理到 `localhost:8000` |

---

## 九、安全与限制

### 9.1 LLM 幻觉防护

| 层级 | 方法 | 防护效果 |
|------|------|---------|
| Prompt 层 | 真实性约束（教育部高校名录 + 专业目录 + 不编造） | 减少幻觉概率 |
| 搜索层 | DuckDuckGo 联网搜索实时数据 | 基于真实数据生成 |
| 后处理层 | 省份过滤 + 学校名校验 | 过滤掉不合法的推荐 |
| 降级层 | Agent 失败时返回占位方案 | 保证服务可用性 |

### 9.2 免责声明

所有推荐结果附带免责声明，提示用户以各省教育考试院官方发布和目标院校招生官网为准。

---

## 十、运维指南

### 10.1 如何调整冲/稳/保三档方案

冲稳保策略分布在 **3 个位置**，按修改场景选择：

| 需求 | 修改位置 | 文件 | 具体内容 |
|------|---------|------|---------|
| 调整分数偏移阈值 | 填报策略段 | `prompts/volunteer_system.txt` 第 28-30 行 | 冲档：`参考线 ≥ 考生分数 + 10`；稳档：`考生分数 - 5 ≤ 参考线 ≤ 考生分数 + 5`；保档：`参考线 ≤ 考生分数 - 10` |
| 调整推荐数量范围 | 填报策略段 | `prompts/volunteer_system.txt` 第 28-30 行 | 如冲档 `推荐 5-8 所` → 改为 `推荐 3-5 所` |
| 调整档位标签名称 | 常量定义 | `constants.py` 第 50-54 行 `TIER_LABELS` | 如 `"chong": "冲刺院校"` → `"chong": "冲击院校"` |
| 调整降级方案分数偏移 | 降级方案 | `parsers.py` 第 292-296 行 `build_fallback_plan` | 冲 `score+15`、稳 `score`、保 `score-15` |

**示例：把冲档阈值从 +10 改为 +15**

```
# 1. 编辑 prompts/volunteer_system.txt 第 28 行
- 冲档(chong)：参考线 ≥ 考生分数 + 10，推荐 5-8 所
+ 冲档(chong)：参考线 ≥ 考生分数 + 15，推荐 5-8 所

# 2. （可选）同步更新 constants.py 第 57 行 TIER_STRATEGIES
- "chong": "参考线 ≥ 考生分数 + 10，推荐 5-8 所",
+ "chong": "参考线 ≥ 考生分数 + 15，推荐 5-8 所",
```

> **注意**：Prompt 文件修改后，由于 `prompt_loader.py` 有缓存机制，需重启后端服务或调用 `_invalidate_cache()` 清除缓存。

---

## 十一、成本估算

### 11.1 A 类：项目部署固定费用（按年）

> 与调用量无关，只要服务在线就产生的固定成本。

| 项目 | 配置 | 月费用 | 年费用 | 说明 |
|------|------|--------|--------|------|
| 云服务器 | 4核8G 6M带宽 | ~150 元 | ~1,800 元 | 需支持 100 并发，2核4G 不够（见第十二章分析） |
| 域名 | .com | ~6 元 | ~70 元 | 可选 |
| SSL 证书 | Let's Encrypt | 0 | 0 | 免费 |
| 前端静态托管 | CDN/OSS | 0 ~ 10 元 | 0 ~ 120 元 | 流量小可免费，量大按量 |
| DuckDuckGo 搜索 | — | 0 | 0 | 免费 API |
| **固定成本合计** | | | **~1,870 元/年** | |

### 11.2 B 类：大模型使用费用（按次计算）

> 与查询次数成正比，用多少算多少。

#### 11.2.1 单次查询 Token 构成

| 组成部分 | 估算 Token | 说明 |
|---------|-----------|------|
| System Prompt（填充后） | ~1,500 | 省份约束 + 搜索工作流 + 填报策略 + JSON 格式 + 枚举值 |
| User Prompt | ~100 | 省份 + 分数 + 类别 + 专业 |
| 工具调用 - 搜索查询（6 次） | ~600 | 6 次 web_search |
| 工具返回 - 搜索结果 | ~3,000 | 6 次搜索返回的网页摘要 |
| LLM 推理输出 | ~2,500 | JSON 格式的冲稳保三档方案（16-26 所学校） |
| **单次总计** | **~8,000** | 输入 ~5,200 + 输出 ~2,800 |

#### 11.2.2 单次费用计算

> qwen-max 定价：输入 0.02 元/千 token，输出 0.06 元/千 token（DashScope 2024 年价格，仅供参考）

```
单次费用 = 输入 token × 0.02/1000 + 输出 token × 0.06/1000
        = 5,200 × 0.00002 + 2,800 × 0.00006
        = 0.104 + 0.168
        ≈ 0.27 元/次
```

| 模型选择 | 单次费用 | 效果 | 适用场景 |
|---------|---------|------|---------|
| qwen-max | ~0.27 元/次 | 最优 | 追求质量 |
| qwen-plus | ~0.08 元/次 | 良好 | 性价比首选 |
| qwen-turbo | ~0.03 元/次 | 一般 | 大批量低成本 |

#### 11.2.3 不同用户规模下的 LLM 年费用（qwen-max）

> 假设 1,000 用户，每人年均查询 5 次 = 5,000 次/年

| 用户规模 | 年查询次数 | 单次费用 | LLM 年费用 |
|---------|-----------|---------|-----------|
| 100 人 × 5 次 | 500 次 | 0.27 元 | ~135 元 |
| 1,000 人 × 5 次 | 5,000 次 | 0.27 元 | ~1,350 元 |
| 1,000 人 × 10 次 | 10,000 次 | 0.27 元 | ~2,700 元 |

#### 11.2.4 填写完整条件是否能减少 Token 消耗？

**结论：填写越完整，Token 消耗越少，减少幅度约 15-20%。**

| 场景 | Token 消耗 | 单次费用 | 原因 |
|------|-----------|---------|------|
| 只填省份 + 分数（不填专业） | ~9,500 | ~0.32 元 | LLM 需额外搜索"该省热门专业"，多 1-2 次搜索 |
| 填省份 + 分数 + 类别 | ~8,500 | ~0.29 元 | 类别缩小了搜索范围，但仍需泛搜索 |
| **全部填写（省份+分数+类别+专业）** | **~8,000** | **~0.27 元** | 搜索精准，减少无效搜索轮次 |

#### 11.2.5 优化建议

| 优化方向 | 预期节省 | 实现方式 |
|---------|---------|---------|
| 缩短 System Prompt | ~500 token | 移除搜索工作流冗余描述，LLM 自主决策 |
| 合并批次线搜索 | ~1,000 token | 3 次合并为 1 次"2023-2025年XX理科批次线" |
| 换便宜模型 | ~70% 费用 | qwen-max → qwen-plus（效果略降） |
| 缓存批次线结果 | ~2,000 token | 同省份同年份只搜 1 次（需引入缓存层） |

### 11.3 总费用汇总（1,000 用户 / 100 并发）

| 费用类型 | 明细 | 年费用 |
|---------|------|--------|
| 固定成本 | 4核8G 服务器 + 域名 + SSL | ~1,870 元 |
| 变动成本 | 5,000 次 × 0.27 元（qwen-max） | ~1,350 元 |
| **总计** | | **~3,220 元/年** |

> 如果用 qwen-plus（0.08 元/次），变动成本降至 400 元/年，总计 ~2,270 元/年

---

## 十二、并发处理

> 目标用户量 1,000 人，并发峰值 100。

### 12.1 当前架构并发瓶颈

| 瓶颈点 | 问题 | 严重程度 |
|--------|------|---------|
| **Agent 单例** | `get_volunteer_agent()` 返回全局单例，LangChain `create_agent` 返回的 agent 是**有状态**的（invoke 期间保留 message 历史），100 个并发请求同时调 `invoke` 会产生 **消息串台/数据竞争** | 🔴 致命 |
| **线程池默认大小** | `run_in_executor(None, ...)` 使用默认线程池（通常 max_workers=CPU×5），4核服务器约 20 线程，无法支撑 100 并发 | 🟡 高 |
| **LLM API 并发限制** | DashScope qwen-max 默认并发上限 60 QPS，100 并发可能被限流返回 429 | 🟡 高 |
| **DuckDuckGo 限流** | 免费版无官方 QPS 限制，但高频请求可能被临时封 IP | 🟡 中 |
| **单次请求耗时长** | 6 次搜索 + LLM 推理，单次约 30-60 秒，100 并发 × 60 秒 = 大量线程长时间阻塞 | 🟡 高 |

### 12.2 当前架构能支撑多少并发？

| 并发量 | 是否能支撑 | 原因 |
|--------|-----------|------|
| 1-5 并发 | ✅ 可以 | 单例串行无竞争，线程池足够 |
| 10-20 并发 | ⚠️ 勉强 | 可能出现消息串台，响应变慢 |
| 50+ 并发 | ❌ 不行 | 单例数据竞争 + 线程池耗尽 + API 限流 |
| 100 并发 | ❌ 完全不行 | 当前架构必然崩溃 |

### 12.3 支撑 100 并发的改造方案

**方案 1：每次请求创建独立 Agent 实例（最小改动，推荐）**

```python
# volunteer_agent.py — 改为每请求创建实例
def generate(self, request: VolunteerRequest) -> VolunteerPlan:
    # 不再用全局单例的 self._agent，而是每次创建
    llm = _get_llm()
    tools = _build_tools()
    agent = create_agent(model=llm, tools=tools, system_prompt=None)
    result = agent.invoke({"messages": [...]})
    # ...
```

优点：改动最小，无状态竞争；缺点：每次创建 Agent 有约 100ms 开销

**方案 2：Agent 池化（更高性能）**

```python
from queue import Queue

class AgentPool:
    def __init__(self, size=50):
        self._pool = Queue(maxsize=size)
        for _ in range(size):
            self._pool.put(self._create_agent())

    def _create_agent(self):
        return create_agent(model=_get_llm(), tools=_build_tools())

    @contextmanager
    def acquire(self):
        agent = self._pool.get()
        try:
            yield agent
        finally:
            self._pool.put(agent)
```

**方案 3：消息队列 + 后端 Worker（最可靠）**

```
用户请求 → FastAPI → 入队（Redis）→ 返回 task_id
                          ↓
                    Worker 池（N个进程）
                          ↓
                    调用 LLM + 搜索
                          ↓
                    结果存 Redis
                          ↓
前端轮询 task_id → 返回结果
```

### 12.4 100 并发推荐配置

| 项目 | 当前 | 需要调整为 | 原因 |
|------|------|-----------|------|
| 服务器 | 2核4G | **4核8G** | 支持 20+ 线程 + 内存余量 |
| Agent 实例 | 全局单例 | **每请求创建 / 池化** | 避免状态竞争 |
| Uvicorn Workers | 1 | **2-4** | 多进程分担 |
| 线程池 | 默认(CPU×5) | **显式设 max_workers=100** | 支撑并发 |
| DashScope QPS | 默认 60 | **申请提升到 200+** | 避免 429 限流 |
| 请求超时 | 3 分钟 | **保留 3 分钟** | 单次搜索+推理需要时间 |
| 前端体验 | 同步等待 | **加进度提示 + 可选异步** | 100 人同时等 60 秒体验差 |
