"""The built-in scene: one HTML page whose `renderAt(t)` draws the frame for time t, deterministically
(no clocks, no randomness), so any frame can be rendered on its own, in any order, by any worker."""
from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="video-size" content="__W__x__H__">
<style>
  :root { --bg:__bg__; --bg2:__bg2__; --fg:__fg__; --muted:__muted__; --accent:__accent__; --accent2:__accent2__; --u:__U__px; }
  * { box-sizing:border-box; margin:0; padding:0; }
  html,body { width:__W__px; height:__H__px; overflow:hidden; background:var(--bg); font-family:__font__; color:var(--fg); }
  #bg { position:absolute; inset:0; background:linear-gradient(160deg,var(--bg) 0%,var(--bg2) 100%); }
  .blob { position:absolute; border-radius:50%; filter:blur(calc(var(--u)*90)); opacity:.35; }
  #b1 { width:calc(var(--u)*900); height:calc(var(--u)*900); background:var(--accent); }
  #b2 { width:calc(var(--u)*760); height:calc(var(--u)*760); background:var(--accent2); }
  .scene { position:absolute; left:calc(var(--u)*__PADX__); right:calc(var(--u)*__PADX__); top:calc(var(--u)*__TOP__); bottom:calc(var(--u)*__BOTTOM__);
           display:flex; flex-direction:column; justify-content:center; gap:calc(var(--u)*34); opacity:0; }
  h1 { font-size:calc(var(--u)*__H1__); font-weight:800; letter-spacing:-.025em; line-height:1.06; }
  h1 em { font-style:normal; background:linear-gradient(90deg,var(--accent),var(--accent2)); -webkit-background-clip:text; background-clip:text; color:transparent; }
  .sub { font-size:calc(var(--u)*__SUB__); color:var(--muted); line-height:1.3; font-weight:500; }
  ul { list-style:none; display:flex; flex-direction:column; gap:calc(var(--u)*22); }
  li { display:flex; align-items:center; gap:calc(var(--u)*26); padding:calc(var(--u)*26) calc(var(--u)*32); border-radius:calc(var(--u)*28);
       background:color-mix(in srgb,var(--fg) 9%,transparent); border:calc(var(--u)*2) solid color-mix(in srgb,var(--fg) 14%,transparent);
       font-size:calc(var(--u)*__LI__); font-weight:600; line-height:1.2; opacity:0; }
  li b { flex:none; width:calc(var(--u)*64); height:calc(var(--u)*64); border-radius:50%; display:grid; place-items:center;
         background:linear-gradient(135deg,var(--accent),var(--accent2)); color:var(--bg); font-size:calc(var(--u)*34); font-weight:800; }
  img.pic { max-width:100%; max-height:calc(var(--u)*__IMGH__); border-radius:calc(var(--u)*28); object-fit:contain; align-self:center; }
  #cap { position:absolute; left:calc(var(--u)*__PADX__); right:calc(var(--u)*__PADX__); bottom:calc(var(--u)*__CAPB__); text-align:center;
         font-size:calc(var(--u)*__CAP__); font-weight:700; line-height:1.25; opacity:0; text-shadow:0 calc(var(--u)*3) calc(var(--u)*18) rgba(0,0,0,.45); }
  #logo { position:absolute; left:calc(var(--u)*__PADX__); top:calc(var(--u)*56); height:calc(var(--u)*84); width:auto; border-radius:calc(var(--u)*16); }
  #bar { position:absolute; left:0; top:0; height:calc(var(--u)*10); background:linear-gradient(90deg,var(--accent),var(--accent2)); width:0; }
