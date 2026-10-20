#!/bin/bash
# Renders every 3D shot into renders/<shot>/NNNN.png (already-rendered frames are skipped).
# Usage: PY=/path/to/python-with-bpy ./render_all.sh [pct] [samples]
set -e
cd "$(dirname "$0")"
PY=${PY:-python3}
PCT=${1:-50}
SMP=${2:-10}
mkdir -p renders
r() { $PY src/scene3d/shots.py --shot "$1" --pct $PCT --samples $SMP --out renders/$1 ${2:+--step $2} 2>&1 | grep --line-buffered "\] frame" ; }
[ -f renders/roofdetail/0001.png ] || $PY src/scene3d/shots.py --shot roofdetail --pct 100 --samples 48 --out renders/roofdetail >/dev/null 2>&1
# slow, mostly-static shots render on twos; the compositor blends the in-betweens
for s in s1 s2a s3 s4 s5b s5c s6a; do r $s; done
for s in s2b s5a s6b s7; do r $s 2; done
echo done
