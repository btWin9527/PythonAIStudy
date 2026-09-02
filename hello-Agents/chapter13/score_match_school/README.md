# 高考志愿填报助手

基于 LangChain + 通义千问（qwen-max）+ DuckDuckGo 联网搜索构建的高考志愿填报 AI 助手。用户输入报考省份、高考分数、报考类别和意向专业，AI 生成冲/稳/保三档志愿方案，每条推荐具体到学校 + 专业。

## 功能特点

- **AI 驱动的志愿推荐**: LangChain `create_agent` + 通义千问大模型，联网搜索近 3 年投档线后智能推荐
- **冲稳保三档方案**: 按分数差自动分为冲刺、稳妥、保底三档，每档独立展示
- **省份硬约束**: Prompt 约束 + Python 后处理双保险，只推荐报考目标省份内的学校
- **跨档位去重**: 同一学校不会在多个档位中重复出现
- **联网搜索**: DuckDuckGo 免费搜索，无需 API Key，获取实时分数线数据
- **结果导出**: 支持将志愿方案导出为图片 / PDF
- **现代化前端**: Vue 3 + TypeScript + Ant Design Vue，响应式设计

## 技术栈

### 后端
- **Agent 框架**: LangChain 1.3.x (`create_agent`)
- **LLM**: 通义千问 qwen-max（DashScope 兼容模式）
- **联网搜索**: DuckDuckGo Search（`langchain-community` 工具，免费）
- **API**: FastAPI + Uvicorn
- **数据校验**: Pydantic

### 前端
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI 组件库**: Ant Design Vue
- **导出**: html2canvas + jsPDF
- **HTTP 客户端**: Axios

## 项目结构

```
score_match_school/
├── backend/                         # 后端服务
│   ├── app/
│   │   ├── agents/                  # Agent 实现（分层架构）
│   │   │   ├── prompts/             # Prompt 模板（txt 文件）
│   │   │   │   ├── volunteer_system.txt   # 系统提示词
│   │   │   │   └── volunteer_user.txt     # 用户提示词
│   │   │   ├── constants.py         # 枚举/常量（省份关键词、院校类型等）
│   │   │   ├── prompt_loader.py     # Prompt 加载器（读 txt + 变量填充）
│   │   │   ├── parsers.py           # 工具函数（JSON 提取、省份过滤、去重、降级）
│   │   │   └── volunteer_agent.py   # Agent 编排层（薄入口）
│   │   ├── api/                     # FastAPI 路由
│   │   │   ├── main.py
│   │   │   └── routes/volunteer.py
│   │   ├── models/schemas.py        # 数据模型
│   │   └── config.py                # 配置管理
│   ├── requirements.txt
│   └── .env
├── frontend/                        # 前端应用
│   ├── src/
│   │   ├── views/
│   │   │   ├── Home.vue             # 填报表单页
│   │   │   └── Result.vue           # 结果展示页（冲稳保 + 筛选 + 导出）
│   │   ├── services/api.ts          # API 调用
│   │   ├── types/index.ts           # TypeScript 类型
│   │   ├── utils/export.ts          # 图片/PDF 导出
│   │   └── main.ts
│   ├── package.json
│   └── vite.config.ts
├── REFACTOR_PLAN.md                 # 改造方案文档
└── README.md
```

## 快速开始

### 前提条件

- Python 3.10+
- Node.js 16+
- 通义千问 API Key（DashScope）

### 后端

1. 进入后端目录
```bash
cd backend
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
```bash
# 编辑 .env 文件，填入你的 DashScope API Key
LLM_MODEL_ID=qwen-max
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

5. 启动后端服务
```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

1. 进入前端目录
```bash
cd frontend
```

2. 安装依赖
```bash
npm install
```

3. 启动开发服务器
```bash
npm run dev
```

4. 打开浏览器访问 `http://localhost:5173`

## 使用指南

1. 在首页填写高考信息:
   - 报考省份（目标省份）
   - 高考分数
   - 报考类别（理科 / 文科 / 艺术类）
   - 意向专业

2. 点击"生成方案"按钮，AI 将:
   - 联网搜索近 3 年该省投档线
   - 搜索该省内院校及专业信息
   - 生成冲/稳/保三档志愿方案

3. 在结果页查看:
   - 院校名称 + 专业名称
   - 参考分数 + 信心度
   - 院校类型（综合类/理工类等）+ 层级（985/211/双一流/普本）
   - 信息来源链接

4. 支持按院校类型、层级、关键词、信心度筛选

5. 支持导出为图片或 PDF

## API 文档

启动后端服务后，访问 `http://localhost:8000/docs` 查看完整 API 文档。

主要端点:
- `POST /api/volunteer/generate` - 生成志愿方案
- `GET /api/volunteer/provinces` - 获取省份列表
- `GET /api/volunteer/health` - 健康检查
- `GET /health` - 服务状态

## 核心设计

### Agent 分层架构

```
volunteer_agent.py  ← 编排层（薄入口）
    ├── prompt_loader.py  ← Prompt 加载（从 txt 读模板 + 填充变量）
    │   └── prompts/*.txt    ← Prompt 模板文件（与代码解耦）
    ├── parsers.py          ← 工具函数（JSON提取/省份过滤/去重/降级）
    └── constants.py        ← 枚举常量（省份关键词/院校类型/档位标签）
```

### 省份过滤双保险

| 层级 | 方法 | 效果 |
|------|------|------|
| Prompt 层 | 系统提示词中写死"学校必须位于报考省份内" | LLM 搜索时只找省内学校 |
| Python 层 | `check_province_match()` 后处理校验 | 过滤掉校名含其他省份关键词的学校 |

### 数据流水线

```
用户请求 → build_prompt → agent.invoke → 提取输出
→ extract_json → json.loads → plan_from_dict
→ filter_schools_by_province → deduplicate_across_tiers → 返回
```

## 开源协议

CC BY-NC-SA 4.0
