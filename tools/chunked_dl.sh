#!/bin/bash
# chunked_dl.sh — parallel ranged download with per-chunk retry, then concat
set -u
URL="$1"; OUT="$2"; TOTAL="$3"; NCHUNK=16
cd "$(dirname "$OUT")"
rm -f part_* "$OUT"
CHUNK=$(( (TOTAL + NCHUNK - 1) / NCHUNK ))
pids=()
for i in $(seq 0 $((NCHUNK-1))); do
  (
    S=$((i * CHUNK)); E=$(( (i+1)*CHUNK - 1 )); [ $E -ge $TOTAL ] && E=$((TOTAL-1))
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
cat part_$(printf %02d 0) part_$(printf %02d 1) part_$(printf %02d 2) part_$(printf %02d 3) \
    part_$(printf %02d 4) part_$(printf %02d 5) part_$(printf %02d 6) part_$(printf %02d 7) \
    part_$(printf %02d 8) part_$(printf %02d 9) part_$(printf %02d 10) part_$(printf %02d 11) \
    part_$(printf %02d 12) part_$(printf %02d 13) part_$(printf %02d 14) part_$(printf %02d 15) > "$OUT"
SZ=$(stat -c%s "$OUT"); echo "assembled $SZ / $TOTAL"
[ "$SZ" = "$TOTAL" ] && rm -f part_* && echo COMPLETE || exit 1

