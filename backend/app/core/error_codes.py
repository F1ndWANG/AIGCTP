"""
Standardized error codes for production error classification.

Each error has a machine-readable code and a user-facing message template.
Frontend can use the code to determine retry-ability and display strategy.
"""

from dataclasses import dataclass


@dataclass
class ErrorInfo:
    code: str
    message: str
    retryable: bool = False
    http_status: int = 500


# ── LLM / AI ──
ERR_LLM_UNAVAILABLE = ErrorInfo(
    code="ERR_LLM_UNAVAILABLE",
    message="AI 服务繁忙，请稍后重试。",
    retryable=True,
    http_status=503,
)
ERR_LLM_TIMEOUT = ErrorInfo(
    code="ERR_LLM_TIMEOUT",
    message="AI 响应超时，请稍后重试。",
    retryable=True,
    http_status=504,
)
ERR_LLM_INVALID_RESPONSE = ErrorInfo(
    code="ERR_LLM_INVALID_RESPONSE",
    message="AI 返回异常结果，请重试。",
    retryable=True,
    http_status=502,
)

# ── Rate Limit ──
ERR_RATE_LIMITED = ErrorInfo(
    code="ERR_RATE_LIMITED",
    message="请求太频繁，请稍后重试。",
    retryable=True,
    http_status=429,
)

# ── Auth ──
ERR_AUTH_EXPIRED = ErrorInfo(
    code="ERR_AUTH_EXPIRED",
    message="登录已过期，请重新登录。",
    retryable=False,
    http_status=401,
)
ERR_AUTH_INVALID = ErrorInfo(
    code="ERR_AUTH_INVALID",
    message="用户名或密码错误。",
    retryable=True,
    http_status=401,
)
ERR_AUTH_LOCKED = ErrorInfo(
    code="ERR_AUTH_LOCKED",
    message="账户已被临时锁定，请 {minutes} 分钟后再试。",
    retryable=True,
    http_status=429,
)

# ── Database ──
ERR_DB_ERROR = ErrorInfo(
    code="ERR_DB_ERROR",
    message="系统内部错误，已记录。",
    retryable=True,
    http_status=500,
)
ERR_NOT_FOUND = ErrorInfo(
    code="ERR_NOT_FOUND",
    message="请求的资源不存在。",
    retryable=False,
    http_status=404,
)

# ── Validation ──
ERR_VALIDATION = ErrorInfo(
    code="ERR_VALIDATION",
    message="请求参数有误：{detail}",
    retryable=False,
    http_status=400,
)
ERR_MESSAGE_TOO_LONG = ErrorInfo(
    code="ERR_MESSAGE_TOO_LONG",
    message="消息过长，请精简后重试。",
    retryable=False,
    http_status=400,
)

# ── External Services ──
ERR_EXTERNAL_API = ErrorInfo(
    code="ERR_EXTERNAL_API",
    message="外部服务暂时不可用，请稍后重试。",
    retryable=True,
    http_status=502,
)
