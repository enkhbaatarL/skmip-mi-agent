from __future__ import annotations

# ruff: noqa: S106
from pathlib import Path
import sys

from botocore.exceptions import ClientError
from botocore.session import get_session


ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_DIR))

from apps.agents.model_parameter_agent.utils.resource_manifest import (  # noqa: E402
    PACKAGE_BASECASE_DIR,
    PACKAGE_LUT_ROOT,
    load_model_parameter_resource_manifest,
)


BUCKET = "sk-mi-d-osb-ss-skgas"
ENDPOINT = "http://127.0.0.1:19000"
MANIFEST_PATH = Path(__file__).with_name("model_parameter_resources.yaml")


def main() -> None:
    client = get_session().create_client(
        "s3",
        endpoint_url=ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="minio-test-access",
        aws_secret_access_key="minio-test-secret",
    )
    try:
        try:
            client.create_bucket(Bucket=BUCKET)
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code") or "")
            if error_code not in {"BucketAlreadyExists", "BucketAlreadyOwnedByYou"}:
                raise

        manifest = load_model_parameter_resource_manifest(MANIFEST_PATH)
        for item in manifest.download_plan(default_bucket=BUCKET, lut_enabled=True):
            source_root = PACKAGE_BASECASE_DIR if item.area == "basecase" else PACKAGE_LUT_ROOT
            source_path = source_root / item.relative_path
            with source_path.open("rb") as body:
                client.put_object(
                    Bucket=item.location.bucket,
                    Key=item.location.object_key,
                    Body=body,
                )
    finally:
        client.close()


if __name__ == "__main__":
    main()
