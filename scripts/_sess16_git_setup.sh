#!/usr/bin/env bash
# session-16: set the authenticated remote URLs (GitHub + GitLab mirror).
# GIT IS THE DISK — this script restores auth after a fresh clone.
set -euo pipefail
REPO_DIR="${1:-/home/z/repos/blender-vision-kit}"
GH_PAT="REDACTED-GITHUB-PAT-see-env"
GL_PAT="glpat-sIgzJ9HToAXg0RUvSc6bMGM6MQpvOjEKdTpvajFzbQ8.01.170zp32lq"
cd "$REPO_DIR"
git remote set-url origin "https://${GH_PAT}@github.com/zmpc01/blender-vision-kit.git"
if git remote get-url gitlab >/dev/null 2>&1; then
  git remote set-url gitlab "https://oauth2:${GL_PAT}@gitlab.com/ansgareutychisO/blender-vision-kit.git"
else
  git remote add gitlab "https://oauth2:${GL_PAT}@gitlab.com/ansgareutychisO/blender-vision-kit.git"
fi
# also the sibling escape repo convention (if cloned later)
echo "[git-setup] remotes set:"
git remote -v | sed 's/ghp_[A-Za-z0-9]*/ghp_***/; s/glpat-[A-Za-z0-9.]*/glpat_***/'
