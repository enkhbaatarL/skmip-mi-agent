from __future__ import annotations

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


admin_bearer_scheme = HTTPBearer(
    scheme_name="ScenarioGroupAdminBearer",
    description=(
        "로컬 개발용 정리 API 전용 인증입니다. "
        "`scenario_group_admin_bearer_tokens`에 등록된 토큰을 "
        "`Authorization: Bearer <token>` 형식으로 전달합니다."
    ),
    auto_error=False,
)


def authorization_header(
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials is None:
        return None
    return f"{credentials.scheme} {credentials.credentials}"
