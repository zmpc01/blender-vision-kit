#!/bin/bash
# chunked_dl.sh — parallel ranged download with per-chunk retry, then concat
set -u
URL="$1"; OUT="$2"; TOTAL="$3"; NCHUNK=16
cd "$(dirname "$OUT")"
# F2E-18: dl_errors.log joins the start-of-run cleanup — a stale error log
# from a previous killed run must not survive into (or look like it
# belongs to) this one. (rm -f on a non-matching glob is a no-op.)
rm -f part_* dl_errors.log "$OUT"
CHUNK=$(( (TOTAL + NCHUNK - 1) / NCHUNK ))
pids=()
for i in $(seq 0 $((NCHUNK-1))); do
  (
    S=$((i * CHUNK)); E=$(( (i+1)*CHUNK - 1 )); [ $E -ge $TOTAL ] && E=$((TOTAL-1))
    # F2E-18: an early-exit chunk (S > E on files smaller than 16 chunks)
    # legitimately creates NO part file — the concat below must tolerate
    # that instead of hardcoding exactly 16 parts.
    [ $S -gt $E ] && exit 0
    for try in 1 2 3 4 5 6 7 8; do
      curl -s -r "$S-$E" --speed-time 20 --speed-limit 20000 --max-time 300 -o "part_$(printf %02d $i)" "$URL" && \
        [ "$(stat -c%s part_$(printf %02d $i) 2>/dev/null || echo 0)" = "$((E-S+1))" ] && exit 0
      sleep 2
    done
    echo "CHUNK $i FAILED" >> dl_errors.log
    exit 1
  ) &
  pids+=($!)
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=1; done
[ $fail -eq 1 ] && { echo "FAILED"; exit 1; }
# F2E-18: build the concat list from the parts that EXIST, in chunk order
# (printf %02d keeps lexical == numeric). The old hardcoded
# part_00..part_15 list failed `cat` for any file smaller than 16 chunks'
# worth — early-exit chunks never create their part.
parts=()
for i in $(seq 0 $((NCHUNK-1))); do
  p="part_$(printf %02d "$i")"
  [ -f "$p" ] && parts+=("$p")
done
if [ "${#parts[@]}" -eq 0 ]; then
  echo "FAILED: no chunk parts created (target $TOTAL bytes from $URL)"
  exit 1
fi
cat "${parts[@]}" > "$OUT"
SZ=$(stat -c%s "$OUT"); echo "assembled $SZ / $TOTAL"
[ "$SZ" = "$TOTAL" ] && rm -f part_* dl_errors.log && echo COMPLETE || exit 1
