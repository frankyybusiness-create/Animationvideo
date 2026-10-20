#!/bin/bash
# Keeps the long render going: restarts it if it is not running, exits when it reports "done".
cd "$(dirname "$0")/../.."
LOG=renders/ec_1080/render.log
while true; do
  if grep -q "^done" $LOG 2>/dev/null; then echo "RENDER DONE"; exit 0; fi
  if ! ps -eo args | grep -q "^/bin/bash projects/eastern_counties/render.s[h]"; then
    echo "starting render $(date -u +%H:%M)"
    PY=${PY} setsid nohup projects/eastern_counties/render.sh 100 6 >> $LOG 2>&1 < /dev/null &
  fi
  sleep 60
done
