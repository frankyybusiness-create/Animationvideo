#!/bin/bash
# low-res preview of first/mid/last frames of each shot
cd /home/user/Animationvideo
for s in $(python3 -c "import json;[print(x['name'],x['frames']) for x in json.load(open('config/timeline.json'))['shots']]" | tr ' ' ':'); do
  n=${s%%:*}; f=${s##*:}; m=$((f/2)); 
  /home/user/venv/bin/python src/blender/render_shot.py $n --frames 1,$m,$f --samples 4 --res 270x480 --out build/preview 2>&1 | grep -E "DONE|Error|rror:|line [0-9]+," | head -6
done
