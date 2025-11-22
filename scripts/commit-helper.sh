#!/usr/bin/env bash
# commit-helper.sh
# Run pre-commit hooks in two passes (autofix first, strict second),
# stages changes, and commits. Honors GIT_COMMIT and GIT_ADD environment variables.

set -euo pipefail

# ----------------------
# Environment overrides
# ----------------------
GIT_COMMIT_CMD="${GIT_COMMIT:-git commit}"
GIT_ADD_CMD="${GIT_ADD:-git add}"
GIT_HELPER_FLAGS="${GIT_HELPER_FLAGS:-}"

# ----------------------
# Defaults
# ----------------------
STAGE_ALL=false
ARGS=()
SKIP_NEXT=false

# ----------------------
# Argument parsing
# ----------------------
while [[ $# -gt 0 ]]; do
    arg="$1"

    if $SKIP_NEXT; then
        # Preserve commit message after -m
        ARGS+=("$arg")
        SKIP_NEXT=false
        shift
        continue
    fi

    case "$arg" in
        -a|--all)
            STAGE_ALL=true
            ARGS+=("$arg")
            shift
            ;;
        -m)
            ARGS+=("$arg")
            shift
            if [[ $# -eq 0 ]]; then
                echo "Error: -m requires an argument"
                exit 1
            fi
            ARGS+=("$1")
            shift
            ;;
        -*)
            flags="${arg#-}"
            [[ "$flags" == *a* ]] && STAGE_ALL=true
            [[ "$flags" == *m* ]] && SKIP_NEXT=true
            ARGS+=("$arg")
            shift
            ;;
        *)
            ARGS+=("$arg")
            shift
            ;;
    esac
done

# ----------------------
# Stage all tracked changes if requested
# ----------------------
if $STAGE_ALL; then
    echo "Staging all tracked modifications due to -a/--all..."
    $GIT_ADD_CMD $GIT_HELPER_FLAGS -u
fi

# ----------------------
# Gather staged files
# ----------------------
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)
if [[ -z "$STAGED_FILES" ]]; then
    echo "No staged changes to commit."
    exit 0
fi

# ----------------------
# Stage 1: Run autofix hooks (allowed to modify files)
# ----------------------
AUTOFIX_HOOKS=("trailing-whitespace" "end-of-file-fixer")
echo "Running autofix pre-commit hooks..."
for hook in "${AUTOFIX_HOOKS[@]}"; do
    echo "  -> $hook"
    pre-commit run "$hook" --files $STAGED_FILES || true
done

# Re-stage any modifications made by autofix hooks
if [[ -n "$STAGED_FILES" ]]; then
    $GIT_ADD_CMD $GIT_HELPER_FLAGS $STAGED_FILES
fi

# ----------------------
# Final commit - runs all pre-commit hooks
# ----------------------
$GIT_COMMIT_CMD $GIT_HELPER_FLAGS "${ARGS[@]}"
