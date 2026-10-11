#!/bin/bash
# push_both.sh — GitHub first (source of truth), GitLab retried in the
# background (the WAF 403s ~1/3 of HK IPs; probabilistic, never fatal).
# NEVER force. On GitHub rejection: fetch + rebase + retry once, then
# report.
set -u
cd "$(dirname "$0")/.."   # repo root (scripts/ parent)
REPO=$(pwd)
FAIL=0
for i in 1 2 3; do
  if git push origin main 2>/tmp/gh_push.err; then break; fi
  if [ $i -eq 3 ]; then FAIL=1; echo "[push] GITHUB FAILED:"; tail -3 /tmp/gh_push.err; break; fi
  echo "[push] GitHub rejected — fetch+rebase, retry $i"
  git fetch origin || true
  git rebase origin/main || { FAIL=1; echo "[push] rebase conflict — STOP, manual"; exit 2; }
done
if [ "$FAIL" -eq 0 ]; then echo "[push] GitHub ok $(git rev-parse --short HEAD)"; fi
( for i in $(seq 1 8); do
    git push gitlab main 2>/dev/null && { echo "[push] GitLab ok $(git rev-parse --short HEAD)"; exit 0; }
    sleep 5
  done
  echo "[push] GitLab gave up after 8 tries (WAF) — non-fatal" ) &
echo "[push] done (GitLab retrying in background)"
