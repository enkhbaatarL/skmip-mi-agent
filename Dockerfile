ARG PLATFORM_ARCH="linux/amd64"
FROM python:3.13-slim

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1

# ✅ 컨테이너 기준 루트 디렉토리를 /app 으로 통일
WORKDIR /app

# (선택) 빌드/런타임에 필요한 패키지가 있으면 여기에 추가
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     curl jq \
#  && rm -rf /var/lib/apt/lists/*

# ✅ 1) requirements 먼저 복사해서 캐시 효율 확보
COPY requirements.txt /app/requirements.txt

# ✅ 2) 의존성 설치는 root로
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

# ✅ 유저 생성 + 디렉토리 권한 정리
RUN addgroup --gid 1000 usergroup && \
    adduser user \
      --disabled-password \
      --uid 1000 --gecos "" \
      --ingroup usergroup && \
    mkdir -p /app && \
    chown -R user:usergroup /app && \
    # ✅ 과거 /workdir 경로를 참조하는 코드/툴이 있어도 동작하게 호환 링크 제공
    ln -s /app /workdir

# ✅ 3) 소스 복사
COPY . /app/

# 런타임에서 env 파일을 “파일로 마운트”할 경우 기본 경로
# 예) docker run -v $(pwd)/env.txt:/app/.env:ro ...
ENV ENV_FILE_PATH="/app/.env"

# ✅ GRAPH_PATH도 환경변수로 override 가능하게(원격 실행/경로 변경 대응)
# 기본값은 /app 기준 상대경로
ENV GRAPH_PATH="./apps/agents/mi_agent/flows/mari_agent_runnable.py:runnable_graph"

# ✅ server.py 생성 (env 파일이 없어도 동작하도록)
RUN echo 'import os' > /app/server.py && \
    echo 'from adxp_sdk.serves.server import get_server' >> /app/server.py && \
    echo '' >> /app/server.py && \
    echo 'graph_path = os.getenv("GRAPH_PATH", "./apps/agents/mi_agent/flows/mari_agent_runnable.py:runnable_graph")' >> /app/server.py && \
    echo 'env_file = os.getenv("ENV_FILE_PATH", "/app/.env")' >> /app/server.py && \
    echo 'if not os.path.exists(env_file):' >> /app/server.py && \
    echo '    env_file = None' >> /app/server.py && \
    echo 'app = get_server(graph_path, env_file)' >> /app/server.py

# 런타임 설정
ENV WORKER_CLASS="uvicorn.workers.UvicornWorker" \
    APP__HOST="0.0.0.0" \
    APP__PORT="18080" \
    LOG_LEVEL="info" \
    GRACEFUL_TIMEOUT="600" \
    TIMEOUT="600" \
    KEEP_ALIVE="600" \
    IS_DEPLOYED_APP="true" \
    APP_MODULE="server:app"

EXPOSE 18080

USER user

# ✅ preload는 플래그로만 쓰고, 앱 모듈은 마지막에 전달
CMD python -m gunicorn \
    -k "${WORKER_CLASS}" \
    -b "${APP__HOST}:${APP__PORT}" \
    --log-level "${LOG_LEVEL}" \
    --graceful-timeout "${GRACEFUL_TIMEOUT}" \
    --timeout "${TIMEOUT}" \
    --keep-alive "${KEEP_ALIVE}" \
    --preload \
    "${APP_MODULE}"
