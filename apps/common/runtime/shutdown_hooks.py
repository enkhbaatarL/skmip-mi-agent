from __future__ import annotations

import asyncio
import atexit
import os
import signal
import threading
from typing import Awaitable, Callable, Optional

_CloseFactory = Callable[[], Awaitable[None]]

_close_factory: Optional[_CloseFactory] = None
_installed_pid: Optional[int] = None
_lock = threading.Lock()


def _run_coro_safely(coro: Awaitable[None]) -> None:
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            asyncio.create_task(coro)  # 같은 이벤트 루프에서 비동기 스케줄
        else:
            loop.run_until_complete(coro)  # 이 분기는 거의 안 옴
    except RuntimeError:
        asyncio.run(coro)  # 루프가 아예 없으면 새 루프로 실행


def _sync_close_handler(*_args) -> None:
    if _close_factory:
        _run_coro_safely(_close_factory())


def install_shutdown_hooks(close_factory: _CloseFactory) -> None:
    global _close_factory, _installed_pid
    with _lock:
        pid = os.getpid()
        if _installed_pid == pid:
            return
        _close_factory = close_factory
        atexit.register(_sync_close_handler)
        try:
            signal.signal(signal.SIGTERM, _sync_close_handler)
        except Exception:
            pass
        try:
            signal.signal(signal.SIGINT, _sync_close_handler)
        except Exception:
            pass
        _installed_pid = pid