</style></head>
<body>
<div id="bg"><div class="blob" id="b1"></div><div class="blob" id="b2"></div></div>
__LOGO__<div id="stage"></div><div id="cap"></div><div id="bar"></div>
<script>
const SPEC = __SPEC__;
const TIMING = __TIMING__;
const TOTAL = TIMING.total;
const W = __W__, H = __H__;
const ease = x => { x = Math.max(0, Math.min(1, x)); return 1 - Math.pow(1 - x, 3); };
const stage = document.getElementById('stage'), cap = document.getElementById('cap');
const nodes = {};
function esc(s) { return String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
function rich(s) { return esc(s).replace(/\*([^*]+)\*/g, '<em>$1</em>'); }   // *word* gets the accent gradient
for (const sc of SPEC.scenes) {
  const d = document.createElement('div'); d.className = 'scene';
  let h = '';
  if (sc.headline) h += '<h1>' + rich(sc.headline) + '</h1>';
  if (sc.sub) h += '<div class="sub">' + rich(sc.sub) + '</div>';
  if (sc.image) h += '<img class="pic" src="' + sc.image + '">';
  if (sc.bullets) h += '<ul>' + sc.bullets.map((b, i) => '<li><b>' + (i + 1) + '</b><span>' + rich(b) + '</span></li>').join('') + '</ul>';
  d.innerHTML = h; stage.appendChild(d); nodes[sc.id] = d;
}
window.init = async () => { await document.fonts.ready; await Promise.all([...document.images].map(i => i.decode().catch(() => 0))); };
function renderAt(t) {
  document.getElementById('b1').style.transform = 'translate(' + (W * (.05 + .10 * Math.sin(t / 7))) + 'px,' + (H * (.02 + .08 * Math.cos(t / 9))) + 'px)';
  document.getElementById('b2').style.transform = 'translate(' + (W * (.45 + .10 * Math.cos(t / 8))) + 'px,' + (H * (.55 + .08 * Math.sin(t / 6))) + 'px)';
  document.getElementById('bar').style.width = (100 * Math.max(0, Math.min(1, t / TOTAL))) + '%';
  let line = null;
  for (const sc of SPEC.scenes) {
    const [s0, s1] = TIMING.scenes[sc.id], el = nodes[sc.id], lines = TIMING.beats[sc.id];
    const vis = ease((t - s0) / .5) * ease((s1 - t) / .45);
    el.style.opacity = vis;
    const h1 = el.querySelector('h1'), sub = el.querySelector('.sub'), pic = el.querySelector('.pic');
    if (h1) h1.style.transform = 'translateY(' + ((1 - ease((t - s0 - .1) / .6)) * 30) + 'px)';
    if (sub) { sub.style.opacity = ease((t - s0 - .5) / .6); }
    if (pic) pic.style.opacity = ease((t - s0 - .2) / .6);
    el.querySelectorAll('li').forEach((li, i) => {
      const tb = (lines[Math.min(i, lines.length - 1)]).t0, p = ease((t - tb + .1) / .5);
      li.style.opacity = p; li.style.transform = 'translateX(' + ((1 - p) * -60) + 'px)';
    });
    if (vis > 0) for (const l of lines) if (t >= l.t0 - .05 && t <= l.t1 + .35) line = [l.text, ease((t - l.t0 + .05) / .25) * ease((l.t1 + .35 - t) / .25)];
  }
  if (SPEC.captions && line) { cap.textContent = line[0]; cap.style.opacity = line[1]; } else cap.style.opacity = 0;
}
renderAt(0);
</script></body></html>
"""


def _data_uri(path: Path) -> str:
    return f"data:{mimetypes.guess_type(path.name)[0] or 'image/png'};base64," + base64.b64encode(path.read_bytes()).decode()


def build(spec, timing: dict) -> str:
    w, h = spec.size
    portrait = h > w
    u = min(w, h) / 1080
    vals = {  # layout per orientation; the caption band sits clear of each platform's own buttons
        "PADX": 80 if portrait else 140, "TOP": 150 if portrait else 90, "BOTTOM": 560 if portrait else 250,
        "CAPB": 330 if portrait else 90, "CAP": 46 if portrait else 40, "H1": 104 if portrait else 96,
        "SUB": 46 if portrait else 40, "LI": 44 if portrait else 40, "IMGH": 700 if portrait else 500,
    }
    scenes = []
    for sc in spec.all_scenes():
        v = {k: sc.get(k) for k in ("id", "headline", "sub", "bullets")}
        if sc.get("image"):
            v["image"] = _data_uri(spec.base / sc["image"])
        scenes.append(v)
    page = PAGE
    for k, val in {**vals, **spec.theme, "W": w, "H": h, "U": round(u, 4)}.items():
        page = page.replace(f"__{k}__", str(val))
    page = page.replace("__LOGO__", f'<img id="logo" src="{_data_uri(spec.logo)}">' if spec.logo else "")
    page = page.replace("__font__", spec.theme["font"]).replace("__SPEC__", _js({"scenes": scenes, "captions": spec.captions})).replace("__TIMING__", _js(timing))
    return page


def _js(o) -> str:
    return json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
