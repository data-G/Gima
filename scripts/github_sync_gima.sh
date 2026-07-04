#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BRANCH="${GIMA_GITHUB_BRANCH:-codex/gima-whitepaper-and-upgrades}"
COMMIT_MESSAGE="${GIMA_GITHUB_COMMIT_MESSAGE:-Publish Gima upgrades and white paper}"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

cd "$ROOT"

command -v git >/dev/null || { print -u2 "git is required"; exit 1; }
GH_BIN="$(command -v gh || true)"
[[ -n "$GH_BIN" && -x "$GH_BIN" ]] || { print -u2 "GitHub CLI is required"; exit 1; }

if ! "$GH_BIN" auth status >/dev/null 2>&1; then
  print -u2 "GitHub login is required. Run: gh auth login --hostname github.com --git-protocol ssh --web"
  exit 2
fi

"$GH_BIN" auth setup-git

git remote get-url origin >/dev/null
git fetch origin

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git switch "$BRANCH"
else
  git switch -c "$BRANCH"
fi

git add \
  .gitattributes .gitignore .dockerignore Dockerfile README.md \
  "Start Gima.command" apps cloudbuild.yaml config.cloud.json \
  docs human_ai tests \
  scripts/*.mjs scripts/*.py scripts/*.sh

git diff --cached --check

if git grep --cached -nE '(sk-or-v1-[A-Za-z0-9_-]{20,}|sk-proj-[A-Za-z0-9_-]{16,}|sk-ant-api03-[A-Za-z0-9_-]{16,}|AIzaSy[A-Za-z0-9_-]{20,})' -- . \
  ':(exclude)tests/**'; then
  print -u2 "A possible API credential was found in staged files. Nothing was committed."
  exit 3
fi

if git diff --cached --quiet; then
  print "No source changes need publishing."
  exit 0
fi

git commit -m "$COMMIT_MESSAGE"
git push -u origin "$BRANCH"

if "$GH_BIN" pr view "$BRANCH" >/dev/null 2>&1; then
  "$GH_BIN" pr view "$BRANCH" --json url --jq .url
else
  "$GH_BIN" pr create \
    --draft \
    --base main \
    --head "$BRANCH" \
    --title "$COMMIT_MESSAGE" \
    --body-file docs/GITHUB_PR_BODY.md
fi

print "Gima is synchronized on branch: $BRANCH"
