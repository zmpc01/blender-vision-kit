#!/usr/bin/env bash
# GitLab retry loop with WAF backoff (documented: ~1/3 of requests 403'd by WAF)
[ -f "$REPO_DIR/.env" ] && . "$REPO_DIR/.env" 2>/dev/null || { [ -f ".env" ] && . ./.env 2>/dev/null; true; }
GL_PAT="${GL_PAT:-${GITLAB_TOKEN:-GL_PAT_FROM_ENV}}"  # F2D-2: token home is .env
for i in 1 2 3 4 5 6; do
  code=$(curl -s -o /tmp/gl_user.json -w "%{http_code}" \
    -H "PRIVATE-TOKEN: ${GL_PAT}" "https://gitlab.com/api/v4/user")
  size=$(wc -c < /tmp/gl_user.json)
  echo "attempt $i: HTTP $code, body ${size} bytes"
  if [ "$code" = "200" ]; then
    python3 -c "import json;d=json.load(open('/tmp/gl_user.json'));print('login:',d.get('username'))"
    break
  fi
  [ $i -lt 6 ] && sleep $((i*5))
done
echo "--- body head (diagnostic only) ---"
head -c 300 /tmp/gl_user.json; echo
