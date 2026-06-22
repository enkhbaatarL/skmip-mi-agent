#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  .claude/skills/mi-source-banib/scripts/create_source_import_bundle.sh <tag> [base-branch]

Examples:
  .claude/skills/mi-source-banib/scripts/create_source_import_bundle.sh v0.0.3
  .claude/skills/mi-source-banib/scripts/create_source_import_bundle.sh v0.0.3 main

Creates:
  release-artifacts/<repo>-<tag>.bundle
  release-artifacts/<repo>-<tag>.bundle.zip  # contains the bundle and internal import sh
  release-artifacts/<repo>-<tag>.manifest.txt
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

TAG="${1:-}"
BASE_BRANCH="${2:-main}"
REMOTE="${REMOTE:-origin}"
OUTPUT_DIR="${OUTPUT_DIR:-release-artifacts}"

if [[ -z "$TAG" ]]; then
  usage >&2
  exit 1
fi

if [[ ! "$TAG" =~ ^v[0-9]+(\.[0-9]+){1,3}([-+][A-Za-z0-9._-]+)?$ ]]; then
  echo "ERROR: tag must look like v0.0.3 or v1.2.3-rc.1: $TAG" >&2
  exit 1
fi

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"

REPO_NAME="$(basename "$PROJECT_ROOT")"
BUNDLE_FILE="${OUTPUT_DIR}/${REPO_NAME}-${TAG}.bundle"
ZIP_FILE="${BUNDLE_FILE}.zip"
MANIFEST_FILE="${OUTPUT_DIR}/${REPO_NAME}-${TAG}.manifest.txt"
IMPORT_SCRIPT=".claude/skills/mi-source-banib/scripts/import_source_bundle.sh"

echo "[1/7] Fetching ${REMOTE}/${BASE_BRANCH} and tags..."
git fetch "$REMOTE" "$BASE_BRANCH" --tags --prune

if git show-ref --verify --quiet "refs/tags/${TAG}"; then
  echo "ERROR: local tag already exists: ${TAG}" >&2
  exit 1
fi

if git ls-remote --exit-code --tags "$REMOTE" "refs/tags/${TAG}" >/dev/null 2>&1; then
  echo "ERROR: remote tag already exists: ${TAG}" >&2
  exit 1
fi

TARGET_COMMIT="$(git rev-parse "${REMOTE}/${BASE_BRANCH}^{commit}")"
SHORT_COMMIT="$(git rev-parse --short=12 "$TARGET_COMMIT")"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "WARN: working tree has local changes. They are not included; bundle uses ${REMOTE}/${BASE_BRANCH} (${SHORT_COMMIT})." >&2
fi

echo "[2/7] Creating annotated tag ${TAG} at ${TARGET_COMMIT}..."
git tag -a "$TAG" "$TARGET_COMMIT" -m "Release ${TAG}"

echo "[3/7] Pushing tag ${TAG} to ${REMOTE}..."
git push "$REMOTE" "refs/tags/${TAG}"

mkdir -p "$OUTPUT_DIR"
rm -f "$BUNDLE_FILE" "$ZIP_FILE" "$MANIFEST_FILE"

echo "[4/7] Creating bundle: ${BUNDLE_FILE}"
git bundle create "$BUNDLE_FILE" "refs/tags/${TAG}"

echo "[5/7] Verifying bundle..."
git bundle verify "$BUNDLE_FILE"

echo "[6/7] Zipping bundle: ${ZIP_FILE}"
zip -j -9 "$ZIP_FILE" "$BUNDLE_FILE" "$IMPORT_SCRIPT" >/dev/null
unzip -l "$ZIP_FILE" >/dev/null

sha256_file() {
  local file="$1"
  if command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 "$file" | awk '{print $NF}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
  else
    echo "sha256-unavailable"
  fi
}

BUNDLE_SHA256="$(sha256_file "$BUNDLE_FILE")"
ZIP_SHA256="$(sha256_file "$ZIP_FILE")"

cat > "$MANIFEST_FILE" <<EOF
repo=${REPO_NAME}
remote=${REMOTE}
base_branch=${BASE_BRANCH}
tag=${TAG}
commit=${TARGET_COMMIT}
bundle_file=$(basename "$BUNDLE_FILE")
bundle_sha256=${BUNDLE_SHA256}
zip_file=$(basename "$ZIP_FILE")
zip_sha256=${ZIP_SHA256}
import_script=import_source_bundle.sh
EOF

echo "[7/7] Done."
echo "Tag commit : ${TARGET_COMMIT}"
echo "Bundle     : ${BUNDLE_FILE}"
echo "Bundle SHA : ${BUNDLE_SHA256}"
echo "Zip        : ${ZIP_FILE}"
echo "Zip SHA    : ${ZIP_SHA256}"
echo "Manifest   : ${MANIFEST_FILE}"
