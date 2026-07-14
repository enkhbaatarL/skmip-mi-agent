#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  RELEASE_NOTES_SOURCE=<release-notes.md> .claude/skills/mi-source-banib/scripts/create_source_import_bundle.sh <tag> [base-branch]

Examples:
  RELEASE_NOTES_SOURCE=/tmp/skmip-mi-agent-v0.0.3.release-notes.md .claude/skills/mi-source-banib/scripts/create_source_import_bundle.sh v0.0.3
  RELEASE_NOTES_SOURCE=/tmp/skmip-mi-agent-v0.0.3.release-notes.md .claude/skills/mi-source-banib/scripts/create_source_import_bundle.sh v0.0.3 main

Creates:
  release-artifacts/<repo>-<tag>.bundle
  release-artifacts/<repo>-<tag>.bundle.zip  # contains the bundle and internal import sh
  release-artifacts/<repo>-<tag>.manifest.txt
  release-artifacts/<repo>-<tag>.release-notes.md

Environment:
  RELEASE_NOTES_SOURCE=<file>  Required. Prewritten release notes to copy into artifacts and GitHub Release
  SKIP_GITHUB_RELEASE=1        Create artifacts only; do not create/update GitHub Release
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
RELEASE_NOTES_SOURCE="${RELEASE_NOTES_SOURCE:-}"

if [[ -z "$TAG" ]]; then
  usage >&2
  exit 1
fi

if [[ -z "$RELEASE_NOTES_SOURCE" ]]; then
  echo "ERROR: RELEASE_NOTES_SOURCE is required. Create release notes with Codex/Claude first, then pass the file path." >&2
  usage >&2
  exit 1
fi

if [[ ! -f "$RELEASE_NOTES_SOURCE" ]]; then
  echo "ERROR: RELEASE_NOTES_SOURCE does not exist or is not a file: $RELEASE_NOTES_SOURCE" >&2
  exit 1
fi

SOURCE_DIR="$(cd "$(dirname "$RELEASE_NOTES_SOURCE")" && pwd)"
RELEASE_NOTES_SOURCE="${SOURCE_DIR}/$(basename "$RELEASE_NOTES_SOURCE")"

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
RELEASE_NOTES_FILE="${OUTPUT_DIR}/${REPO_NAME}-${TAG}.release-notes.md"
IMPORT_SCRIPT=".claude/skills/mi-source-banib/scripts/import_source_bundle.sh"

echo "[1/9] Fetching ${REMOTE}/${BASE_BRANCH} and checking tag metadata..."
git fetch "$REMOTE" "$BASE_BRANCH" --prune
git fetch "$REMOTE" --tags --prune

TARGET_COMMIT="$(git rev-parse "${REMOTE}/${BASE_BRANCH}^{commit}")"
SHORT_COMMIT="$(git rev-parse --short=12 "$TARGET_COMMIT")"
TAG_EXISTS_LOCAL=0
TAG_EXISTS_REMOTE=0
TAG_OBJECT=""
TAG_COMMIT=""
TAG_OBJECT_TYPE=""
REMOTE_TAG_OBJECT=""
REMOTE_TAG_COMMIT=""

if git show-ref --verify --quiet "refs/tags/${TAG}"; then
  TAG_EXISTS_LOCAL=1
  TAG_OBJECT="$(git rev-parse "refs/tags/${TAG}")"
  TAG_COMMIT="$(git rev-parse "${TAG}^{commit}")"
  TAG_OBJECT_TYPE="$(git cat-file -t "$TAG_OBJECT")"
fi

if git ls-remote --exit-code --tags "$REMOTE" "refs/tags/${TAG}" >/dev/null 2>&1; then
  TAG_EXISTS_REMOTE=1
  REMOTE_TAG_OBJECT="$(git ls-remote --tags "$REMOTE" "refs/tags/${TAG}" | awk -v ref="refs/tags/${TAG}" '$2 == ref {print $1; exit}')"
  REMOTE_TAG_COMMIT="$(git ls-remote --tags "$REMOTE" "refs/tags/${TAG}^{}" | awk '{print $1}' | head -n1)"
  if [[ -z "$REMOTE_TAG_COMMIT" ]]; then
    REMOTE_TAG_COMMIT="$REMOTE_TAG_OBJECT"
  fi
fi

if [[ "$TAG_EXISTS_REMOTE" -eq 1 && "$TAG_EXISTS_LOCAL" -eq 0 ]]; then
  echo "      Fetching existing remote tag ${TAG}..."
  git fetch "$REMOTE" "refs/tags/${TAG}:refs/tags/${TAG}"
  TAG_EXISTS_LOCAL=1
  TAG_OBJECT="$(git rev-parse "refs/tags/${TAG}")"
  TAG_COMMIT="$(git rev-parse "${TAG}^{commit}")"
  TAG_OBJECT_TYPE="$(git cat-file -t "$TAG_OBJECT")"
fi

if [[ "$TAG_EXISTS_LOCAL" -eq 1 && "$TAG_OBJECT_TYPE" != "tag" ]]; then
  echo "ERROR: local tag ${TAG} is not an annotated tag (object type: ${TAG_OBJECT_TYPE})." >&2
  exit 1
fi

if [[ "$TAG_EXISTS_LOCAL" -eq 1 && "$TAG_COMMIT" != "$TARGET_COMMIT" ]]; then
  echo "ERROR: local tag ${TAG} points to ${TAG_COMMIT}, not ${REMOTE}/${BASE_BRANCH} (${TARGET_COMMIT})." >&2
  exit 1
