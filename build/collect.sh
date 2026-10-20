#!/bin/bash
# Pull frames pushed by the cloud render workers; trigger assembly when all present.
cd /home/user/Animationvideo
got=""
while true; do
  for b in frames-r1 frames-r2 frames-r3; do
    case " $got " in *" $b "*) continue;; esac
    if git fetch -q origin $b 2>/dev/null; then
      git archive origin/$b build/frames | tar -x && got="$got $b" && echo "pulled $b $(date +%T)"
    fi
  done
  missing=$(python3 -c "
import json,os
print(' '.join(s['name'] for s in json.load(open('config/timeline.json'))['shots']
  if not os.path.isdir('build/frames/'+s['name']) or len(os.listdir('build/frames/'+s['name']))!=s['frames']))")
  if [ -z "$missing" ]; then echo "all frames present $(date +%T)"; echo ALLDONE >> build/render_day.log; break; fi
  sleep 60
done
