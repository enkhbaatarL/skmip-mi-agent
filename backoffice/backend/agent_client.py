from __future__ import annotations

from typing import Any

import httpx

from backoffice.backend.schemas import AgentHttpError, JsonObject


class AgentClient:
    def __init__(self, base_url: str, timeout_seconds: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds)

    async def create_scenario_group(self, payload: JsonObject) -> JsonObject:
        return await self._request("create", "POST", "/scenario-groups", json=payload)

    async def get_scenario_group(self, scenario_group_id: int, include_deleted: bool = False) -> JsonObject:
        return await self._request(
            "detail",
            "GET",
            f"/scenario-groups/{scenario_group_id}",
            params={"includeDeleted": str(include_deleted).lower()},
        )

    async def list_scenario_groups(self, params: dict[str, Any]) -> JsonObject:
        return await self._request("list", "GET", "/scenario-groups", params=params)

    async def soft_delete_scenario_group(
        self,
        scenario_group_id: int,
        user_id: int,
        delete_authorization: str,
    ) -> JsonObject:
        return await self._request(
            "soft_delete",
            "DELETE",
            f"/scenario-groups/{scenario_group_id}",
            json={"userId": user_id},
            headers={"Authorization": f"Bearer {delete_authorization}"},
        )

    async def validate_scenarios(self, scenario_group_id: int, payload: JsonObject) -> JsonObject:
        return await self._request("validation", "POST", f"/scenario-groups/{scenario_group_id}/validation", json=payload)

    async def create_signposts(self, scenario_group_id: int, payload: JsonObject) -> JsonObject:
        return await self._request("signposts", "POST", f"/scenario-groups/{scenario_group_id}/signposts", json=payload)

    async def confirm_generation(self, scenario_group_id: int, payload: JsonObject) -> JsonObject:
        return await self._request("confirmation", "POST", f"/scenario-groups/{scenario_group_id}/confirmation", json=payload)

    async def _request(self, step: str, method: str, path: str, **kwargs: Any) -> JsonObject:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise AgentHttpError(step=step, status_code=response.status_code, body=_response_body(response))
        return _response_body(response)


def _response_body(response: httpx.Response) -> JsonObject:
    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text}
    if isinstance(body, dict):
        return body
    return {"data": body}
