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
  release-artifacts/<repo>-<tag>.bundle.zip  # contains only the bundle and self-contained versioned import sh

Environment:
  RELEASE_NOTES_SOURCE=<file>  Required. Prewritten release notes used directly for GitHub Release
  SKIP_GITHUB_RELEASE=1        Create artifacts only; do not create/update GitHub Release
  TARGET_BRANCH=develop        Default target branch embedded in the versioned import script
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

TAG="${1:-}"
BASE_BRANCH="${2:-main}"
TARGET_BRANCH="${TARGET_BRANCH:-develop}"
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
ZIP_FILE="${OUTPUT_DIR}/${REPO_NAME}-${TAG}.bundle.zip"

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

PREVIOUS_TAG="$(git tag --merged "$TARGET_COMMIT" --sort=-v:refname | grep -E '^v[0-9]+(\.[0-9]+){1,3}([-+][A-Za-z0-9._-]+)?$' | grep -F -x -v "$TAG" | head -n1 || true)"

GITHUB_RELEASE_URL=""
if [[ "${SKIP_GITHUB_RELEASE:-0}" == "1" ]]; then
  echo "[4/9] Skipping GitHub Release because SKIP_GITHUB_RELEASE=1."
else
  echo "[4/9] Creating/updating GitHub Release from release notes..."
  if ! command -v gh >/dev/null 2>&1; then
    echo "ERROR: gh CLI is required to create/update GitHub Release. Set SKIP_GITHUB_RELEASE=1 to create artifacts only." >&2
    exit 1
  fi

  if gh release view "$TAG" >/dev/null 2>&1; then
    gh release edit "$TAG" --title "$TAG" --notes-file "$RELEASE_NOTES_SOURCE"
  else
    gh release create "$TAG" --title "$TAG" --notes-file "$RELEASE_NOTES_SOURCE"
  fi
  GITHUB_RELEASE_URL="$(gh release view "$TAG" --json url --jq '.url')"
fi

echo "[5/9] Removing previous generated artifacts from ${OUTPUT_DIR}..."
mkdir -p "$OUTPUT_DIR"
find "$OUTPUT_DIR" -maxdepth 1 -type f \( \
  -name "${REPO_NAME}-*.bundle" -o \
  -name "${REPO_NAME}-*.bundle.zip" -o \
  -name "${REPO_NAME}-*.manifest.txt" -o \
  -name "${REPO_NAME}-*.release-notes.md" -o \
  -name 'import_source_bundle_*.sh' \
\) -delete

STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mi-source-banib.XXXXXX")"
cleanup() {
  rm -rf "$STAGING_DIR"
}
trap cleanup EXIT

BUNDLE_FILE="${STAGING_DIR}/${REPO_NAME}-${TAG}.bundle"
VERSIONED_IMPORT_SCRIPT="${STAGING_DIR}/import_source_bundle_${TAG}.sh"

echo "[6/9] Creating bundle: $(basename "$BUNDLE_FILE")"
git bundle create "$BUNDLE_FILE" "refs/tags/${TAG}"

echo "[7/9] Verifying bundle..."
git bundle verify "$BUNDLE_FILE"

