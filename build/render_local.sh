#!/bin/bash
# local share of the split render: wait for current s2 process, then s3, s4
cd /home/user/Animationvideo
while pgrep -f "render_shot.py s2_worry" >/dev/null; do sleep 5; done
for n in s2_worry s3_region s4_team; do
  /home/user/venv/bin/python src/blender/render_shot.py $n --samples 5 --res 540x960 --skip-existing 2>&1 | grep -E "DONE|rror"
done
echo LOCALDONE
