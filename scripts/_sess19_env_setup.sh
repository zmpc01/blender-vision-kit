#!/usr/bin/env bash
# session-19: restore authenticated remotes from .env (fresh sandbox).
set -euo pipefail
REPO_DIR="${1:-/home/z/repos/vision-kit}"
cd "$REPO_DIR"
[ -f .env ] && . ./.env
GH_PAT="${GITHUB_TOKEN:?GITHUB_TOKEN missing}"
GL_PAT="${GITLAB_TOKEN:?GITLAB_TOKEN missing}"
git remote set-url origin "https://${GH_PAT}@github.com/zmpc01/blender-vision-kit.git"
if git remote get-url gitlab >/dev/null 2>&1; then
  git remote set-url gitlab "https://oauth2:${GL_PAT}@gitlab.com/ansgareutychisO/blender-vision-kit.git"
else
  git remote add gitlab "https://oauth2:${GL_PAT}@gitlab.com/ansgareutychisO/blender-vision-kit.git"
fi
echo "[s19-setup] remotes set (tokens sourced from .env):"
git remote -v | sed 's/ghp_[A-Za-z0-9]*/ghp_***/g; s/glpat-[A-Za-z0-9.]*/glpat_***/g'
