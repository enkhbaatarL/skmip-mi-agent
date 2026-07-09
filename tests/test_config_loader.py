from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


PRESERVED_SUBPROCESS_ENV_KEYS = {
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "POETRY_ACTIVE",
    "PYTHONHOME",
    "PYTHONPATH",
    "SHELL",
    "TMPDIR",
    "USER",
    "VIRTUAL_ENV",
}

BASE_CONFIG = textwrap.dedent(
    """
    METADATA_DB_TYPE: mysql
    METADATA_DB_HOST: db-host
    METADATA_DB_PORT: 3306
    METADATA_DB_NAME: midb
    METADATA_DB_USERNAME: user
    METADATA_DB_PASSWORD: pass

    ai_platform_host_url: http://ai-platform
    api_key: api-key

    model_endpoint: http://model-endpoint
    model_api_key: model-key
    model_api_deployment_name: model
    lightly_thinking_model_api_deployment_name: model
    deeply_thinking_model_api_deployment_name: model

    MCP_POOL_URLS: {}
    COMPANY_MCP_MAP: {}
    mcp_pool_size: 10
    mcp_per_session_limit: 5
    mcp_client_timeout: 30
    mcp_client_sse_read_timeout: 60

    http_timeout: 60
    http_connect_timeout: 10
    http_verify: true
    http2: true
    http_max_connection: 100
    http_max_keepalive: 20

    rdb_search_metadata_repo_id: 00000000-0000-0000-0000-000000000000

    llm_concurrency: 4
    llm_max_retries: 1
    mcp_max_concurrency: 8
    http_max_concurrency: 16
    rdb_exec_max_parallel: 4
    log_level: DEBUG
    """
).strip()


class ConfigLoaderTest(unittest.TestCase):
    def run_settings_import(
        self,
        config_text: str,
        extra_env: dict[str, str] | None = None,
        print_lines: list[str] | None = None,
    ) -> list[str]:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"
            config_path.write_text(config_text, encoding="utf-8")

            env = {
                key: value
                for key, value in os.environ.items()
                if key in PRESERVED_SUBPROCESS_ENV_KEYS
            }
            env["APP_CONFIG"] = str(config_path)
            if extra_env:
                env.update(extra_env)

            script_lines = [
                "from apps.common.configs.config import get_settings",
                "cfg = get_settings()",
            ]
            script_lines.extend(
                print_lines
                or [
                    "print(cfg.METADATA_DB_HOST)",
                    "print(cfg.llm_max_retries)",
                    "print(cfg.http_timeout)",
                    "print(cfg.log_level)",
                ]
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "\n".join(script_lines),
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            return result.stdout.strip().splitlines()

    def test_lf_config_loads(self) -> None:
        lines = self.run_settings_import(BASE_CONFIG)

        self.assertEqual(lines, ["db-host", "1", "60.0", "DEBUG"])

    def test_real_crlf_config_loads(self) -> None:
        lines = self.run_settings_import(BASE_CONFIG.replace("\n", "\r\n"))

        self.assertEqual(lines, ["db-host", "1", "60.0", "DEBUG"])

    def test_literal_escaped_crlf_config_loads(self) -> None:
        escaped_config = BASE_CONFIG.replace("\n", r"\r\n")

        lines = self.run_settings_import(escaped_config)

        self.assertEqual(lines, ["db-host", "1", "60.0", "DEBUG"])

    def test_literal_escaped_crlf_config_with_trailing_newline_loads(self) -> None:
        escaped_config = BASE_CONFIG.replace("\n", r"\r\n") + "\n"

        lines = self.run_settings_import(escaped_config)

        self.assertEqual(lines, ["db-host", "1", "60.0", "DEBUG"])

    def test_env_placeholders_are_replaced_after_newline_normalization(self) -> None:
        escaped_config = BASE_CONFIG.replace("METADATA_DB_HOST: db-host", "METADATA_DB_HOST: ${TEST_DB_HOST}")
        escaped_config = escaped_config.replace("\n", r"\r\n")

        lines = self.run_settings_import(escaped_config, {"TEST_DB_HOST": "db-from-env"})

        self.assertEqual(lines, ["db-from-env", "1", "60.0", "DEBUG"])

    def test_missing_env_placeholder_is_left_literal(self) -> None:
        escaped_config = BASE_CONFIG.replace("METADATA_DB_HOST: db-host", "METADATA_DB_HOST: ${MISSING_TEST_DB_HOST}")
        escaped_config = escaped_config.replace("\n", r"\r\n")

        lines = self.run_settings_import(escaped_config)

        self.assertEqual(lines, ["${MISSING_TEST_DB_HOST}", "1", "60.0", "DEBUG"])

    def test_multiline_yaml_preserves_literal_escaped_newline_value(self) -> None:
        config_text = BASE_CONFIG + "\ncallback_oauth2_client_secret: 'line1\\r\\nline2'"

        lines = self.run_settings_import(
            config_text,
            print_lines=["print(repr(cfg.callback_oauth2_client_secret))"],
        )

        self.assertEqual(lines, [r"'line1\\r\\nline2'"])

    def test_single_line_escaped_blob_loads_plain_scalar_apostrophe(self) -> None:
        config_text = BASE_CONFIG.replace("api_key: api-key", "api_key: it's-ok\n# don't lower")
        escaped_config = config_text.replace("\n", r"\r\n")

        lines = self.run_settings_import(
            escaped_config,
            print_lines=["print(cfg.api_key)"],
        )

        self.assertEqual(lines, ["it's-ok"])

    def test_parent_config_env_vars_do_not_override_temp_config(self) -> None:
        original = os.environ.get("METADATA_DB_HOST")
        os.environ["METADATA_DB_HOST"] = "external-db-host"
        try:
            lines = self.run_settings_import(BASE_CONFIG)
        finally:
            if original is None:
                os.environ.pop("METADATA_DB_HOST", None)
            else:
                os.environ["METADATA_DB_HOST"] = original

        self.assertEqual(lines, ["db-host", "1", "60.0", "DEBUG"])


if __name__ == "__main__":
    unittest.main()
