"""
Progress Reporter - Agent 执行步骤报告

允许 Agent 在执行过程中报告当前进度，
Supervisor 将其转发为 SSE thinking 事件，
用户可以看到 AI 正在做什么。

两种模式:
  1. Buffer mode: 收集所有进度消息，等待 Agent 完成后批量发送
  2. Callback mode: 实时回调（需要外部机制转发到 SSE）
"""
from typing import Callable, Coroutine

ProgressCallback = Callable[[str], Coroutine] | None


class ProgressReporter:
    """Agent 进度报告器，通过回调向 Supervisor 发送进度事件。"""

    def __init__(self, callback: ProgressCallback = None):
        self._callback = callback
        self._buffer: list[str] = []

    async def step(self, message: str) -> None:
        """报告一个进度步骤。"""
        self._buffer.append(message)
        if self._callback:
            await self._callback(message)

    @property
    def steps(self) -> list[str]:
        """获取所有已报告的进度步骤。"""
        return list(self._buffer)

    def clear(self) -> None:
        """清除已缓存的进度步骤。"""
        self._buffer.clear()


def noop_reporter() -> ProgressReporter:
    """创建一个无操作的进度报告器（用于非流式场景）。"""
    return ProgressReporter()


async def yield_progress(
    reporter: ProgressReporter | None,
    message: str,
) -> None:
    """Helper: safely yield a progress step."""
    if reporter:
        await reporter.step(message)
