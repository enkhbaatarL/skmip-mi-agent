#!/usr/bin/env bash
set -euo pipefail

VM_HOST="40.82.137.178"
VM_USER="azureuser"
DEFAULT_PEM="/Users/messiah/sk-mi-demo-vm-key.pem"
SCENARIO_DIR="/home/azureuser/mi/mi-agent-scenario"
DEFAULT_IMAGE_REPO="skmidemoacr.azurecr.io/mi-agent-scenario"
DEFAULT_DOCKERFILE="Dockerfile"
DEFAULT_PLATFORM="linux/amd64"

IMAGE_REPO="$DEFAULT_IMAGE_REPO"
DOCKERFILE="$DEFAULT_DOCKERFILE"
PLATFORM="$DEFAULT_PLATFORM"
PEM="${MI_DEMO_VM_PEM:-$DEFAULT_PEM}"
PULL=1
NO_CACHE=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  build_push_deploy.sh [options] <command> [args]

Commands:
  build-push-deploy <version>  Build image, push to ACR, then deploy on demo VM
  build-push <version>         Build image and push to ACR only
  deploy <version>             Update remote compose IMAGE and recreate app only
  status                       Show remote scenario agent compose status
  logs [tail]                  Show remote scenario agent logs; default tail=120

Options:
  --pem <path>                 SSH PEM path. Defaults to MI_DEMO_VM_PEM or /Users/messiah/sk-mi-demo-vm-key.pem
  --dockerfile <path>          Dockerfile path. Default: Dockerfile
  --platform <platform>        Docker platform. Default: linux/amd64
  --image-repo <repo>          Image repo. Default: skmidemoacr.azurecr.io/mi-agent-scenario
  --no-cache                   Add --no-cache to docker build
  --no-pull                    Do not add --pull to docker build
  --dry-run                    Print commands without executing them
  -h, --help                   Show help

Version examples:
  v0.0.16
  0.0.16                       Normalized to v0.0.16
EOF
}

quote_cmd() {
  printf '%q ' "$@"
}

run_cmd() {
  echo "+ $(quote_cmd "$@")"
  if [[ "$DRY_RUN" != "1" ]]; then
    "$@"
  fi
}

require_arg() {
  local option="$1"
  local value="${2:-}"
  if [[ -z "$value" ]]; then
    echo "ERROR: $option requires a value." >&2
    exit 2
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pem)
      require_arg "$1" "${2:-}"
      PEM="$2"
      shift 2
      ;;
    --dockerfile)
      require_arg "$1" "${2:-}"
      DOCKERFILE="$2"
      shift 2
      ;;
    --platform)
      require_arg "$1" "${2:-}"
      PLATFORM="$2"
      shift 2
      ;;
    --image-repo)
      require_arg "$1" "${2:-}"
      IMAGE_REPO="$2"
      shift 2
      ;;
    --no-cache)
      NO_CACHE=1
      shift
      ;;
    --no-pull)
      PULL=0
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      break
      ;;
  esac
done

