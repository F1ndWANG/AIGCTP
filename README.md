# AIGCTP - AI 生活推荐与规划系统

AIGCTP 是一个面向日常生活场景的 AI 多智能体推荐与执行系统。项目不是单纯的聊天机器人，而是把自然语言对话作为统一入口，将用户需求分发到行程规划、餐厅推荐、饮食健康、商品推荐、购物车和订单等业务模块，并把 AI 生成结果沉淀为可查询、可恢复、可继续操作的结构化数据。

## 项目定位

现代生活决策往往跨越多个场景：出行需要规划路线和行程，吃饭需要结合地点、口味和健康偏好，购物需要搜索商品、加入购物车并形成订单。传统应用通常把这些能力拆散在多个垂直系统中，用户需要反复切换工具。

AIGCTP 要解决的问题是：用一个统一的 AI 交互入口，理解用户的自然语言需求，并把推荐结果转化为可执行的系统能力。

系统核心目标包括：

- 用自然语言完成跨场景生活服务推荐。
- 将 AI 回复从一次性文本升级为结构化业务结果。
- 支持历史对话、历史行程、用户偏好和业务状态的持续沉淀。
- 让推荐结果继续流转到购物车、订单、行程确认、反馈分析等后续动作。
- 形成前后端分层清晰、可扩展、可观测、可继续演进的工程架构。

## 能解决的问题

- 用户不需要学习复杂表单，可以直接通过对话描述需求。
- 多领域推荐能力统一在一个入口下，减少应用切换成本。
- 行程、餐厅、饮食、商品等推荐结果可以保存和再次打开，不会只停留在聊天记录里。
- 系统可以基于历史会话和上下文继续优化推荐，而不是每次从零开始。
- 后端通过智能体编排、服务层和运行时记录，把 AI 调用变成可维护的业务流程。
- 前端提供登录、会话恢复、结果卡片、历史面板和业务页面，使推荐结果可以被用户真正使用。

## 核心功能

### 1. 用户与认证

- 用户注册、登录和退出。
- JWT 鉴权。
- 当前用户信息读取。
- 用户资料、密码和偏好配置维护。

### 2. AI 对话与会话管理

- 支持同步对话和 SSE 流式响应。
- 根据用户输入识别意图并路由到不同业务智能体。
- 支持历史对话列表、会话恢复和会话删除。
- 支持上下文携带，例如当前行程、商品、餐厅、饮食计划和购物车状态。
- 对失效会话进行自动清理，避免用户点击 AI 对话时持续恢复失败。

### 3. 行程规划

- 根据自然语言生成旅行计划。
- 支持行程列表、详情查看、确认和历史恢复。
- 支持基于用户追问继续调整行程。
- 集成路线规划能力，为行程结果提供后续导航支撑。

### 4. 餐厅推荐

- 支持按城市和口味偏好推荐餐厅。
- 支持附近餐厅查询。
- 推荐结果可以进入对话上下文，后续继续追问或选择。

### 5. 饮食健康

- 健康档案管理。
- 每日饮食记录。
- 饮食汇总和营养分析。
- AI 生成饮食计划并支持历史查看。

### 6. 商品、购物车与订单

- 商品分类、搜索、筛选和详情查看。
- AI 辅助商品推荐。
- 加入购物车、修改数量、删除商品和清空购物车。
- 创建订单、订单列表、取消订单和再次下单。
- 支持从对话中识别加购、复购等意图。

### 7. 反馈与分析

- 对推荐结果进行喜欢/不喜欢反馈。
- 按内容类型统计反馈数据。
- 提供汇总分析能力，用于后续优化推荐质量。

### 8. 高可用运行时基础

- 后端记录任务运行状态。
- 支持领域事件记录。
- 支持失败任务查询和重试接口。
- 为后续接入队列、异步工作流、审计追踪和可观测系统打基础。

## 整体架构

```text
用户
 |
 v
Next.js 前端
 |
 |-- 登录 / 注册
 |-- AI 对话
 |-- 行程 / 餐厅 / 饮食 / 商品 / 购物车 / 订单页面
 |-- 历史会话、结果卡片、反馈与仪表盘
 |
 v
FastAPI API 层
 |
 |-- Auth / Users
 |-- Chat / Runtime
 |-- Travel / Restaurant / Diet
 |-- Commerce / Feedback / Route
 |
 v
应用服务层
 |
 |-- ChatOrchestrator        对话编排
 |-- ConversationService     会话持久化
 |-- ArtifactService         业务结果同步
 |-- ContextBuilder          上下文构建
 |-- RuntimeService          任务和事件记录
 |-- PreferenceLearner       用户偏好沉淀
 |
 v
智能体层
 |
 |-- Supervisor              意图识别与调度
 |-- Dispatcher              统一派发
 |-- TravelAgent             行程规划
 |-- RestaurantAgent         餐厅推荐
 |-- DietAgent               饮食健康
 |-- CommerceAgent           商品、购物车、订单
 |-- CrossDomain             跨领域结果整合
 |
 v
数据与外部能力
 |
 |-- SQLite / PostgreSQL     业务数据持久化
 |-- Redis                   缓存和限流基础
 |-- DeepSeek/OpenAI 兼容 API AI 推理
 |-- AMap                    地图与路线
 |-- QWeather                天气能力
```

