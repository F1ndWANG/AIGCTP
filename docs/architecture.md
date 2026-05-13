# AIGCTP 项目架构文档

> AI Life Recommender — 多智能体 AI 生活服务平台
> FastAPI + Next.js 14 + DeepSeek + PostgreSQL + Redis

---

## 目录

1. [项目概览](#1-项目概览)
2. [顶层结构](#2-顶层结构)
3. [后端架构](#3-后端架构)
4. [前端架构](#4-前端架构)
5. [请求数据流](#5-请求数据流)
6. [多智能体系统](#6-多智能体系统)
7. [认证体系](#7-认证体系)
8. [关键集成](#8-关键集成)
9. [任务与事件系统](#9-任务与事件系统)
10. [可观测性](#10-可观测性)
11. [测试与CI](#11-测试与ci)
12. [当前架构评估与改进记录](#12-当前架构评估与改进记录)

---

## 1. 项目概览

AIGCTP 是一个面向终端用户的多智能体 AI 生活服务平台，集成旅行规划、饮食管理、商品推荐、餐厅推荐、路线导航等功能。系统采用**前后端分离**架构，后端为 Python FastAPI 服务，前端为 Next.js 14 React 应用。

**核心能力**：

- 旅行行程规划与调整（支持 POI 排除/替换/预算控制）
- 饮食计划生成、饮食记录与营养分析
- 电商商品推荐、一键加购与快速复购
- 餐厅推荐与附近搜索（Amap → LLM 排序）
- 路线规划与导航
- 多轮对话 + 流式 SSE 响应
- 全域混合推荐系统（行为采集、画像、召回、排序、解释）
- 游记分享与互动社区
- 后台异步任务队列（arq）
- PWA 离线操作队列

---

## 2. 顶层结构

```
E:\AIGCTP/
├── backend/                    # Python FastAPI 后端
│   ├── app/                    # 应用代码
│   ├── alembic/                # 数据库迁移 (5 版本)
│   ├── tests/                  # 测试套件 (240 passed + 10 PostgreSQL integration skipped)
│   ├── run.py                  # Uvicorn 入口
│   ├── run_worker.py           # arq worker 入口
│   └── seed_data.py            # 数据播种
├── frontend/                   # Next.js 14 前端
│   ├── app/                    # App Router 页面
│   ├── components/             # React 组件
│   └── lib/                    # API 客户端 / 工具库
├── k8s/                        # Kubernetes 部署清单
├── nginx/                      # Nginx 反向代理配置
├── monitoring/                 # Prometheus + Grafana 监控
├── loadtest/                   # k6 负载测试脚本
├── .github/                    # GitHub Actions CI/CD
├── docs/                       # 文档
├── docker-compose.yml          # 开发环境编排
├── docker-compose.prod.yml     # 生产环境编排
├── docker-compose.e2e.yml      # 端到端测试编排
└── start.sh                    # 开发启动脚本
```

---

## 3. 后端架构

### 3.1 目录结构

```
backend/app/
├── main.py                 # 应用入口 (工厂模式 + 中间件注册)
├── jobs.py                 # arq 后台任务定义
├── seed_data.py            # 演示数据播种
│
├── core/                   # 基础设施层
│   ├── config.py           # 配置管理 (Pydantic Settings + 生产校验)
│   ├── database.py         # SQLAlchemy async engine + _utcnow()
│   ├── redis.py            # Redis 客户端 (优雅降级 + TOCTOU防护)
│   ├── security.py         # JWT 签发/解码/黑名单 + bcrypt
│   ├── cache.py            # Redis 类型化缓存操作
│   ├── metrics.py          # Prometheus 指标
│   ├── logging.py          # 结构化 JSON 日志
│   └── error_codes.py      # 标准化错误码
│
├── api/                    # HTTP 路由层
│   ├── deps.py             # 认证依赖注入 (cookie + header 双来源)
│   ├── auth.py             # 注册/登录/刷新/登出/me (httpOnly cookie)
│   ├── chat.py             # 对话 (同步 + SSE 流式)
│   ├── travel.py           # 旅行 CRUD
│   ├── diet.py             # 饮食 CRUD
│   ├── commerce.py         # 商品/购物车/订单
│   ├── restaurant.py       # 餐厅推荐
│   ├── recommendation.py   # 全域推荐 feed / 埋点 / 反馈 / 画像
│   ├── share.py            # 游记分享 / 点赞 / 收藏 / 评论
│   ├── route.py            # 路线规划
│   ├── feedback.py         # 反馈与统计
│   └── runtime.py          # 任务/事件查询
│
├── agents/                 # 多智能体系统
│   ├── supervisor.py       # 总调度入口 + 意图路由
│   ├── dispatcher.py       # 意图分发
│   ├── travel_agent.py     # 旅行规划/调整
│   ├── diet_agent.py       # 饮食推荐/记录/分析
│   ├── restaurant_agent.py # 餐厅推荐
│   ├── commerce_agent.py   # 商品推荐/加购/复购
│   ├── cross_domain.py     # 跨域组合 (旅行+商品)
│   ├── prompt_builder.py   # LLM 提示词工厂
│   ├── domain_results.py   # 类型化结果定义
│   ├── result.py           # AgentResult 归一化
│   └── tools/
│       ├── poi_tools.py    # POI/餐厅/酒店搜索 (三级缓存)
│       └── weather_tools.py# 天气 (API + 确定性季节降级)
│
├── services/               # 业务逻辑层
│   ├── chat_orchestrator.py # 对话编排 (单次 db.commit)
│   ├── llm.py              # LLM 服务 (断路器+重试+降级+缓存)
│   ├── intent_classifier.py # 意图分类 (关键词22+模式 + LLM)
│   ├── amap.py             # 高德地图 API
│   ├── weather.py          # 和风天气 API
│   ├── runtime.py          # TaskRun/DomainEvent 服务
│   ├── preference_learner.py # 用户偏好学习
│   ├── artifact_service.py # 结果持久化
│   ├── conversation_service.py # 会话管理
│   ├── context_builder.py  # 上下文构建
│   ├── progress.py         # Agent 进度报告
│   ├── truncation.py       # 消息截断
│   ├── share_service.py    # 游记分享、评论、互动编排
│   ├── product_images.py   # 商品图片 URL / 本地生成兜底
│   ├── recommendation/     # 推荐系统 V1
│   │   ├── events.py       # 行为事件写入
│   │   ├── profile.py      # 用户画像构建
│   │   ├── embeddings.py   # 文本表示和向量/关键词相似度
│   │   ├── candidate.py    # 多路候选召回
│   │   ├── ranker.py       # 混合排序和 MMR 重排
│   │   ├── explain.py      # 推荐解释
│   │   └── service.py      # 推荐系统门面服务
│   └── demo_catalog.py     # 演示商品目录
│
├── models/                 # SQLAlchemy ORM 模型
│   ├── user.py             # 用户 + 偏好
│   ├── conversation.py     # 对话
│   ├── travel.py           # 旅行计划
│   ├── diet.py             # 健康/饮食 (含 HealthProfile/MealRecord/DietPlan)
│   ├── commerce.py         # 商品/购物车/订单 (含 Category/Product/Cart/Order)
│   ├── restaurant.py       # 餐厅推荐
│   ├── feedback.py         # 推荐日志
│   ├── recommendation.py   # 推荐事件 / 向量 / 推荐日志
│   ├── share.py            # 游记 / 评论 / 互动
│   ├── runtime.py          # TaskRun + DomainEvent
│   └── cache.py            # POI 缓存
│
├── middleware/
│   ├── rate_limit.py       # Redis 限流 (按端点分级)
│   ├── security_headers.py # 安全头 (CSP/XSS/Frame)
│   └── request_size.py     # 请求体大小限制 (1MB)
│
└── schemas/                # Pydantic 请求/响应模型
```

### 3.2 中间件栈 (注册顺序 = 执行顺序)

```
CORSMiddleware
  → RequestSizeLimitMiddleware (Content-Length > 1MB → 413)
    → RateLimitMiddleware (auth:5/min, chat:30/min, 默认:60/min)
      → SecurityHeadersMiddleware (CSP/X-Frame-Options/Permissions-Policy)
        → MetricsMiddleware (Prometheus HTTP 指标)
          → request_id_middleware (X-Request-ID 注入)
```

### 3.3 路由注册

所有路由注册在 `app/main.py`，统一前缀 `/api/v1`：

| 前缀 | 标签 | 功能 |
|------|------|------|
| `/api/v1/auth` | auth | 注册/登录/刷新/登出/me |
| `/api/v1/users` | users | 用户信息与偏好 |
| `/api/v1/chat` | chat | 对话 (同步 + SSE 流式) |
| `/api/v1/travel` | travel | 旅行计划 CRUD |
| `/api/v1/diet` | diet | 健康档案/饮食记录/计划 |
| `/api/v1/commerce` | commerce | 商品/分类/购物车/订单 |
| `/api/v1/restaurant` | restaurant | 餐厅推荐 |
| `/api/v1/recommend` | recommendation | 推荐 feed、事件埋点、反馈、画像 |
| `/api/v1/shares` | share | 游记发布、列表、详情、互动 |
| `/api/v1/route` | route | 路线规划 |
| `/api/v1/feedback` | feedback | 反馈提交与统计 |
| `/api/v1/runtime` | runtime | 任务/事件查询与重试 |

健康检查端点：

| 端点 | 用途 |
|------|------|
| `GET /health` | 存活检查 |
| `GET /api/v1/health/ready` | 就绪检查 (DB SELECT 1 + Redis ping) |
| `GET /api/v1/health/llm` | DeepSeek 连通性检查 |

### 3.4 数据库模型 (17 张表)

```
users                    # 用户账户
  └── user_preferences   # 用户偏好 (键值对)

conversations            # 对话记录 (JSON 消息列表)

travel_plans             # 旅行计划 (JSONB 行程)

health_profiles          # 健康档案
meal_records             # 饮食记录 (含时区支持)
diet_plans               # 饮食计划

categories               # 商品分类
products                 # 商品
carts                    # 购物车
  └── cart_items         # 购物车项
orders                   # 订单

restaurant_recommendations  # 餐厅推荐 (回复支持5000字符)

recommendation_logs     # 推荐反馈日志
recommendation_events   # 推荐行为事件
recommendation_embeddings # 商品/餐厅/行程等 item 表示

travel_notes            # 用户公开游记
travel_note_comments    # 游记评论
travel_note_interactions # 点赞/收藏等互动

cached_pois             # POI 缓存 (Redis → DB → API 三级)

task_runs               # 任务执行记录 (含重试/错误追踪)
domain_events           # 领域事件 (审计日志, 追加写)
```

所有时间戳字段统一使用 `DateTime(timezone=True)` + 集中式 `_utcnow()`（定义于 `core/database.py`，导入到所有模型）。

### 3.5 核心配置

`app/core/config.py` 使用 Pydantic Settings 从 `.env` 加载：

```python
# 数据库
DATABASE_URL              # postgresql+asyncpg://user:pass@host:5432/dbname

# Redis (缓存/限流/黑名单/任务队列)
REDIS_URL                 # redis://localhost:6379/0
REDIS_TTL_LLM_CHAT: 3600  # LLM 响应缓存 TTL
REDIS_TTL_POI: 3600       # POI 缓存 TTL
REDIS_TTL_RESTAURANT: 1800 # 餐厅缓存 TTL

# LLM
LLM_API_KEY               # DeepSeek API Key
LLM_API_BASE              # https://api.deepseek.com
LLM_MODEL                 # deepseek-v4-flash
LLM_FALLBACK_MODEL        # 可选降级模型

# JWT
JWT_SECRET                # 签名密钥 (生产环境强制 ≥32字符)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: 15  # 短生命周期
JWT_REFRESH_TOKEN_EXPIRE_DAYS: 30

# Cookie
COOKIE_SECURE: False      # 生产环境 True (HTTPS)
COOKIE_SAMESITE: "lax"    # 或 "strict"

# 安全
PASSWORD_MIN_LENGTH: 8
LOGIN_MAX_ATTEMPTS: 5     # 登录重试锁定
LOGIN_LOCKOUT_MINUTES: 15
MAX_REQUEST_BODY_SIZE: 1_048_576  # 1MB

# 外部 API
AMAP_API_KEY              # 高德地图 Web API
QWEATHER_API_KEY          # 和风天气 API
```

生产环境启动自动校验：检测空值/占位符密钥、默认 JWT Secret、DEBUG 模式，不符合则拒绝启动。

---

## 4. 前端架构

### 4.1 目录结构

```
frontend/
├── app/                           # Next.js App Router
│   ├── layout.tsx                 # 根布局 (Provider 链)
│   ├── page.tsx                   # 首页 (登录/注册 + 仪表盘)
│   ├── chat/page.tsx              # 核心聊天界面
│   ├── cart/page.tsx              # 购物车
│   ├── diet/page.tsx              # 饮食管理
│   ├── plans/page.tsx             # 计划列表
│   ├── products/page.tsx          # 商品浏览
│   ├── restaurants/page.tsx       # 餐厅
│   ├── shares/page.tsx            # 游记社区列表
│   ├── shares/[id]/page.tsx       # 游记详情
│   └── settings/page.tsx          # 设置
├── components/
│   ├── Chat/                      # 聊天组件集
│   │   ├── ChatInput.tsx
│   │   ├── MessageList.tsx
│   │   ├── ChatResultCards.tsx
│   │   └── HistoryPanels.tsx
│   ├── Commerce/                  # 电商组件
│   ├── Diet/                      # 饮食组件
│   ├── TravelPlan/                # 旅行组件
│   ├── Restaurant/                # 餐厅组件
│   ├── Layout/                    # 布局组件
│   │   ├── AuthProvider.tsx       # 认证上下文 (含卸载保护)
│   │   └── NavBar.tsx
│   ├── Home/
│   │   ├── PersonalDashboard.tsx  # 个人仪表盘
│   │   ├── RecommendationInsights.tsx # 首页推荐 feed / 画像面板
│   │   └── DietReminder.tsx       # 每日饮食提醒
│   └── UI/                        # 通用 UI 组件
│       ├── Toast.tsx
│       ├── NotificationCenter.tsx
│       ├── ErrorBoundary.tsx
│       └── OfflineIndicator.tsx   # PWA 离线指示器
├── lib/
│   ├── api.ts                     # API 客户端 (核心)
│   ├── api-client.ts              # HTTP request / ApiError / auth refresh 基础设施
│   ├── api-clients/               # 分域 API client
│   │   ├── auth.ts                # 登录/注册/登出
│   │   ├── chat.ts                # 普通聊天请求 / SSE 流式聊天
│   │   ├── commerce.ts            # 商品/购物车/订单
│   │   ├── diet.ts                # 饮食档案/记录/计划
│   │   ├── feedback.ts            # 用户反馈
│   │   ├── recommendation.ts      # 推荐 feed / 埋点 / 反馈
│   │   ├── restaurant.ts          # 餐厅推荐
│   │   ├── travel.ts              # 行程和路线
│   │   ├── shares.ts              # 游记分享 API
│   │   └── user.ts                # 用户资料和偏好
│   ├── types.ts                   # TypeScript 类型定义
│   ├── offline-queue.ts           # IndexedDB 离线队列 (含 onerror)
│   ├── useRecommendationTracking.ts # 推荐埋点 hook
│   └── useOnlineStatus.ts         # 在线状态 hook
├── middleware.ts                  # 路由保护 (cookie 检查)
└── next.config.js                 # API 代理重写
```

### 4.2 Provider 链

```
ToastProvider
  └── AuthProvider (httpOnly Cookie 认证, 组件卸载保护)
       └── NotificationProvider
            └── OfflineIndicator (离线/队列横幅)
                 └── NavBar
                      └── DietReminder (每日提醒)
                           └── ErrorBoundary
                                └── children (页面内容)
```

### 4.3 API 客户端

前端 API 层采用“基础设施 + 分域 client + 兼容聚合导出”：

- `lib/api-client.ts`：封装 `request<T>()`、`ApiError`、`checkAuth()`、access token 刷新和通用超时/重试策略。
- `lib/api-clients/*`：承载 auth、chat、travel、diet、restaurant、commerce、recommendation、shares、user、feedback 等按领域拆分的客户端。
- `lib/api.ts`：作为兼容聚合出口，继续导出 `auth`、`chat`、`travel`、`commerce`、`recommendation`、`shares` 等对象，避免页面层出现大规模 import 迁移。

`request<T>()` 的基础能力：

- **认证**: 全部请求使用 `credentials: "include"`，无 localStorage token 管理
- **请求封装**: `request<T>()` — 自动带 cookie、30s 超时（AbortController）、指数退避重试（带抖动）+ 401 自动刷新
- **SSE 流式**: `chat.sendStream()` — 解析 `ReadableStream`、支持 9 种事件类型、自动重连（3 次 + 抖动）
- **Token 刷新**: 通过 `POST /api/auth/refresh`（cookie）自动完成，互斥锁防止并发刷新
- **错误处理**: `ApiError` 类 + 分级（retryable / auth_expired）

推荐埋点统一通过 `lib/useRecommendationTracking.ts`：

- 页面层只声明 `source` 和可选 `sessionId`。
- hook 内部统一补全 `source`、`session_id` 和上下文，并吞掉埋点失败，避免影响主流程。
- 首页推荐曝光、商品点击/加购、餐厅曝光/选择都通过同一入口写入推荐事件或反馈。

### 4.4 API 代理

`next.config.js` 将前端请求代理到后端：

```
/api/:path*          → http://localhost:8000/api/v1/:path*
/health/:path*       → http://localhost:8000/health/:path*
```

### 4.5 路由保护

`middleware.ts` 检查 `access_token` cookie，保护以下页面：

```
/chat  /plans  /products  /cart  /diet
/restaurants  /profile  /settings  /dashboard
```

未登录用户自动重定向到首页（含 `?redirect=` 参数）。

---

## 5. 请求数据流

### 5.1 聊天消息端到端流程

```
用户输入 → ChatInput
  → chatApi.sendStream()           # SSE 流式连接
    → next.config.js rewrite       # /api/* → backend
      → chat.py:chat_stream()      # cookie → JWT → StreamingResponse
        → chat_orchestrator:stream_chat_events()
            │
            ├─ ① 创建 TaskRun (status: running)
            ├─ ② 加载/创建 Conversation
            │   ├─ 按 session_id + user_id 查询
            │   ├─ 合并用户偏好与画像
            │   └─ 加载旅行计划上下文
            ├─ ③ 追加用户消息 + 截断 (>3000 tokens → 摘要)
            │
            └─ ④ Agent 循环
                └─ supervisor.run_agent_stream()
                    ├─ intent_classifier.classify()
                    │   ├─ 关键词快速路径 (22+ 中文模式)
                    │   └─ LLM 语义分类 (6s 超时, 降级 general_chat)
                    └─ dispatcher.dispatch()
                        └─ travel / diet / restaurant / commerce / cross_domain

    ← ⑤ SSE 事件流 (type: thinking / token / result / plan / products / ...)
            │
            └─ ⑥ 后处理 (单次 db.commit)
                ├─ 保存 Agent 结果到 DB (旅行计划/餐厅推荐/...)
                ├─ 发射 DomainEvent (审计日志)
                ├─ 更新 TaskRun → succeeded/failed
                ├─ 同步 artifacts → conversation context
                └─ 提取偏好 → User.preferences
```

### 5.2 SSE 事件类型

| 类型 | 触发时机 | 前端处理 |
|------|----------|----------|
| `thinking` | Agent 处理中 / 进度更新 | 显示 "正在分析..." 指示器 |
| `token` | LLM 流式输出 | 追加到消息气泡 |
| `result` | Agent 生成结果 | 替换消息气泡 |
| `plan` | 旅行计划生成/更新 | 更新旅行卡片 |
| `products` | 商品推荐 | 显示商品卡片 |
| `restaurants` | 餐厅推荐 | 显示餐厅卡片 |
| `diet_plan` | 饮食计划 | 显示饮食卡片 |
| `cart_items` | 加购操作 | 更新购物车徽标 |
| `done` | 全部完成 | 停止加载 |

### 5.3 非聊天请求 (标准 REST)

```
前端 → request<T>() → fetch (credentials: include)
  → next.config.js rewrite
    → API handler (JWT auth → 业务逻辑 → DB query)
      ← JSON 响应 (含 X-Request-ID / X-RateLimit-* 头)
```

### 5.4 后台任务流程

```
HTTP 请求 → chat.py:enqueue_background()
  → 创建 TaskRun (status: running)
  → arq.enqueue_job("background_chat_job", ...)
  ← 立即返回 {session_id, task_id, status: "pending"}

客户端轮询 GET /api/v1/runtime/tasks/{task_id}

arq Worker:
  → 打开独立 DB session
  → 执行 handle_chat()
  → 更新 TaskRun → succeeded/failed
  ← 返回结果 dict
```

---

## 6. 多智能体系统

### 6.1 架构

```
Supervisor (run_agent_stream)
  │
  ├── IntentClassifier (两阶段)
  │   ├── 关键词快速路径 (22+ 中文模式, 无 LLM 调用)
  │   │   → 10 种意图: travel_plan, travel_adjust, diet_recommend,
  │   │               diet_log, diet_analyze, restaurant_recommend,
  │   │               commerce_recommend, auto_cart, quick_reorder, route_query
  │   └── LLM 语义分类 (关键词置信度 <0.7 时触发, 6s 超时 → general_chat)
  │
  └── AgentDispatcher
      ├── TravelAgent
      │   ├── plan_trip()          → Amap POI + QWeather + DeepSeek 行程
      │   └── adjust_plan()        → 排除/请求 POI 处理 + LLM 重规划
      ├── DietAgent
      │   ├── recommend_diet()     → LLM 推荐 + 可选计划
      │   ├── log_meal()           → NLP → MealRecord
      │   └── analyze_nutrition()  → 近期记录汇总 → LLM 分析
      ├── RestaurantAgent
      │   ├── recommend_restaurants() → Amap → LLM 排序
      │   └── recommend_nearby()      → 位置搜索 → LLM 排序
      ├── CommerceAgent
      │   ├── commerce_recommend() → LLM → DB 搜索 → 排序
      │   ├── auto_cart()          → NLP → 购物车操作
      │   └── quick_reorder()      → 最近订单 → 购物车
      ├── CrossDomainComposer
      │   └── merge()              → 旅行 + 商品联动推荐
      └── GeneralChat (直接 LLM 调用)
```

### 6.2 意图分类器

`services/intent_classifier.py` 使用两阶段分类：

**第一阶段 — 关键词快速路径**：

| 意图 | 示例触发词 | 置信度 |
|------|-----------|--------|
| `travel_plan` | 去/旅游/玩/trip/行程 | 0.85-0.9 |
| `travel_adjust` | 换/改/加/去掉/不要/太赶 | 0.85 |
| `diet_recommend` | 减肥/增肌/饮食计划/食谱 | 0.75-0.8 |
| `diet_log` | 吃了/早餐/午餐/晚餐 | 0.75 |
| `diet_analyze` | 分析我的饮食 | 0.85 |
| `restaurant_recommend` | 餐厅/好吃的/推荐菜/附近 | 0.8-0.85 |
| `commerce_recommend` | 买/推荐/商城/装备 | 0.8-0.9 |
| `auto_cart` | 加购/加入购物车 | 0.85-0.95 |
| `quick_reorder` | 再买/复购/重新订购 | 0.8-0.95 |
| `route_query` | 怎么去/路线/导航 | 0.85 |

**第二阶段 — LLM 语义分类**：当关键词置信度 <0.7 时，调用 DeepSeek 分类（6 秒超时，超时降级为 `general_chat`）。支持复合意图检测（如旅行+餐厅）。

### 6.3 Agent 工具

**POI 工具** (`agents/tools/poi_tools.py`) — 三级缓存架构：

```
Redis 缓存 (TTL: 3600s, 可配置)
  └── CachedPOI 表 (持久化)
       └── Amap API (实时查询)
```

支持 `search_scenic_spots`、`search_restaurants`、`search_hotels`，后两者新增 Redis 缓存。

**天气工具** (`agents/tools/weather_tools.py`)：

- 首选：和风天气 API
- 降级：确定性季节数据（基于月份 + 城市种子，免 API 调用）

### 6.4 结果类型

所有 Agent 返回类型化结果，统一通过 `AgentResult` 归一化：

```python
@dataclass
class AgentResult:
    response: str                    # 自然语言回复
    travel_plan: dict | None         # 旅行计划 artifact
    products: list[dict] | None      # 商品列表
    restaurants: list[dict] | None   # 餐厅列表
    diet_plan: dict | None           # 饮食计划
    cart_items: list[dict] | None    # 购物车项
    artifacts: dict | None           # 通用扩展
```

---

## 7. 认证体系

### 7.1 Token 方案

采用双 Token JWT + httpOnly Cookie 方案（不依赖 localStorage）：

| Token | 有效期 | Cookie | 路径 |
|-------|--------|--------|------|
| Access Token | 15 分钟 | httpOnly, SameSite=Lax | `/api` |
| Refresh Token | 30 天 | httpOnly, SameSite=Lax | `/api/v1/auth` |

Token 载荷包含 `jti`（UUID）用于黑名单检测。

### 7.2 端点

| 端点 | 功能 |
|------|------|
| `POST /api/v1/auth/register` | 注册 (返回 token + 设置 cookie) |
| `POST /api/v1/auth/login` | 登录 (5 次失败 → 15 分钟锁定) |
| `POST /api/v1/auth/refresh` | 刷新令牌对 (旧 refresh 加入黑名单 → 令牌旋转) |
| `POST /api/v1/auth/logout` | 登出 (access + refresh jti 加入黑名单, 清除 cookie) |
| `GET /api/v1/auth/me` | 获取当前用户 (从 cookie/header 自动检测) |

### 7.3 认证流程

```
请求 → Cookie: access_token=xxx / Authorization: Bearer xxx
  → deps.py:get_current_user()
     ├─ 候选来源: cookie → header (任一有效即可, 非阻塞)
     ├─ 提取 jti → 检查 Redis 黑名单
     ├─ 解码验证 Access Token (HS256)
     ├─ 查询 User 表 (user_id)
     └─ 返回 User 或 401

401 处理 (前端):
  → POST /api/auth/refresh (cookie 自动带 refresh_token)
  → 成功: 后台自动设置新 cookie, 重试原请求
  → 失败: 跳转登录页
```

### 7.4 安全机制

- 登录锁定: 5 次失败 → 15 分钟 Redis 锁定
- 令牌旋转: 每次 refresh 将旧 refresh 加入黑名单
- 生产环境校验: JWT_SECRET ≥32 字符, API key 非占位符, DEBUG=False
- 请求体限制: 1MB (nginx + FastAPI 双重检查)
- 安全响应头: CSP、X-Content-Type-Options、X-Frame-Options、Permissions-Policy

---

## 8. 关键集成

| 系统 | 用途 | 容错机制 |
|------|------|----------|
| **DeepSeek** | 核心 LLM | 断路器 (5 次失败 → 30s 开放 → 半开) + 指数退避重试 (仅耗尽后计失败) + 降级模型 + MD5 缓存(1h) |
| **PostgreSQL** | 主数据库 | 连接池 (10+10) + pool_pre_ping + 慢查询日志 (>0.5s) |
| **Redis** | 缓存/限流/黑名单/队列 | 优雅降级 (失败返回 None, 30s 自动重连) + TOCTOU 防护 |
| **高德地图** | POI 搜索/路线/编码 | 三级缓存: Redis → CachedPOI 表 → API |
| **和风天气** | 天气预报 | 确定性季节降级 (无 API 也正常返回) |

---

## 9. 任务与事件系统

### 9.1 TaskRun

用于跟踪可恢复的工作流执行：

```python
class TaskRun(Base):
    task_id: str        # UUID, 唯一
    user_id, session_id # 归属
    task_type: str      # chat / chat_stream / travel_plan_background / chat_background
    status: str         # running → succeeded / failed / retrying
    input: dict         # 输入载荷
    result: dict        # 输出结果
    error: str          # 错误信息 (2000字)
    retry_count: int    # 重试计数
    max_retries: int    # 最大重试
    started_at: datetime
    finished_at: datetime
```

### 9.2 DomainEvent

用于审计日志和异步集成（追加写，不可变）：

```python
class DomainEvent(Base):
    event_id: str                        # UUID, 唯一
    event_type: str                      # chat.completed / travel_plan.saved / ...
    aggregate_type: str                  # 聚合类型
    aggregate_id: str                    # 聚合 ID
    payload: dict                        # 事件数据
    created_at: datetime                 # 事件时间
```

### 9.3 事件类型

| 事件类型 | 触发场景 |
|----------|----------|
| `chat.completed` | 每次对话完成 |
| `travel_plan.saved` | 旅行计划保存 |
| `restaurant_recommendation.saved` | 餐厅推荐保存 |
| `commerce.products_recommended` | 商品推荐 |
| `commerce.cart_items_added` | 加购操作 |
| `diet.plan_generated` | 饮食计划生成 |

### 9.4 后台任务 (arq)

```python
# jobs.py — 每个任务打开独立 DB session
async def plan_trip_job(ctx, user_id, ...)      # 旅行计划 (后台)
async def generate_diet_plan_job(ctx, user_id, ...)  # 饮食计划 (后台)
async def background_chat_job(ctx, *, user_id, ...)  # 全流程对话 (后台)
```

客户端轮询 `GET /api/v1/runtime/tasks/{task_id}` 获取结果。

---

## 10. 可观测性

### 10.1 结构化日志

```json
{
  "timestamp": "2026-05-09T12:00:00Z",
  "level": "INFO",
  "logger": "app.services.chat_orchestrator",
  "message": "Chat completed",
  "request_id": "req-abc123",
  "user_id": 1,
  "session_id": "sess-xyz"
}
```

### 10.2 Prometheus 指标

| 指标 | 类型 | 标签 |
|------|------|------|
| `http_requests_total` | Counter | method, endpoint, status |
| `http_request_duration_seconds` | Histogram | method, endpoint |
| `llm_calls_total` | Counter | method (chat/chat_stream/extract_json), status |
| `llm_call_duration_seconds` | Histogram | method |
| `llm_cache_hits_total` / `llm_cache_misses_total` | Counter | — |
| `circuit_breaker_state` | Gauge | model (0=closed, 0.5=half-open, 1=open) |
| `active_sessions` | Gauge | — |

### 10.3 健康检查

| 端点 | 检查内容 |
|------|----------|
| `GET /health` | 进程存活 |
| `GET /api/v1/health/ready` | DB (SELECT 1) + Redis ping |
| `GET /api/v1/health/llm` | DeepSeek 连通性 (ping 调用, 5s 超时) |

### 10.4 错误码体系

`core/error_codes.py` 定义了标准化错误码：

| 错误码 | HTTP 状态 | 用户提示 |
|--------|-----------|----------|
| `ERR_LLM_UNAVAILABLE` | 503 | AI 服务繁忙，请稍后重试 |
| `ERR_RATE_LIMITED` | 429 | 请求太频繁，请 {retry_after} 秒后重试 |
| `ERR_AUTH_EXPIRED` | 401 | 登录已过期，请重新登录 |
| `ERR_DB_ERROR` | 500 | 系统错误，已记录 |
| `ERR_BODY_TOO_LARGE` | 413 | 请求体超过限制 |

---

## 11. 测试与CI

### 11.1 测试套件

| 测试类型 | 当前结果 | 数据库 |
|----------|------|--------|
| 单元/API/服务测试 | 240 passed | SQLite (内存) + mock |
| PostgreSQL 集成测试 | 10 skipped | 需要 `DATABASE_URL` 指向 PostgreSQL |
| Playwright E2E | 19 passed | 后端 venv + 前端 dev server |

测试覆盖：
- API 认证流程 (注册/登录/刷新/登出/cookie)
- 6 个 Agent (意图分类/路由/失败降级)
- Prompt 构建工具
- 跨域组合
- DB 集成 (CRUD/时区/连接池)
- 首页、认证、聊天、导航等关键前端路径

### 11.2 端到端测试运行约定

`frontend/playwright.config.ts` 启动两个本地服务：

- 后端：优先使用 `backend/venv/Scripts/python.exe -m uvicorn`，避免误用全局 Python 环境导致依赖缺失。
- 前端：使用 `npm run dev` 启动 Next.js。

Playwright 本地默认使用本机 Chrome channel，这样本地测试不依赖 Playwright 下载浏览器。CI 默认不指定 channel，使用 Playwright 镜像/安装步骤提供的浏览器；如需覆盖，可设置 `PLAYWRIGHT_CHANNEL`。

本地 webServer 日志默认隐藏，以避免 Next dev server 在关闭连接时打印 `ECONNRESET / Error: aborted` 噪声。需要排查启动问题时设置 `PLAYWRIGHT_SHOW_WEBSERVER_LOGS=1`。

认证测试有两条隔离规则：

- `auth.setup.ts` 只负责准备稳定登录态，注册成功状态码按后端当前语义使用 `201 Created`。
- `auth.spec.ts` 显式使用空 `storageState`，并通过独立 `request.newContext()` 创建测试用户，避免 API 请求污染页面 cookie。

### 11.3 CI/CD (GitHub Actions)

4 个并行 job：

| Job | 触发条件 | 内容 |
|-----|----------|------|
| `backend-lint` | push/PR | ruff check app/ tests/ |
| `backend-test` | push/PR | PostgreSQL 16 service + pytest |
| `frontend-build` | push/PR | npm ci + npm run build |
| `loadtest-smoke` | 所有测试通过后 | Docker Compose + k6 1VU 烟雾测试 |

### 11.4 PWA 离线能力

- **IndexedDB 离线队列** (`offline-queue.ts`): 网络不可用时入队操作，在线后自动重放
- **在线状态 Hook** (`useOnlineStatus.ts`): 全局 online/offline 事件检测
- **离线指示器** (`OfflineIndicator.tsx`): 固定横幅，显示离线状态或待同步操作数
- 重连后自动触发队列重放，发射 `offline-queue-replay` 自定义事件

---

## 12. 当前架构评估与改进记录

### 12.1 当前分层判断

当前项目整体分层是合理的：HTTP 路由集中在 `backend/app/api/`，核心业务逻辑在 `backend/app/services/` 和 `backend/app/agents/`，数据库结构在 `backend/app/models/`，前端页面、业务组件、API 客户端分别位于 `frontend/app/`、`frontend/components/`、`frontend/lib/`。这套结构适合继续演进多智能体生活推荐产品。

本轮新增能力后，推荐系统已经从普通业务 API 中抽成独立服务边界：

```
frontend cards/pages
  → frontend/lib/api.ts recommendation client
    → backend/app/api/recommendation.py
      → RecommendationService
        → events / profile / candidate / ranker / explain / embeddings
          → recommendation_events / recommendation_embeddings / recommendation_logs
```

这个边界避免了商品、餐厅、行程、首页各自写一套排序逻辑，也为后续接入 two-tower、DeepFM、DIN、SASRec/BERT4Rec 留出了稳定数据闭环。

分享模块的当前边界是：

```
frontend/app/shares/*
  → frontend/lib/api.ts share client
    → backend/app/api/share.py
      → ShareService
        → travel_notes / travel_note_comments / travel_note_interactions
```

分享模块现在已经具备独立服务层。`api/share.py` 只负责 HTTP 参数、鉴权依赖和响应模型，`ShareService` 负责可见性校验、作者权限、序列化、互动计数、评论创建和推荐事件写入。后续如果加入内容审核、通知、举报和社区推荐分发，可以继续在服务层下拆分 `moderation`、`notification`、`distribution` 子模块。

### 12.2 已完成的架构改进

- 新增 `RecommendationService.profile_insights()`，把推荐画像序列化从 `api/recommendation.py` 下沉到服务层，API 只负责鉴权、参数和响应模型。
- 新增 `frontend/components/Home/RecommendationInsights.tsx`，把首页推荐流和画像面板从 `PersonalDashboard.tsx` 中拆出，降低首页组件复杂度。
- 新增 `frontend/lib/api-client.ts` 和 `frontend/lib/api-clients/*`，把 HTTP 基础设施和标准 REST domain client 从 `frontend/lib/api.ts` 中拆出，并保留原兼容导出。
- 新增 `frontend/lib/api-clients/chat.ts`，把聊天 SSE 重连、token refresh 后重试、事件解析从聚合出口中拆出。
- 新增 `frontend/lib/useRecommendationTracking.ts`，把首页、商品页、餐厅页的推荐曝光、点击、加购、选择和隐藏反馈统一收敛到一个 hook。
- 新增 `backend/app/services/share_service.py`，把游记分享的查询、权限、序列化、互动和推荐埋点从路由层下沉到服务层。
- 推荐服务支持无外部 embedding key 的本地关键词/标签相似度兜底，保证开发环境和离线演示可运行。
- 推荐事件覆盖浏览、点击、加购、选择餐厅、确认行程、喜欢、不感兴趣、隐藏等闭环行为，后续可以直接用于模型训练样本。
- 游记分享模块已经接入旅行卡片发布入口，并提供列表、详情、点赞、收藏、评论等基础互动面。

### 12.3 当前主要问题

| 问题 | 影响 | 建议 |
|------|------|------|
| `travel_agent.py`、`chat_orchestrator.py` 仍然偏大 | 后续修改容易引入回归 | 分阶段拆出 itinerary builder、artifact writer |
| 推荐系统 V1 使用数据库 JSON 存向量 | 数据量变大后相似度查询成本会上升 | 先保留 V1，达到规模后迁移 pgvector、Qdrant 或 Milvus |
| 分享模块后续可能加入审核、通知、举报 | 单一服务继续增长会影响可维护性 | 在 `ShareService` 下拆分 moderation / notification / distribution |
| 前端推荐曝光目前由页面主动触发 | 长列表滚动曝光可能不够精确 | 后续可基于 IntersectionObserver 做真正可见曝光批量上报 |
| 部分构建产物容易出现在工作区 | PR diff 噪声较大 | 保持 `.gitignore`，构建后检查 `frontend/public/sw.js` 等生成文件 |
| Playwright 本地关闭 dev server 时偶发 `ECONNRESET` 日志 | 不影响通过结果 | 默认隐藏 webServer 日志，需要排查时用 `PLAYWRIGHT_SHOW_WEBSERVER_LOGS=1` 打开 |

### 12.4 后续演进路线

1. 推荐系统 V2：引入离线特征快照表，定时从 `RecommendationEvent` 汇总用户长期/短期兴趣。
2. 推荐系统 V3：商品、餐厅、POI、游记统一 item catalog，接入向量检索或近邻索引。
3. 社区推荐：游记进入 `RecommendationService` 候选池，按城市、主题、互动质量和用户兴趣排序。
4. 编排瘦身：`chat_orchestrator` 只保留流式会话生命周期，artifact 保存、推荐事件写入、偏好学习继续下沉到独立服务。
5. 前端 API 迁移策略：后续页面可以按需直接导入 `api-clients/*`，当前继续保留 `frontend/lib/api.ts` 作为稳定兼容层。

---

## 附录

### A. 文件统计

| 层 | 文件数 | 代码行数 |
|-------|--------|----------|
| 核心基础设施 | ~8 | ~600 |
| API 路由 | 10 | ~1,500 |
| ORM 模型 | 9 | ~400 |
| 智能体 | ~10 | ~2,500 |
| 服务层 | ~15 | ~2,800 |
| 中间件 | 3 | ~150 |
| **后端总计** | **~70** | **~9,500** |
| **前端总计** | **~40** | **~6,500** |
| **总计** | **~110** | **~16,000** |

### B. 技术栈

| 层 | 技术 |
|-------|--------|
| 运行时 | Python 3.11+ + Node.js 18+ |
| 后端框架 | FastAPI + Uvicorn (--reload 开发模式) |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| 数据库 | PostgreSQL 16 + Redis 7 |
| LLM | DeepSeek (OpenAI 兼容 API) |
| 前端框架 | Next.js 14 + React 18 |
| 样式 | Tailwind CSS |
| 外部 API | 高德地图 + 和风天气 |
| 任务队列 | arq (Redis) |
| 监控 | Prometheus + Grafana + Sentry |
| 负载测试 | k6 |
| 容器化 | Docker + Docker Compose |
| 编排 | Kubernetes (可选) |
