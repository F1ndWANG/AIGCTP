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
- 后台异步任务队列（arq）
- PWA 离线操作队列

---

## 2. 顶层结构

```
E:\AIGCTP/
├── backend/                    # Python FastAPI 后端
│   ├── app/                    # 应用代码
│   ├── alembic/                # 数据库迁移 (5 版本)
│   ├── tests/                  # 测试套件 (237 个)
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
│   │   └── DietReminder.tsx       # 每日饮食提醒
│   └── UI/                        # 通用 UI 组件
│       ├── Toast.tsx
│       ├── NotificationCenter.tsx
│       ├── ErrorBoundary.tsx
│       └── OfflineIndicator.tsx   # PWA 离线指示器
├── lib/
│   ├── api.ts                     # API 客户端 (核心)
│   ├── types.ts                   # TypeScript 类型定义
│   ├── offline-queue.ts           # IndexedDB 离线队列 (含 onerror)
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

`lib/api.ts` 实现集中式 HTTP 客户端：

- **认证**: 全部请求使用 `credentials: "include"`，无 localStorage token 管理
- **请求封装**: `request<T>()` — 自动带 cookie、30s 超时（AbortController）、指数退避重试（带抖动）+ 401 自动刷新
- **SSE 流式**: `chat.sendStream()` — 解析 `ReadableStream`、支持 9 种事件类型、自动重连（3 次 + 抖动）
- **Token 刷新**: 通过 `POST /api/auth/refresh`（cookie）自动完成，互斥锁防止并发刷新
- **错误处理**: `ApiError` 类 + 分级（retryable / auth_expired）

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

| 测试类型 | 数量 | 数据库 |
|----------|------|--------|
| 单元测试 | 227 | SQLite (内存) + mock |
| PostgreSQL 集成测试 | 10 | PostgreSQL 16 (WindowsSelectorEventLoop) |
| **总计** | **237** | — |

测试覆盖：
- API 认证流程 (注册/登录/刷新/登出/cookie)
- 6 个 Agent (意图分类/路由/失败降级)
- Prompt 构建工具
- 跨域组合
- DB 集成 (CRUD/时区/连接池)

### 11.2 CI/CD (GitHub Actions)

4 个并行 job：

| Job | 触发条件 | 内容 |
|-----|----------|------|
| `backend-lint` | push/PR | ruff check app/ tests/ |
| `backend-test` | push/PR | PostgreSQL 16 service + pytest --cov |
| `frontend-build` | push/PR | npm ci + npm run build |
| `loadtest-smoke` | 所有测试通过后 | Docker Compose + k6 1VU 烟雾测试 |

### 11.3 PWA 离线能力

- **IndexedDB 离线队列** (`offline-queue.ts`): 网络不可用时入队操作，在线后自动重放
- **在线状态 Hook** (`useOnlineStatus.ts`): 全局 online/offline 事件检测
- **离线指示器** (`OfflineIndicator.tsx`): 固定横幅，显示离线状态或待同步操作数
- 重连后自动触发队列重放，发射 `offline-queue-replay` 自定义事件

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
| **后端总计** | **~60** | **~8,500** |
| **前端总计** | **~30** | **~5,500** |
| **总计** | **~90** | **~14,000** |

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
