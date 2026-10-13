#!/usr/bin/env bash
# GitLab push with WAF retry (documented ~1/3 block rate)
cd /home/z/repos/blender-vision-kit
echo "--- fetch from gitlab ---"
for i in 1 2 3 4 5 6; do
  if git fetch gitlab main 2>/dev/null; then echo "fetch ok (attempt $i)"; break; fi
  echo "fetch attempt $i failed"; sleep $((i*3))
done
git log --oneline -1 gitlab/main 2>/dev/null || echo "gitlab/main: no ref"
echo "--- local vs gitlab ---"
git rev-list --left-right --count main...gitlab/main 2>/dev/null || true
echo "--- push with retry ---"
for i in 1 2 3 4 5 6 7 8; do
  if git push gitlab main 2>/tmp/glpush.err; then echo "PUSH OK (attempt $i)"; break; fi
  echo "push attempt $i failed:"; tail -2 /tmp/glpush.err
  [ $i -lt 8 ] && sleep $((i*4))
done
git log --oneline -1
