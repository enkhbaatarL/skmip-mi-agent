#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  import_source_bundle.sh <tag> <bundle-or-bundle-zip> [target-branch] [import-branch]

Examples:
  bash import_source_bundle.sh v0.0.3 skmip-mi-agent-v0.0.3.bundle develop
  bash import_source_bundle.sh v0.0.3 skmip-mi-agent-v0.0.3.bundle.zip develop

Environment:
  REMOTE=origin
  AUTO_RESOLVE_THEIRS=1  # resolve all conflicts with GitHub tag side

What it does:
  1. Verify the bundle.
  2. Fetch and push the release tag.
  3. Create import/<tag> from origin/<target-branch>.
  4. Merge the tag into the import branch.
  5. Push the import branch for PR creation.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

TAG="${1:-}"
INPUT_FILE="${2:-}"
TARGET_BRANCH="${3:-develop}"
IMPORT_BRANCH="${4:-import/${TAG}}"
REMOTE="${REMOTE:-origin}"
AUTO_RESOLVE_THEIRS="${AUTO_RESOLVE_THEIRS:-0}"

if [[ -z "$TAG" || -z "$INPUT_FILE" ]]; then
  usage >&2
  exit 1
fi

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
