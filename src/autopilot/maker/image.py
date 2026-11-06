"""A feed image (Instagram and Facebook): a headline card in the same themes as the videos."""
from __future__ import annotations

import html as _h
import re
import shutil
from pathlib import Path

import yaml

from . import render
from .spec import COLOUR, PRESETS

SIZES = {"portrait": (1080, 1350), "square": (1080, 1080)}
PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:%(W)dpx;height:%(H)dpx;overflow:hidden;font-family:%(font)s;color:%(fg)s;background:linear-gradient(160deg,%(bg)s,%(bg2)s)}
.blob{position:absolute;border-radius:50%%;filter:blur(110px);opacity:.38}
#a{width:820px;height:820px;background:%(accent)s;left:-160px;top:-200px}#b{width:700px;height:700px;background:%(accent2)s;right:-200px;bottom:-180px}
main{position:absolute;inset:0;padding:110px 90px;display:flex;flex-direction:column;justify-content:center;gap:40px}
.kicker{font-size:30px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:%(accent)s}
h1{font-size:%(h1)dpx;font-weight:800;letter-spacing:-.025em;line-height:1.08}
h1 em{font-style:normal;background:linear-gradient(90deg,%(accent)s,%(accent2)s);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{font-size:44px;line-height:1.3;color:%(muted)s;font-weight:500}
.logo{position:absolute;left:90px;top:80px;height:96px;width:auto}
footer{position:absolute;left:90px;right:90px;bottom:80px;font-size:32px;font-weight:700;color:%(muted)s;display:flex;justify-content:space-between}
</style></head><body><div class="blob" id="a"></div><div class="blob" id="b"></div>
%(logo)s<main>%(kicker)s<h1>%(headline)s</h1>%(sub)s</main><footer><span>%(footer)s</span><span>%(footer_r)s</span></footer></body></html>"""


def _rich(s):
    return re.sub(r"\*([^*]+)\*", r"<em>\1</em>", _h.escape(s))


def _logo(path):
    if not path:
        return ""
    import base64, mimetypes
    p = Path(path)
    return f'<img class="logo" src="data:{mimetypes.guess_type(p.name)[0] or "image/png"};base64,{base64.b64encode(p.read_bytes()).decode()}">'


def make(slug, headline, out_dir: Path, sub="", kicker="", footer="", footer_right="", preset="calm", size="portrait", theme=None, logo=None) -> Path:
    if size not in SIZES:
        raise ValueError("size must be portrait or square")
    th = {**PRESETS[preset], **(theme or {})}
    for k, v in th.items():
        if k in ("bg", "bg2", "fg", "muted", "accent", "accent2") and not COLOUR.match(v):
            raise ValueError(f"theme.{k} must be a #rrggbb colour")
    w, h = SIZES[size]
    n = len(headline)
    page = PAGE % {**th, "W": w, "H": h, "h1": 104 if n <= 40 else 88 if n <= 70 else 74,
                   "headline": _rich(headline), "sub": f'<div class="sub">{_rich(sub)}</div>' if sub else "",
                   "kicker": f'<div class="kicker">{_h.escape(kicker)}</div>' if kicker else "",
                   "footer": _h.escape(footer), "footer_r": _h.escape(footer_right), "logo": _logo(logo)}
    out_dir.mkdir(parents=True, exist_ok=True)
    html = out_dir / f"{slug}.html"
    html.write_text(page)
    png = out_dir / f"{slug}.png"
    sp = render._need_playwright()
    with sp() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": w, "height": h})
        pg.goto(html.resolve().as_uri())
        pg.wait_for_timeout(200)
        pg.screenshot(path=str(png))
        b.close()
    html.unlink()
    return png


def to_queue(slug, png: Path, queue_dir: Path, caption: str, link="") -> Path:
    d = queue_dir / slug
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(png, d / "image.png")
    item = {"kind": "image", "title": slug, "caption": caption, "files": {"image": "image.png"}}
    (d / "item.yml").write_text(yaml.safe_dump(item, sort_keys=False, allow_unicode=True))
    return d