fi

if [[ "$TAG_EXISTS_REMOTE" -eq 1 && "$REMOTE_TAG_COMMIT" != "$TARGET_COMMIT" ]]; then
  echo "ERROR: remote tag ${TAG} points to ${REMOTE_TAG_COMMIT}, not ${REMOTE}/${BASE_BRANCH} (${TARGET_COMMIT})." >&2
  exit 1
fi

if [[ "$TAG_EXISTS_LOCAL" -eq 1 && "$TAG_EXISTS_REMOTE" -eq 1 && "$TAG_OBJECT" != "$REMOTE_TAG_OBJECT" ]]; then
  echo "ERROR: local tag ${TAG} object ${TAG_OBJECT} differs from ${REMOTE} tag object ${REMOTE_TAG_OBJECT}." >&2
  echo "       Refusing to create a bundle from a local tag that does not exactly match the external Git tag." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "WARN: working tree has local changes. They are not included; bundle uses ${REMOTE}/${BASE_BRANCH} (${SHORT_COMMIT})." >&2
fi

if [[ "$TAG_EXISTS_LOCAL" -eq 1 ]]; then
  echo "[2/9] Reusing existing local tag ${TAG} at ${TARGET_COMMIT}..."
else
  echo "[2/9] Creating annotated tag ${TAG} at ${TARGET_COMMIT}..."
  git tag -a "$TAG" "$TARGET_COMMIT" -m "Release ${TAG}"
fi

if [[ "$TAG_EXISTS_REMOTE" -eq 1 ]]; then
  echo "[3/9] Remote tag ${TAG} already exists at ${TARGET_COMMIT}; skipping push."
else
  echo "[3/9] Pushing tag ${TAG} to ${REMOTE}..."
  git push "$REMOTE" "refs/tags/${TAG}"
fi

mkdir -p "$OUTPUT_DIR"
TARGET_DIR="$(cd "$(dirname "$RELEASE_NOTES_FILE")" && pwd)"
TARGET_ABS="${TARGET_DIR}/$(basename "$RELEASE_NOTES_FILE")"

if [[ "$RELEASE_NOTES_SOURCE" == "$TARGET_ABS" ]]; then
  echo "ERROR: RELEASE_NOTES_SOURCE must be a separate input file, not the generated artifact path: $RELEASE_NOTES_FILE" >&2
  exit 1
fi

rm -f "$BUNDLE_FILE" "$ZIP_FILE" "$MANIFEST_FILE" "$RELEASE_NOTES_FILE"

PREVIOUS_TAG="$(git tag --merged "$TARGET_COMMIT" --sort=-v:refname | grep -E '^v[0-9]+(\.[0-9]+){1,3}([-+][A-Za-z0-9._-]+)?$' | grep -F -x -v "$TAG" | head -n1 || true)"
if [[ -n "$PREVIOUS_TAG" ]]; then
  COMPARE_RANGE="${PREVIOUS_TAG}..${TAG}"
else
  COMPARE_RANGE="${TAG}"
fi

echo "[4/9] Creating release notes: ${RELEASE_NOTES_FILE}"
cp "$RELEASE_NOTES_SOURCE" "$RELEASE_NOTES_FILE"

GITHUB_RELEASE_URL=""
if [[ "${SKIP_GITHUB_RELEASE:-0}" == "1" ]]; then
  echo "[5/9] Skipping GitHub Release because SKIP_GITHUB_RELEASE=1."
else
  echo "[5/9] Creating/updating GitHub Release from release notes..."
  if ! command -v gh >/dev/null 2>&1; then
    echo "ERROR: gh CLI is required to create/update GitHub Release. Set SKIP_GITHUB_RELEASE=1 to create artifacts only." >&2
    exit 1
  fi

  if gh release view "$TAG" >/dev/null 2>&1; then
    gh release edit "$TAG" --title "$TAG" --notes-file "$RELEASE_NOTES_FILE"
  else
    gh release create "$TAG" --title "$TAG" --notes-file "$RELEASE_NOTES_FILE"
  fi
  GITHUB_RELEASE_URL="$(gh release view "$TAG" --json url --jq '.url')"
fi

echo "[6/9] Creating bundle: ${BUNDLE_FILE}"
git bundle create "$BUNDLE_FILE" "refs/tags/${TAG}"

echo "[7/9] Verifying bundle..."
git bundle verify "$BUNDLE_FILE"

echo "[8/9] Zipping bundle: ${ZIP_FILE}"
zip -j -9 "$ZIP_FILE" "$BUNDLE_FILE" "$IMPORT_SCRIPT" "$RELEASE_NOTES_FILE" >/dev/null
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
release_notes_file=$(basename "$RELEASE_NOTES_FILE")
previous_tag=${PREVIOUS_TAG:-}
compare_range=${COMPARE_RANGE}
github_release_url=${GITHUB_RELEASE_URL}
import_script=import_source_bundle.sh
EOF

echo "[9/9] Done."
echo "Tag commit : ${TARGET_COMMIT}"
echo "Previous   : ${PREVIOUS_TAG:-none}"
echo "Release    : ${GITHUB_RELEASE_URL:-skipped}"
echo "Bundle     : ${BUNDLE_FILE}"
echo "Bundle SHA : ${BUNDLE_SHA256}"
echo "Zip        : ${ZIP_FILE}"
echo "Zip SHA    : ${ZIP_SHA256}"
echo "Manifest   : ${MANIFEST_FILE}"
echo "Notes      : ${RELEASE_NOTES_FILE}"
