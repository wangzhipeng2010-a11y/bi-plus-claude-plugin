#!/usr/bin/env bash
# 本地 AI review：用本机 claude 审查 git diff origin/main...HEAD，输出四级报告。
# 来源：仿照 BIAIAgent/.agent/remote-claude-review.sh，去掉 SSH，改为本地执行，允许在 main 上运行。
set -euo pipefail

die() {
  echo "ERROR: $*" >&2
  exit 1
}

ROOT="$(git rev-parse --show-toplevel)" || die "当前不在 git 仓库里"
cd "$ROOT"

BASE_REMOTE="${AI_REVIEW_BASE_REMOTE:-origin}"
BASE_BRANCH="${AI_REVIEW_BASE_BRANCH:-main}"
BASE_REF="$BASE_REMOTE/$BASE_BRANCH"
LOCAL_REVIEW_DIR="${AI_REVIEW_LOCAL_REVIEW_DIR:-.agent/reviews}"
REQUEST_FILE="${AI_REVIEW_REQUEST_FILE:-.agent/review-request.md}"
CLAUDE_CMD="${AI_REVIEW_CLAUDE_CMD:-claude}"
CLAUDE_MODEL="${AI_REVIEW_CLAUDE_MODEL:-opus}"
CLAUDE_EFFORT_LEVEL="${AI_REVIEW_CLAUDE_EFFORT_LEVEL:-high}"
CLAUDE_PERMISSION_MODE="${AI_REVIEW_CLAUDE_PERMISSION_MODE:-}"
CLAUDE_TIMEOUT="${AI_REVIEW_CLAUDE_TIMEOUT:-1800}"

[[ -f "$REQUEST_FILE" ]] || die "缺少 review prompt: $REQUEST_FILE"
command -v "$CLAUDE_CMD" >/dev/null 2>&1 || die "找不到 claude 命令：$CLAUDE_CMD"
[[ "$CLAUDE_TIMEOUT" =~ ^[0-9]+$ ]] || die "AI_REVIEW_CLAUDE_TIMEOUT 必须是秒数: $CLAUDE_TIMEOUT"
[[ "$CLAUDE_PERMISSION_MODE" != "plan" ]] || die "AI_REVIEW_CLAUDE_PERMISSION_MODE=plan 不适合非交互式 review 报告输出"

branch="$(git symbolic-ref --quiet --short HEAD || echo HEAD)"

# 尝试更新基线；离线时退回本地已有的 origin/main 或本地 main，不致命。
if ! git fetch "$BASE_REMOTE" "+refs/heads/$BASE_BRANCH:refs/remotes/$BASE_REMOTE/$BASE_BRANCH" 2>/dev/null; then
  echo "WARN: 无法 fetch $BASE_REF，改用本地已有基线" >&2
fi
if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
  if git rev-parse --verify "$BASE_BRANCH" >/dev/null 2>&1; then
    BASE_REF="$BASE_BRANCH"
    echo "WARN: 找不到 $BASE_REMOTE/$BASE_BRANCH，改用本地分支 $BASE_BRANCH 作为基线" >&2
  else
    die "找不到基线 $BASE_REMOTE/$BASE_BRANCH，也没有本地 $BASE_BRANCH"
  fi
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "WARN: 有未提交改动；本次只审查已提交的增量（git diff $BASE_REF...HEAD）。建议先提交再 review。" >&2
fi

if git diff --quiet "$BASE_REF"...HEAD; then
  die "git diff $BASE_REF...HEAD 为空，没有可审查的增量（是否还没提交，或已与 $BASE_REF 一致？）"
fi

mkdir -p "$LOCAL_REVIEW_DIR"
safe_branch="$(printf '%s' "$branch" | LC_ALL=C sed 's#[^A-Za-z0-9_-]#_#g')"
[[ -n "$safe_branch" ]] || die "无法从分支名生成结果文件名: $branch"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)-$$"
local_result="$LOCAL_REVIEW_DIR/$safe_branch-$timestamp.md"
latest_result=".agent/latest-review.md"

prompt_file="$(mktemp)"
stderr_file="$(mktemp)"
trap 'rm -f "$prompt_file" "$stderr_file"' EXIT

{
  echo "## 本次实际基线"
  echo
  echo "- git diff $BASE_REF...HEAD"
  echo "- git log $BASE_REF..HEAD"
  echo
  cat "$REQUEST_FILE"
  echo
  echo "## git log $BASE_REF..HEAD"
  echo '```text'
  git log "$BASE_REF"..HEAD
  echo '```'
  echo
  echo "## git diff $BASE_REF...HEAD"
  echo '```diff'
  git diff "$BASE_REF"...HEAD
  echo '```'
} > "$prompt_file"

{
  echo "# Local Claude Review"
  echo
  echo "- Branch: $branch"
  echo "- Base: $BASE_REF"
  echo "- Generated: $(date -u +%Y%m%dT%H%M%SZ)"
  echo
} > "$local_result"

claude_args=("-p" "--model" "$CLAUDE_MODEL")
if [[ -n "$CLAUDE_EFFORT_LEVEL" ]]; then
  claude_args+=("--effort" "$CLAUDE_EFFORT_LEVEL")
  export CLAUDE_CODE_EFFORT_LEVEL="$CLAUDE_EFFORT_LEVEL"
fi
if [[ -n "$CLAUDE_PERMISSION_MODE" ]]; then
  claude_args+=("--permission-mode" "$CLAUDE_PERMISSION_MODE")
fi

echo "==> run local Claude review ($branch vs $BASE_REF)"
set +e
if command -v timeout >/dev/null 2>&1; then
  timeout "$CLAUDE_TIMEOUT" "$CLAUDE_CMD" "${claude_args[@]}" < "$prompt_file" >> "$local_result" 2> "$stderr_file"
elif command -v gtimeout >/dev/null 2>&1; then
  gtimeout "$CLAUDE_TIMEOUT" "$CLAUDE_CMD" "${claude_args[@]}" < "$prompt_file" >> "$local_result" 2> "$stderr_file"
else
  # macOS 默认没有 timeout/gtimeout，直接运行不设超时。
  "$CLAUDE_CMD" "${claude_args[@]}" < "$prompt_file" >> "$local_result" 2> "$stderr_file"
fi
claude_status=$?
set -e

if [[ "$claude_status" -ne 0 ]]; then
  {
    echo
    echo "## Claude Command Failed"
    echo
    echo '```text'
    echo "exit=$claude_status"
    stderr_lines="$(wc -l < "$stderr_file" | tr -d ' ')"
    if [[ "$stderr_lines" -gt 200 ]]; then
      echo "(showing first 200 lines of $stderr_lines)"
      sed -n '1,200p' "$stderr_file"
    else
      cat "$stderr_file"
    fi
    echo '```'
  } >> "$local_result"
fi

cp "$local_result" "$latest_result"

echo
echo "==> review saved: $local_result"
echo "==> latest copy: $latest_result"
echo
cat "$local_result"

exit "$claude_status"
