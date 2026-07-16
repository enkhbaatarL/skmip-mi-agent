# Model Parameter Object Storage MinIO smoke test

로컬 MinIO에 packaged Basecase/LUT를 원격 이름으로 업로드한 뒤 실제 `HeadObject`/`GetObject`,
semantic validation, `current` 활성화, 재사용, credential 오류 시 packaged fallback을 확인한다.

```bash
docker compose \
  -f devops/compose/minio-docker-compose.yaml \
  up -d --wait

.venv/bin/python tests/manual/model_parameter_object_storage/setup_minio.py
.venv/bin/python tests/manual/model_parameter_object_storage/run_smoke_test.py
.venv/bin/python tests/manual/model_parameter_object_storage/run_multi_worker_smoke.py

docker compose \
  -f devops/compose/minio-docker-compose.yaml \
  down -v
```

- S3 API: `http://127.0.0.1:19000`
- MinIO Console: `http://127.0.0.1:19001`
- bucket: `sk-mi-d-osb-ss-skgas`
- credential은 이 로컬 테스트 전용 고정값이며 운영 환경에서 사용하지 않는다.
- `envs/config.yaml`의 `model_parameter_resources`는 운영 매핑과 동일한 bucket-relative
  `object_storage_path`를 사용한다.
- 3-worker smoke는 Object Storage client가 한 번만 생성되고 `GetObject`가 최초 worker에서만
  9회 호출되는지 확인한다.
