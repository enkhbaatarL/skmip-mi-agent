from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
STATIC_URL = "/static"


def register_local_openapi_docs(app: FastAPI, ingress_prefix: str = "") -> None:
    ingress_prefix = ingress_prefix.rstrip("/")

    app.mount(STATIC_URL, StaticFiles(directory=STATIC_DIR), name="static")
    if ingress_prefix:
        app.mount(
            f"{ingress_prefix}{STATIC_URL}",
            StaticFiles(directory=STATIC_DIR),
            name="prefixed-static",
        )

    def build_swagger_ui_html(prefix: str = "") -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url=f"{prefix}{app.openapi_url}",
            title=f"{app.title} - Swagger UI",
            swagger_js_url=f"{prefix}{STATIC_URL}/swagger-ui/swagger-ui-bundle.js",
            swagger_css_url=f"{prefix}{STATIC_URL}/swagger-ui/swagger-ui.css",
            swagger_favicon_url="data:,",
            swagger_ui_parameters={"validatorUrl": None},
        )

    def build_redoc_html(prefix: str = "") -> HTMLResponse:
        return get_redoc_html(
            openapi_url=f"{prefix}{app.openapi_url}",
            title=f"{app.title} - ReDoc",
            redoc_js_url=f"{prefix}{STATIC_URL}/redoc/redoc.standalone.js",
            redoc_favicon_url="data:,",
            with_google_fonts=False,
        )

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui_html() -> HTMLResponse:
        return build_swagger_ui_html()

    @app.get("/redoc", include_in_schema=False)
    async def redoc_html() -> HTMLResponse:
        return build_redoc_html()

    if ingress_prefix:

        @app.get(f"{ingress_prefix}/docs", include_in_schema=False)
        async def prefixed_swagger_ui_html() -> HTMLResponse:
            return build_swagger_ui_html(ingress_prefix)

        @app.get(f"{ingress_prefix}/redoc", include_in_schema=False)
        async def prefixed_redoc_html() -> HTMLResponse:
            return build_redoc_html(ingress_prefix)

        @app.get(f"{ingress_prefix}{app.openapi_url}", include_in_schema=False)
        async def prefixed_openapi_json() -> JSONResponse:
            return JSONResponse(app.openapi())
