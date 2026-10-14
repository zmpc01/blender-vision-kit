#!/usr/bin/env bash
# ensure the vision-kit project exists on GitLab; create with API if missing
[ -f "$REPO_DIR/.env" ] && . "$REPO_DIR/.env" 2>/dev/null || { [ -f ".env" ] && . ./.env 2>/dev/null; true; }
GL_PAT="${GL_PAT:-${GITLAB_TOKEN:-GL_PAT_FROM_ENV}}"  # F2D-2: token home is .env
SLUG="ansgareutychisO%2Fblender-vision-kit"
for i in 1 2 3 4 5; do
  code=$(curl -s -o /tmp/gl_proj.json -w "%{http_code}" -H "PRIVATE-TOKEN: ${GL_PAT}" \
    "https://gitlab.com/api/v4/projects/${SLUG}")
  [ "$code" = "200" ] && break
  sleep $((i*4))
done
if [ "$code" = "200" ]; then
  python3 -c "import json;d=json.load(open('/tmp/gl_proj.json'));print('EXISTS:',d['path_with_namespace'],'default_branch:',d.get('default_branch'))"
else
  echo "lookup HTTP $code — attempting create"
  for i in 1 2 3 4 5; do
    code=$(curl -s -o /tmp/gl_create.json -w "%{http_code}" -H "PRIVATE-TOKEN: ${GL_PAT}" \
      -X POST "https://gitlab.com/api/v4/projects" \
      --data-urlencode "name=blender-vision-kit" \
      --data-urlencode "description=VISION-FIRST VARIANT of blender-agent-kit (mirror of zmpc01/blender-vision-kit; GitHub PAT dead session-16 — GitLab is authoritative)" \
      --data-urlencode "visibility=public")
    [ "$code" = "201" ] && break
    sleep $((i*4))
  done
  echo "create HTTP $code"
  python3 -c "import json;d=json.load(open('/tmp/gl_create.json'));print(d.get('path_with_namespace') or d.get('message'))"
fi
