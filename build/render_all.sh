#!/bin/bash
# Full-quality 3D render of every shot (resumable).
cd /home/user/Animationvideo
for n in $(python3 -c "import json;[print(x['name']) for x in json.load(open('config/timeline.json'))['shots']]"); do
  /home/user/venv/bin/python src/blender/render_shot.py $n --samples ${SAMPLES:-8} --res 540x960 --skip-existing 2>&1 | grep -E "DONE|rror" 
done
echo ALLDONE