## 后端架构说明

后端采用 FastAPI + SQLAlchemy Async ORM，按 API 层、服务层、智能体层、模型层拆分。

- `api/`：提供 HTTP 接口，只负责请求校验、鉴权入口和响应组织。
- `services/`：承载应用业务流程，例如对话编排、会话持久化、任务运行记录、业务结果同步。
- `agents/`：承载 AI 领域智能体，包括意图分类、统一调度和领域处理。
- `models/`：定义数据库 ORM 实体。
- `schemas/`：定义 Pydantic 请求和响应模型。
- `core/`：配置、数据库、安全、日志、Redis 等基础能力。
- `middleware/`：限流等横切能力。

这种分层避免 API 路由直接堆业务逻辑，也避免智能体直接操作所有系统资源，使后续替换模型、扩展领域、增加异步任务队列和观测能力更容易。

## 前端架构说明

前端采用 Next.js 14 App Router + React + TypeScript + Tailwind CSS。

- `app/`：页面路由，包括首页、AI 对话、行程、餐厅、饮食、商品、购物车、仪表盘、个人中心和设置。
- `components/`：复用组件和业务组件，例如聊天输入、消息列表、结果卡片、历史面板、商品卡片、餐厅卡片、Toast、导航栏等。
- `lib/api.ts`：统一 API 客户端，封装鉴权、请求和错误处理。
- `lib/session.ts`：管理当前 AI 会话 ID，使业务页面可以携带上下文。
- `lib/types.ts`：前端共享类型定义。

前端重点不是展示静态结果，而是把 AI 输出转成可操作界面：行程卡片可查看和确认，商品可加入购物车，历史对话可恢复，失效会话会自动清理。

## 代码结构

```text
AIGCTP/
|-- backend/
|   |-- app/
|   |   |-- agents/        # Supervisor、Dispatcher 和各领域智能体
|   |   |-- api/           # FastAPI 路由
|   |   |-- core/          # 配置、数据库、安全、日志、Redis
|   |   |-- middleware/    # 限流等中间件
|   |   |-- models/        # SQLAlchemy ORM 模型
|   |   |-- schemas/       # Pydantic Schema
|   |   `-- services/      # 应用服务层和运行时能力
|   |-- tests/             # 后端单元测试和 API 测试
|   |-- requirements.txt
|   `-- run.py
|-- frontend/
|   |-- app/               # Next.js 页面
|   |-- components/        # 前端组件
|   |-- lib/               # API 客户端、会话工具、类型
|   |-- package.json
|   `-- tailwind.config.ts
|-- docker-compose.yml
|-- start.sh
|-- .env.example
`-- README.md
```

## 技术栈

### 前端

- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Server-Sent Events
- PWA/离线页面基础

### 后端

- FastAPI
- SQLAlchemy Async ORM
- Pydantic
- JWT
- Redis
- SQLite 开发模式
- PostgreSQL 兼容部署
- Pytest

### AI 与外部服务

- OpenAI 兼容 SDK
- DeepSeek 兼容模型接口
- AMap 地图 API
- QWeather 天气 API

## 快速启动

### 1. 配置环境变量

复制 `.env.example` 为 `.env`，并填写必要配置。

```env
DATABASE_URL=sqlite+aiosqlite:///./life_recommender.db
LLM_API_KEY=your_api_key
LLM_API_BASE=https://api.deepseek.com
LLM_MODEL=deepseek-chat
AMAP_API_KEY=your_amap_key
QWEATHER_API_KEY=your_qweather_key
JWT_SECRET=replace_with_a_strong_secret
DEBUG=true
```

### 2. 启动后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

后端默认地址：

- `http://localhost:8000`
- `http://localhost:8000/docs`
- `http://localhost:8000/health`

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：

- `http://localhost:3000`

## 测试

后端测试：

```bash
cd backend
pytest
```

前端类型检查：

```bash
cd frontend
npx tsc --noEmit
```

## 适用场景

- AI 多智能体系统课程项目。
- 毕业设计或工程实践项目。
- 全栈 AI 应用作品集。
- 生活服务推荐系统原型。
- 研究跨领域推荐、上下文记忆、智能体编排和人机协同决策的基础项目。

## 后续演进方向

- 引入任务队列，将长耗时 AI 工作流异步化。
- 使用 PostgreSQL + Redis 部署生产环境。
- 增加 OpenTelemetry、结构化日志和指标监控。
- 强化推荐质量评估、用户反馈闭环和 A/B 测试。
- 增加更细粒度的权限、审计和数据隔离。
- 将领域智能体插件化，使新场景可以低成本接入。
- 为关键业务流程补充端到端测试和浏览器自动化测试。

## 项目价值

AIGCTP 展示的是一个从“AI 对话”走向“AI 可执行系统”的完整工程路径。它将自然语言理解、多领域智能体、结构化业务结果、用户状态、运行时任务和前端交互统一到一个系统中，为构建更可用、更可扩展、更接近真实业务的 AI 应用提供了基础。

## License

当前项目尚未声明开源许可证。如需正式开源，建议补充明确的 License 文件。
