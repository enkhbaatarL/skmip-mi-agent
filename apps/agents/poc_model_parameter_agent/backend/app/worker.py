from __future__ import annotations

import asyncio
import signal

from loguru import logger

from app.config import get_settings
from app.db import get_session_factory
from app.services.learning_service import process_pending


class LearningWorker:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.stopping = asyncio.Event()

    def request_stop(self) -> None:
        self.stopping.set()

    async def run(self) -> None:
        logger.info(
            "Learning Worker started mode={} poll={}s batch_size={}",
            self.settings.agent_mode,
            self.settings.worker_poll_seconds,
            self.settings.worker_batch_size,
        )
        while not self.stopping.is_set():
            session = get_session_factory()()
            try:
                result = process_pending(session)
                if result["processed"]:
                    logger.info("Learning cycle completed: {}", result)
            except Exception as exc:  # noqa: BLE001 - polling boundary records failure and continues safely.
                session.rollback()
                logger.exception("Learning cycle failed: {}", exc)
            finally:
                session.close()
            try:
                await asyncio.wait_for(self.stopping.wait(), timeout=self.settings.worker_poll_seconds)
            except TimeoutError:
                continue
        logger.info("Learning Worker stopped gracefully")


async def async_main() -> None:
    worker = LearningWorker()
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signal_name, worker.request_stop)
    await worker.run()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