echo "[8/9] Creating self-contained import script: $(basename "$VERSIONED_IMPORT_SCRIPT")"
{
  cat <<'IMPORT_SCRIPT_HEADER'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMPORT_SCRIPT_HEADER
  printf 'DEFAULT_TAG=%q\n' "$TAG"
  printf 'DEFAULT_BUNDLE=%q\n' "$(basename "$BUNDLE_FILE")"
  printf 'DEFAULT_TARGET_BRANCH=%q\n' "$TARGET_BRANCH"
  cat <<'IMPORT_SCRIPT_BODY'

usage() {
  cat <<USAGE
Usage:
  bash $(basename "$0") [tag] [bundle-or-bundle-zip] [target-branch] [import-branch]

Defaults:
  tag           ${DEFAULT_TAG}
  bundle        ${DEFAULT_BUNDLE}
  target branch ${DEFAULT_TARGET_BRANCH}
  import branch import/<tag>

Environment:
  REMOTE=origin
  AUTO_RESOLVE_THEIRS=1  # resolve all conflicts with GitHub tag side
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

TAG="${1:-$DEFAULT_TAG}"
INPUT_FILE="${2:-${SCRIPT_DIR}/${DEFAULT_BUNDLE}}"
TARGET_BRANCH="${3:-$DEFAULT_TARGET_BRANCH}"
IMPORT_BRANCH="${4:-import/${TAG}}"
REMOTE="${REMOTE:-origin}"
AUTO_RESOLVE_THEIRS="${AUTO_RESOLVE_THEIRS:-0}"

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"

if git rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then
  echo "ERROR: a merge is already in progress. Resolve or abort it first." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "ERROR: tracked files have local changes. Commit or restore them first." >&2
  git status --short --untracked-files=no
  exit 1
fi

resolve_path() {
  local path="$1"
  if [[ "$path" = /* || "$path" =~ ^[A-Za-z]:[\\/] ]]; then
    echo "$path"
  else
    echo "$PWD/$path"
  fi
}

INPUT_FILE="$(resolve_path "$INPUT_FILE")"
if [[ ! -f "$INPUT_FILE" ]]; then
  echo "ERROR: file not found: $INPUT_FILE" >&2
  exit 1
fi

TMP_DIR=""
cleanup() {
  if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

BUNDLE_FILE="$INPUT_FILE"
if [[ "$INPUT_FILE" == *.zip ]]; then
  TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t mi-source-import)"
  unzip -q "$INPUT_FILE" -d "$TMP_DIR"
  mapfile -t BUNDLE_FILES < <(find "$TMP_DIR" -type f -name "*.bundle" | sort)
  if [[ "${#BUNDLE_FILES[@]}" -ne 1 ]]; then
    echo "ERROR: expected exactly one .bundle in zip, found ${#BUNDLE_FILES[@]}." >&2
    exit 1
  fi
  BUNDLE_FILE="${BUNDLE_FILES[0]}"
fi

echo "[1/6] Verifying bundle..."
git bundle verify "$BUNDLE_FILE"

echo "[2/6] Fetching tag ${TAG}..."
BUNDLE_TAG_OBJECT="$(git bundle list-heads "$BUNDLE_FILE" "refs/tags/${TAG}" | awk '$2 == "refs/tags/'"$TAG"'" { print $1 }')"
if [[ -z "$BUNDLE_TAG_OBJECT" ]]; then
  echo "ERROR: bundle does not contain refs/tags/${TAG}" >&2
  exit 1
fi

if git show-ref --verify --quiet "refs/tags/${TAG}"; then
  LOCAL_TAG_OBJECT="$(git rev-parse "refs/tags/${TAG}")"
  if [[ "$LOCAL_TAG_OBJECT" != "$BUNDLE_TAG_OBJECT" ]]; then
    echo "ERROR: local tag ${TAG} already exists but differs from bundle." >&2
    exit 1
  fi
  echo "Local tag ${TAG} already exists; skipping tag fetch."
else
  git fetch "$BUNDLE_FILE" "refs/tags/${TAG}:refs/tags/${TAG}"
fi

echo "[3/6] Pushing tag ${TAG} to ${REMOTE}..."
git push "$REMOTE" "refs/tags/${TAG}:refs/tags/${TAG}"

echo "[4/6] Creating import branch ${IMPORT_BRANCH} from ${REMOTE}/${TARGET_BRANCH}..."
git fetch "$REMOTE"
if ! git rev-parse --verify "refs/remotes/${REMOTE}/${TARGET_BRANCH}" >/dev/null 2>&1; then
  echo "ERROR: remote target branch not found: ${REMOTE}/${TARGET_BRANCH}" >&2
  echo "Create it first, for example:" >&2
  echo "  git checkout -b ${TARGET_BRANCH} ${REMOTE}/master" >&2
  echo "  git push ${REMOTE} ${TARGET_BRANCH}" >&2
  exit 1
fi

if git show-ref --verify --quiet "refs/heads/${IMPORT_BRANCH}"; then
  echo "ERROR: local branch already exists: ${IMPORT_BRANCH}" >&2
  echo "Delete it or pass a different import branch name." >&2
  exit 1
fi

git checkout --no-track -b "$IMPORT_BRANCH" "${REMOTE}/${TARGET_BRANCH}"

echo "[5/6] Merging tag ${TAG}..."
set +e
git merge --allow-unrelated-histories --no-ff "$TAG" -m "Import GitHub tag ${TAG}"
MERGE_EXIT=$?
set -e

if [[ "$MERGE_EXIT" -ne 0 ]]; then
  mapfile -t CONFLICTS < <(git diff --name-only --diff-filter=U)
  if [[ "${#CONFLICTS[@]}" -eq 0 ]]; then
    echo "ERROR: merge failed without conflict files. Check git status." >&2
    exit "$MERGE_EXIT"
  fi

  if [[ "$AUTO_RESOLVE_THEIRS" != "1" ]]; then
    echo "Merge conflicts detected."
    echo "Resolve in VSCode, then run:"
    echo "  git add <resolved-files>"
    echo "  git commit"
    echo "  git push -u ${REMOTE} HEAD:refs/heads/${IMPORT_BRANCH}"
    echo
    echo "If GitHub tag files should win for all conflicts:"
    echo "  git diff --name-only --diff-filter=U | while IFS= read -r path; do git checkout --theirs -- \"\$path\"; git add -- \"\$path\"; done"
    echo "  git commit"
    exit 1
  fi

  echo "Auto-resolving conflicts with GitHub tag side (--theirs)..."
  for path in "${CONFLICTS[@]}"; do
    git checkout --theirs -- "$path"
    git add -- "$path"
  done
  git commit --no-edit
fi

echo "[6/6] Pushing import branch..."
git push -u "$REMOTE" "HEAD:refs/heads/${IMPORT_BRANCH}"

REMOTE_URL="$(git remote get-url "$REMOTE" || true)"
COMPARE_URL=""
if [[ "$REMOTE_URL" =~ ^https?:// ]]; then
  BASE_URL="${REMOTE_URL%.git}"
  COMPARE_URL="${BASE_URL}/compare/${TARGET_BRANCH}...${IMPORT_BRANCH}"
fi

echo
echo "Done."
echo "Create PR:"
echo "  source: ${IMPORT_BRANCH}"
echo "  target: ${TARGET_BRANCH}"
echo "  merge : Create merge commit"
if [[ -n "$COMPARE_URL" ]]; then
  echo "  url   : ${COMPARE_URL}"
fi

IMPORT_SCRIPT_BODY
} > "$VERSIONED_IMPORT_SCRIPT"
chmod +x "$VERSIONED_IMPORT_SCRIPT"

echo "[9/9] Zipping final artifact: ${ZIP_FILE}"
zip -j -9 "$ZIP_FILE" "$BUNDLE_FILE" "$VERSIONED_IMPORT_SCRIPT" >/dev/null

ZIP_ENTRY_COUNT="$(unzip -Z1 "$ZIP_FILE" | wc -l | tr -d ' ')"
if [[ "$ZIP_ENTRY_COUNT" != "2" ]]; then
  echo "ERROR: expected exactly two files in zip, found ${ZIP_ENTRY_COUNT}." >&2
  exit 1
fi
unzip -Z1 "$ZIP_FILE" | grep -F -x "$(basename "$BUNDLE_FILE")" >/dev/null
unzip -Z1 "$ZIP_FILE" | grep -F -x "$(basename "$VERSIONED_IMPORT_SCRIPT")" >/dev/null

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

echo "Done."
echo "Tag commit : ${TARGET_COMMIT}"
echo "Previous   : ${PREVIOUS_TAG:-none}"
echo "Release    : ${GITHUB_RELEASE_URL:-skipped}"
echo "Bundle SHA : ${BUNDLE_SHA256}"
echo "Zip        : ${ZIP_FILE}"
echo "Zip SHA    : ${ZIP_SHA256}"