COMMAND="${1:-}"
if [[ $# -gt 0 ]]; then
  shift
fi

if [[ -z "$COMMAND" ]]; then
  usage >&2
  exit 2
fi

normalize_version() {
  local version="$1"
  if [[ "$version" =~ ^[0-9]+(\.[0-9]+){1,3}([-+][A-Za-z0-9._-]+)?$ ]]; then
    version="v${version}"
  fi
  if [[ ! "$version" =~ ^v[0-9]+(\.[0-9]+){1,3}([-+][A-Za-z0-9._-]+)?$ ]]; then
    echo "ERROR: version must look like v0.0.16 or 0.0.16: $version" >&2
    exit 2
  fi
  printf '%s\n' "$version"
}

normalize_tail() {
  local tail="${1:-120}"
  if [[ ! "$tail" =~ ^[0-9]+$ ]] || (( tail < 1 || tail > 2000 )); then
    echo "ERROR: tail must be an integer from 1 to 2000: $tail" >&2
    exit 2
  fi
  printf '%s\n' "$tail"
}

repo_root() {
  git rev-parse --show-toplevel
}

ensure_repo_context() {
  local root
  root="$(repo_root)"
  cd "$root"
  if [[ ! -f "$DOCKERFILE" ]]; then
    echo "ERROR: Dockerfile not found: $DOCKERFILE" >&2
    exit 2
  fi
}

ensure_pem() {
  if [[ "$DRY_RUN" == "1" ]]; then
    return
  fi
  if [[ ! -f "$PEM" ]]; then
    cat >&2 <<EOF
ERROR: PEM file not found: $PEM

Ask the user for the PEM file path, then rerun one of:
  $0 --pem /path/to/key.pem $COMMAND
  MI_DEMO_VM_PEM=/path/to/key.pem $0 $COMMAND
EOF
    exit 3
  fi
  if [[ ! -r "$PEM" ]]; then
    echo "ERROR: PEM file is not readable: $PEM" >&2
    exit 3
  fi
  chmod 600 "$PEM" 2>/dev/null || true
}

ssh_opts() {
  printf '%s\n' \
    -i "$PEM" \
    -o IdentitiesOnly=yes \
    -o StrictHostKeyChecking=accept-new \
    -o BatchMode=yes \
    -o ConnectTimeout=15
}

remote_script() {
  local script
  script="$(cat)"
  ensure_pem
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "+ ssh -i $(printf '%q' "$PEM") -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o BatchMode=yes -o ConnectTimeout=15 ${VM_USER}@${VM_HOST} 'bash -s' <<'REMOTE_SCRIPT'"
    printf '%s\n' "$script"
    echo "REMOTE_SCRIPT"
    return
  fi
  ssh \
    -i "$PEM" \
    -o IdentitiesOnly=yes \
    -o StrictHostKeyChecking=accept-new \
    -o BatchMode=yes \
    -o ConnectTimeout=15 \
    "${VM_USER}@${VM_HOST}" "bash -s" <<<"$script"
}

image_for_version() {
  local version="$1"
  printf '%s:%s\n' "$IMAGE_REPO" "$version"
}

build_push() {
  local version="$1"
  local image
  image="$(image_for_version "$version")"

  ensure_repo_context

  build_args=(docker build --platform "$PLATFORM" -f "$DOCKERFILE" -t "$image")
  if [[ "$PULL" == "1" ]]; then
    build_args+=(--pull)
  fi
  if [[ "$NO_CACHE" == "1" ]]; then
    build_args+=(--no-cache)
  fi
  build_args+=(.)

  echo "[build] image=$image"
  run_cmd "${build_args[@]}"
  run_cmd docker image inspect "$image" --format '{{.Id}} {{.Os}}/{{.Architecture}} {{index .RepoTags 0}}'
  run_cmd docker push "$image"
}

remote_deploy() {
  local version="$1"
  local image
  image="$(image_for_version "$version")"

  remote_script <<EOF
set -euo pipefail
cd "$SCENARIO_DIR"
echo "[scenario] path=\$(pwd)"
if [[ ! -f .env ]]; then
  echo "ERROR: .env not found in $SCENARIO_DIR" >&2
  exit 1
fi
echo "[scenario] before:"
grep -n '^IMAGE=' .env || true
if grep -q '^IMAGE=' .env; then
  perl -0pi -e 's#^IMAGE=.*#IMAGE=$image#m' .env
else
  printf '\nIMAGE=$image\n' >> .env
fi
echo "[scenario] after:"
grep -n '^IMAGE=' .env
docker compose --progress plain pull app
docker compose --progress plain up -d --force-recreate app
docker compose ps
docker compose logs --tail=120 app | tee /tmp/mi-agent-scenario-deploy.log
if grep -q 'Application startup complete' /tmp/mi-agent-scenario-deploy.log; then
  echo "[scenario] startup=complete"
else
  echo "WARN: startup marker not found in the last 120 log lines." >&2
fi
EOF
}

remote_status() {
  remote_script <<EOF
set -euo pipefail
cd "$SCENARIO_DIR"
echo "[scenario] path=\$(pwd)"
grep -n '^IMAGE=' .env || true
docker compose ps
EOF
}

remote_logs() {
  local tail="$1"
  remote_script <<EOF
set -euo pipefail
cd "$SCENARIO_DIR"
echo "[scenario] path=\$(pwd)"
docker compose logs --tail=$tail app
EOF
}

case "$COMMAND" in
  build-push-deploy)
    if [[ -z "${1:-}" ]]; then
      echo "ERROR: build-push-deploy requires a version, e.g. v0.0.16." >&2
      exit 2
    fi
    version="$(normalize_version "$1")"
    build_push "$version"
    remote_deploy "$version"
    ;;
  build-push)
    if [[ -z "${1:-}" ]]; then
      echo "ERROR: build-push requires a version, e.g. v0.0.16." >&2
      exit 2
    fi
    version="$(normalize_version "$1")"
    build_push "$version"
    ;;
  deploy)
    if [[ -z "${1:-}" ]]; then
      echo "ERROR: deploy requires a version, e.g. v0.0.16." >&2
      exit 2
    fi
    version="$(normalize_version "$1")"
    remote_deploy "$version"
    ;;
  status)
    remote_status
    ;;
  logs)
    tail_count="$(normalize_tail "${1:-120}")"
    remote_logs "$tail_count"
    ;;
  *)
    echo "ERROR: unknown command: $COMMAND" >&2
    usage >&2
    exit 2
    ;;
esac
