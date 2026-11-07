"""Make a README thumbnail for a YouTube video: its own thumbnail with a play button, so the image links to the video.

  python3 docs/media/make_play_thumb.py <youtube id> <out.jpg> [--short]

GitHub READMEs cannot embed a player; a clickable thumbnail is the standard way. Needs Pillow."""
import io, sys, urllib.request
from PIL import Image, ImageDraw, ImageFilter

vid, out = sys.argv[1], sys.argv[2]
short = "--short" in sys.argv
img = None
for name in ("maxresdefault", "sddefault", "hqdefault"):
    try:
        data = urllib.request.urlopen(f"https://i.ytimg.com/vi/{vid}/{name}.jpg", timeout=20).read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        if img.width > 200:
            break
    except Exception:
        continue
if img is None:
    sys.exit("no thumbnail yet (YouTube may still be processing the video)")
if short:   # a Short: show it as a 9:16 card cut from the middle of the frame
    h = img.height; w = int(h * 9 / 16)
    img = img.crop(((img.width - w) // 2, 0, (img.width + w) // 2, h)).resize((360, 640))
else:
    img = img.resize((1280, 720))
W, H = img.size
r = int(min(W, H) * 0.13)
cx, cy = W // 2, H // 2
shadow = Image.new("L", img.size, 0)
ImageDraw.Draw(shadow).ellipse((cx - r - 6, cy - r - 2, cx + r + 6, cy + r + 10), fill=120)
img.paste((0, 0, 0), mask=shadow.filter(ImageFilter.GaussianBlur(10)))
d = ImageDraw.Draw(img)
d.rounded_rectangle((cx - int(r * 1.35), cy - r, cx + int(r * 1.35), cy + r), radius=int(r * 0.45), fill=(255, 0, 0))
t = int(r * 0.55)
d.polygon([(cx - t * 0.7, cy - t), (cx - t * 0.7, cy + t), (cx + t, cy)], fill=(255, 255, 255))
img.save(out, quality=88)
print(out, img.size)
