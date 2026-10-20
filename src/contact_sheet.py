"""Contact sheet of the finished video: one frame per second, 6 columns,
with timestamps. usage: python3 src/contact_sheet.py [video] [out.png]"""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
video = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "output",
                                                           "fenland_drives_patios_tiktok.mp4")
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "output", "contact_sheet.png")
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                     "-of", "csv=p=0", video]))
tw, th, cols = 270, 480, 6
times = [t + 0.5 for t in range(int(dur))]
rows = (len(times) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows * (th + 34)), (12, 12, 16))
f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 22)
with tempfile.TemporaryDirectory() as td:
    for i, t in enumerate(times):
        p = os.path.join(td, f"{i}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", video, "-frames:v",
                        "1", "-vf", f"scale={tw}:{th}", p], check=True)
        x, y = (i % cols) * tw, (i // cols) * (th + 34)
        sheet.paste(Image.open(p), (x, y + 34))
        ImageDraw.Draw(sheet).text((x + 8, y + 5), f"{t:05.2f}s", font=f, fill=(255, 140, 70))
sheet.save(out)
print("wrote", out)
