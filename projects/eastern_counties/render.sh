#!/bin/bash
# Renders all Eastern Counties Paving shots into renders/eastern_counties/<shot>/ (skips existing frames).
# Usage: PY=/path/to/python-with-bpy projects/eastern_counties/render.sh [pct] [samples]
set -e
cd "$(dirname "$0")/../.."
PY=${PY:-python3}
PCT=${1:-50}
SMP=${2:-10}
OUT=renders/eastern_counties
mkdir -p $OUT
[ -f $OUT/pavedetail/0001.png ] || $PY src/scene3d/eastern.py --shot pavedetail --pct 100 --samples 48 --out $OUT/pavedetail >/dev/null 2>&1
for s in $(python3 -c "import json;print(' '.join(f\"{x['id']}:{x['step']}\" for x in json.load(open('projects/eastern_counties/config/timeline.json'))['shots']))"); do
  id=${s%%:*}; st=${s##*:}
  $PY src/scene3d/eastern.py --shot $id --pct $PCT --samples $SMP --step $st --out $OUT/$id 2>&1 | grep --line-buffered "\] frame"
done
echo done
