#!/bin/bash
# dl_watchdog.sh — resilient Blender tarball download with stall-restart + resume
URL1="https://ftp.nluug.nl/pub/graphics/blender/release/Blender4.5/blender-4.5.13-linux-x64.tar.xz"
URL2="https://download.blender.org/release/Blender4.5/blender-4.5.13-linux-x64.tar.xz"
F="blender-4.5.13-linux-x64.tar.xz"
cd /home/z/blender-agent-kit/tools || exit 1
TARGET=$(curl -sI "$URL1" | grep -i content-length | tr -d '\r' | awk '{print $2}')
echo "target size: $TARGET" > /tmp/dl_watch.log
for i in $(seq 1 60); do
  SZ=$(stat -c%s "$F" 2>/dev/null || echo 0)
  if [ "$SZ" = "$TARGET" ] && [ -n "$TARGET" ]; then
    echo "COMPLETE $SZ" >> /tmp/dl_watch.log
    exit 0
  fi
  echo "attempt $i size $SZ" >> /tmp/dl_watch.log
  URL=$URL1; [ $((i % 2)) -eq 0 ] && URL=$URL2
  curl -sL -C - --speed-time 25 --speed-limit 2000 --max-time 240 -o "$F" "$URL" >> /tmp/dl_watch.log 2>&1
  sleep 2
done
echo "FAILED after 60 attempts" >> /tmp/dl_watch.log
