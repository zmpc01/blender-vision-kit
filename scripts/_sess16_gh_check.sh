#!/usr/bin/env bash
# check PAT validity + repo access
GH_PAT="REDACTED-GITHUB-PAT-see-env"
echo "--- /user ---"
curl -s -o /tmp/gh_user.json -w "%{http_code}\n" -H "Authorization: token ${GH_PAT}" https://api.github.com/user
python3 -c "import json;d=json.load(open('/tmp/gh_user.json'));print(d.get('login') or d.get('message'))"
echo "--- repo access ---"
curl -s -o /tmp/gh_repo.json -w "%{http_code}\n" -H "Authorization: token ${GH_PAT}" https://api.github.com/repos/zmpc01/blender-vision-kit
python3 -c "import json;d=json.load(open('/tmp/gh_repo.json'));print(d.get('full_name') or d.get('message'), '| push:', d.get('permissions',{}).get('push'))"
echo "--- git credential test via ls-remote (auth URL) ---"
cd /home/z/repos/blender-vision-kit
GIT_TERMINAL_PROMPT=0 git ls-remote origin HEAD 2>&1 | head -3
echo "ls_remote_exit=$?"
