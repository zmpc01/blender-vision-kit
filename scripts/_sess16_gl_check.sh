#!/usr/bin/env bash
# check GitLab PAT validity + push access
GL_PAT="glpat-sIgzJ9HToAXg0RUvSc6bMGM6MQpvOjEKdTpvajFzbQ8.01.170zp32lq"
echo "--- /api/v4/user ---"
curl -s -o /tmp/gl_user.json -w "%{http_code}\n" -H "PRIVATE-TOKEN: ${GL_PAT}" "https://gitlab.com/api/v4/user"
python3 -c "import json;d=json.load(open('/tmp/gl_user.json'));print(d.get('username') or d.get('message'))"
echo "--- project lookup (vision-kit) ---"
for slug in "ansgareutychisO%2Fblender-vision-kit" "ansgareutychisO%2Fblender-agent-kit"; do
  echo "== $slug =="
  curl -s -o /tmp/gl_proj.json -w "%{http_code}\n" -H "PRIVATE-TOKEN: ${GL_PAT}" "https://gitlab.com/api/v4/projects/${slug}"
  python3 -c "import json;d=json.load(open('/tmp/gl_proj.json'));print(d.get('path_with_namespace') or d.get('message'), '| visibility:', d.get('visibility'), '| can_push:', d.get('permissions',{}).get('project_access',{}) is not None)"
done
