#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPOSITORY_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

COMMAND=${1:-}
MODULE=${2:-}
REMOTE=${2:-origin}
BASE_BRANCH=${3:-dev}

CANONICAL_PATHS=(
    README.md
    docs/specs
    docs/reports
    docs/guides
    docs/contributions/README.md
)

usage() {
    cat <<'EOF'
Usage:
  ./scripts/docs-workflow.sh init <module>
  ./scripts/docs-workflow.sh sync [remote] [base-branch]
  ./scripts/docs-workflow.sh check [remote] [base-branch]
EOF
}

fail() {
    echo "$1" >&2
    exit 1
}

slugify() {
    printf '%s' "$1" \
        | tr '[:upper:]' '[:lower:]' \
        | sed -E 's#[^a-z0-9._-]+#-#g; s/^-+//; s/-+$//'
}

require_repository() {
    git -C "$REPOSITORY_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
        || fail "This command must run inside the ERP Git repository."
}

require_base_ref() {
    git -C "$REPOSITORY_DIR" rev-parse --verify "$REMOTE/$BASE_BRANCH" >/dev/null 2>&1 \
        || fail "Remote branch not found: $REMOTE/$BASE_BRANCH"
}

init_contribution() {
    [[ -n $MODULE ]] || fail "Module is required. Example: ./scripts/docs-workflow.sh init vacation"

    local branch_name module_slug branch_slug contribution_dir contribution_file
    branch_name=$(git -C "$REPOSITORY_DIR" branch --show-current)
    [[ -n $branch_name ]] || fail "A contribution document cannot be created from detached HEAD."

    module_slug=$(slugify "$MODULE")
    branch_slug=$(slugify "$branch_name")
    [[ -n $module_slug ]] || fail "Module must contain letters, numbers, '.', '_' or '-'."
    [[ -n $branch_slug ]] || fail "The current branch name cannot be converted to a document path."

    contribution_dir="$REPOSITORY_DIR/docs/contributions/$module_slug/$branch_slug"
    contribution_file="$contribution_dir/README.md"
    [[ ! -e $contribution_file ]] || fail "Contribution document already exists: $contribution_file"

    mkdir -p "$contribution_dir"
    cat >"$contribution_file" <<EOF
# $MODULE / $branch_name 기여 문서

- 대상 모듈: \`$MODULE\`
- 작업 브랜치: \`$branch_name\`
- 기준 브랜치: \`dev\`
- 상태: 작성 중

## 기능 범위

- 구현 범위:
- 제외 범위:

## 설계 결정

- 관련 규칙·기능 ID:
- 도메인·애플리케이션 결정:

## 인터페이스와 데이터 영향

- API·권한 변경:
- 스키마·migration 변경:
- 환경변수·인프라 영향:

## 검증

- 실행한 테스트:
- 남은 검증:

## 공용 문서 반영 후보

- Notion 원문:
- 저장소 명세·README:
EOF

    echo "Created: docs/contributions/$module_slug/$branch_slug/README.md"
}

sync_canonical_docs() {
    local changes
    changes=$(git -C "$REPOSITORY_DIR" status --porcelain -- "${CANONICAL_PATHS[@]}")
    [[ -z $changes ]] || {
        echo "$changes" >&2
        fail "Canonical documents have uncommitted changes. Commit or stash them before syncing."
    }

    git -C "$REPOSITORY_DIR" fetch "$REMOTE" "$BASE_BRANCH"
    require_base_ref
    git -C "$REPOSITORY_DIR" restore \
        --source "$REMOTE/$BASE_BRANCH" \
        --worktree \
        -- "${CANONICAL_PATHS[@]}"

    echo "Canonical documents were synchronized from $REMOTE/$BASE_BRANCH."
    echo "Review the diff and commit the synchronized files. Contribution drafts were preserved."
}

check_document_scope() {
    require_base_ref

    local changed_files
    changed_files=$(git -C "$REPOSITORY_DIR" diff \
        --name-only \
        "$REMOTE/$BASE_BRANCH" \
        HEAD \
        -- "${CANONICAL_PATHS[@]}")

    if [[ -n $changed_files ]]; then
        echo "$changed_files" >&2
        fail "This branch changes canonical documents. Move proposals under docs/contributions/."
    fi

    echo "Document scope check passed against $REMOTE/$BASE_BRANCH."
}

require_repository

case "$COMMAND" in
    init)
        init_contribution
        ;;
    sync)
        sync_canonical_docs
        ;;
    check)
        check_document_scope
        ;;
    *)
        usage
        exit 2
        ;;
esac
