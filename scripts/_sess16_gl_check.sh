#!/usr/bin/env bash
# check GitLab PAT validity + push access
[ -f "$REPO_DIR/.env" ] && . "$REPO_DIR/.env" 2>/dev/null || { [ -f ".env" ] && . ./.env 2>/dev/null; true; }
GL_PAT="${GL_PAT:-${GITLAB_TOKEN:-GL_PAT_FROM_ENV}}"  # F2D-2: token home is .env
echo "--- /api/v4/user ---"
curl -s -o /tmp/gl_user.json -w "%{http_code}\n" -H "PRIVATE-TOKEN: ${GL_PAT}" "https://gitlab.com/api/v4/user"
python3 -c "import json;d=json.load(open('/tmp/gl_user.json'));print(d.get('username') or d.get('message'))"
echo "--- project lookup (vision-kit) ---"
for slug in "ansgareutychisO%2Fblender-vision-kit" "ansgareutychisO%2Fblender-agent-kit"; do
  echo "== $slug =="
  curl -s -o /tmp/gl_proj.json -w "%{http_code}\n" -H "PRIVATE-TOKEN: ${GL_PAT}" "https://gitlab.com/api/v4/projects/${slug}"
  python3 -c "import json;d=json.load(open('/tmp/gl_proj.json'));print(d.get('path_with_namespace') or d.get('message'), '| visibility:', d.get('visibility'), '| can_push:', d.get('permissions',{}).get('project_access',{}) is not None)"
done
