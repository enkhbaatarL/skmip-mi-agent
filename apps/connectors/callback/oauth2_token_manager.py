from __future__ import annotations

import asyncio
import base64
import time
from typing import Any

import httpx

from apps.common.logging.logger_config import logger


class OAuth2TokenManager:
    """client_credentials 방식 OAuth2 토큰 발급·캐싱·갱신."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get_token(self) -> str:
        if self._token and time.monotonic() < self._expires_at - 30:
            return self._token
        async with self._lock:
            if self._token and time.monotonic() < self._expires_at - 30:
                return self._token
            return await self._fetch_token()

    async def refresh_token(self) -> str:
        async with self._lock:
            self._token = None
            return await self._fetch_token()

    async def _fetch_token(self) -> str:
        from apps.common.configs.config import get_settings

        cfg = get_settings()
        credentials = base64.b64encode(
            f"{cfg.callback_oauth2_client_id}:{cfg.callback_oauth2_client_secret}".encode()
        ).decode()

        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                async with httpx.AsyncClient(
                    verify=cfg.http_verify,
                    timeout=30.0,
                    trust_env=False,
                ) as client:
                    resp = await client.post(
                        cfg.callback_oauth2_token_url,
                        headers={
                            "Authorization": f"Basic {credentials}",
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                        data={"grant_type": "client_credentials"},
                    )
                    resp.raise_for_status()

                payload: dict[str, Any] = resp.json()
                token, expires_in = self._parse_token_payload(payload)
                self._token = token
                self._expires_at = time.monotonic() + expires_in
                logger.info(f"[CALLBACK][OAuth2] Token acquired | expires_in={expires_in}s")
                return self._token
            except Exception as exc:
                last_error = exc
                if attempt >= 3:
                    break
                backoff = 0.5 * (2 ** (attempt - 1))
                logger.warning(
                    "[CALLBACK][OAuth2] Token fetch failed, retrying "
                    f"(attempt={attempt}/3, backoff={backoff:.1f}s) | error={exc!r}"
                )
                await asyncio.sleep(backoff)

        if last_error is not None:
            raise last_error
        raise RuntimeError("OAuth2 token fetch failed without explicit error")

    def _parse_token_payload(self, payload: dict[str, Any]) -> tuple[str, int]:
        token: Any = payload.get("access_token")
        expires_in_raw: Any = payload.get("expires_in")

        nested_data = payload.get("data")
        if isinstance(nested_data, dict):
            if not token:
                token = nested_data.get("accessToken") or nested_data.get("access_token")
            if expires_in_raw is None:
                expires_in_raw = (
                    nested_data.get("expiresIn") or nested_data.get("expires_in")
                )

        if not isinstance(token, str) or not token.strip():
            raise ValueError("OAuth2 token response missing access token")

        try:
            expires_in = int(expires_in_raw) if expires_in_raw is not None else 3600
        except (TypeError, ValueError):
            expires_in = 3600
        if expires_in <= 0:
            expires_in = 3600
        return token.strip(), expires_in


_token_manager = OAuth2TokenManager()


def get_token_manager() -> OAuth2TokenManager:
    return _token_manager
