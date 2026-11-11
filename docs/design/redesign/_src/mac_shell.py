from common import *

import os
OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "macos", "cupertino"))
PAGES = {}   # name -> (html, width, height)

def doc(title, body):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="cupertino.css"></head>
<body>
{body}
</body></html>'''

NAV = [("home","Home","home"),("library","Library","library")]
DISC = [("sparkles","New","new"),("radar","Gap Radar","gap"),("graph","Connections","connections"),("timeline","Timeline","timeline"),("map","Atlas","atlas"),("bulb","Insights","insights")]
TOOLS = [("wand","Smart Playlists","smart"),("download","Downloads","downloads"),("gear","Settings","settings")]

def sidebar(active, playing=True, downloads=2):
    def row(icon, label, key, sub=False):
        on = " on" if key == active else ""
        badge = f'<span class="badge acc">{downloads}</span>' if key == "downloads" and downloads else ""
        return f'<div class="sb-row{on}{" sub" if sub else ""}">{ico(icon,16)}<span>{label}</span>{badge}</div>'
    h = '<div class="lights"><i></i><i></i><i></i></div>'
    h += "".join(row(i,l,k) for i,l,k in NAV)
    h += f'<div class="sb-head">{ico("chevd",10,2.4)}Discover</div>'
    h += "".join(row(i,l,k,True) for i,l,k in DISC)
    h += '<div style="height:16px"></div>'
    h += "".join(row(i,l,k) for i,l,k in TOOLS)
    if not playing:
        h += '<div class="sb-head">Playlists</div>'
        for n in ["Late night, slow", "Unplayed since 2024", "Jazz before 1975"]:
            h += f'<div class="sb-row">{ico("note",16)}<span>{n}</span></div>'
    return f'<div class="sidebar{" playing" if playing else ""}">{h}</div>'

def status_btn(kind="ok", label="All working"):
    icon = {"ok":"checkc","wa":"warn","da":"xc","off":"info"}[kind]
    return f'<div class="glassbtn status"><span class="st {kind}">{ico(icon,16,2)}</span>{label}</div>'

def toolbar(status=("ok","All working"), queue=False):
    return (f'<div class="toolbar{" q" if queue else ""}">{status_btn(*status)}'
            f'<div class="glassbtn search">{ico("search",16)}Search&nbsp;&nbsp;⌘K</div>'
            f'<div class="glassbtn round" style="{"color:var(--accent)" if queue else ""}">{ico("list",16)}</div></div>')

def player(playing=True, label="Home network · Tailscale"):
    if not playing:
        return (f'<div class="player idle"></div>'
                f'<div class="conn"><span class="st ok">{ico("checkc",12,2.2)}</span>{label}</div>')
    return (f'<div class="player"><div class="meta"><b>After the Flood</b><span>Talk Talk · Laughing Stock</span></div>'
            f'<div class="mid">“Shake my head, turn my face to the floor”</div>'
            f'<div class="ctl">{ico("shuffle",16)}{ico("prev",20)}{ico("pause",28)}{ico("next",20)}{ico("heart",16)}</div>'
            f'<div class="time">3:12 / 9:39</div><div class="bar"><i></i></div></div>'
            f'<div class="slot" style="background:{cover_bg("laughing")}"></div>')

def window(name, title, active, content, h=832, playing=True, status=("ok","All working"), overlay="", queue=False, banner=""):
    q = '<div class="queue"><div class="t-title3">Up Next</div></div>' if queue else ""
    body = (f'<div class="win" style="height:{h}px">'
            f'<div class="content{" q" if queue else ""}">{banner}{content}</div>'
            f'{sidebar(active, playing)}{q}{toolbar(status, queue)}{player(playing)}{overlay}</div>')
    PAGES[name] = (doc(f"Discair macOS · Cupertino · {title}", body), 1280 + 48, h + 48)

def sheet_page(name, title, body, w=1280, h=900):
    PAGES[name] = (doc(f"Discair macOS · Cupertino · {title}", f'<div class="spec" style="width:{w}px;min-height:{h}px">{body}</div>'), w + 48, h + 48)

def st(kind, text, size=14):
    icon = {"ok":"checkc","wa":"warn","da":"xc","off":"minus","inf":"info"}[kind]
    return f'<span class="st {kind}">{ico(icon,size,2)}{text}</span>'

def pill(kind, text, icon=None):
    i = ico(icon,12,2.2) if icon else ""
    return f'<span class="pill {kind}">{i}{text}</span>'

def delta(up, text, good=True):
    cls = "ok" if good else "c2"
    return f'<span class="st {cls}" style="font-weight:600">{ico("arrowu" if up else "arrowd",12,2.4)}</span><span class="t-call">{text}</span>'

# ---------------------------------------------------------------- charts
def chart_line(w, h, vals, xlabels, yticks, sel=None, annot=None, prev=None, ghost=False, area=True, pad=(8, 44, 24, 8)):
    """Line chart: horizontal gridlines only, value labels on the trailing side, baseline stronger, one accent line."""
    t, r, b, l = pad
    x0, x1, y0, y1 = l, w - r, h - b, t
    lo, hi = yticks[0], yticks[-1]
    xs = scale(list(range(len(vals))), 0, len(vals) - 1, x0, x1)
    ys = scale(vals, lo, hi, y0, y1)
    o = f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
    for i, tk in enumerate(yticks):
        y = scale([tk], lo, hi, y0, y1)[0]
        col = "var(--chart-base)" if i == 0 else "var(--chart-grid)"
        o += f'<line x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}" stroke="{col}" stroke-width="1"/>'
        o += f'<text class="axn" x="{x1+8}" y="{y+4:.1f}">{tk:,}</text>'
    n = len(xlabels)
    for i, lab in enumerate(xlabels):
        x = x0 + (x1 - x0) * i / (n - 1)
        anchor = "start" if i == 0 else ("end" if i == n - 1 else "middle")
        o += f'<text class="ax" x="{x:.1f}" y="{h-6}" text-anchor="{anchor}">{lab}</text>'
    pts = list(zip(xs, ys))
    stroke = "var(--chart-3)" if ghost else "var(--chart-1)"
    if prev:
        pxs = scale(list(range(len(prev))), 0, len(prev) - 1, x0, x1); pys = scale(prev, lo, hi, y0, y1)
        o += f'<path d="{nice_path(list(zip(pxs,pys)))}" fill="none" stroke="var(--chart-2)" stroke-width="1.5" stroke-dasharray="4 4"/>'
    if area and not ghost:
        o += f'<path d="{nice_path(pts)} L{x1},{y0} L{x0},{y0} Z" fill="var(--chart-1)" opacity=".08"/>'
    o += f'<path d="{nice_path(pts)}" fill="none" stroke="{stroke}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" {"stroke-dasharray=\'2 6\'" if ghost else ""}/>'
    if annot is not None:
        i, text = annot
        o += f'<circle cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="3" fill="#fff" stroke="var(--text-2)" stroke-width="1.5"/>'
        o += f'<line x1="{xs[i]:.1f}" x2="{xs[i]:.1f}" y1="{ys[i]-6:.1f}" y2="{ys[i]-22:.1f}" stroke="var(--text-2)" stroke-width="1"/>'
        o += f'<text class="ax" x="{xs[i]:.1f}" y="{ys[i]-28:.1f}" text-anchor="middle">{text}</text>'
    if sel is not None:
        o += f'<line x1="{xs[sel]:.1f}" x2="{xs[sel]:.1f}" y1="{y1}" y2="{y0}" stroke="var(--text-2)" stroke-width="1"/>'
        o += f'<circle cx="{xs[sel]:.1f}" cy="{ys[sel]:.1f}" r="5" fill="var(--chart-1)" stroke="#fff" stroke-width="2"/>'
    if not ghost and sel is None:
        o += f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="4" fill="var(--chart-1)" stroke="#fff" stroke-width="2"/>'
    return o + "</svg>", (xs, ys)

def chart_cols(w, h, vals, labels, hi_idx=None, yticks=None, marks=None, ghost=False, pad=(8, 44, 24, 8), barw=.62, valuelabels=False):
    """Columns from a zero baseline. One accent column, the rest neutral."""
    t, r, b, l = pad
    x0, x1, y0, y1 = l, w - r, h - b, t
    top = (yticks or [0, max(vals)])[-1]
    n = len(vals); step = (x1 - x0) / n; bw = step * barw
    o = f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
    for i, tk in enumerate(yticks or []):
        y = y0 - (y0 - y1) * tk / top
        col = "var(--chart-base)" if i == 0 else "var(--chart-grid)"
        o += f'<line x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}" stroke="{col}"/>'
        o += f'<text class="axn" x="{x1+8}" y="{y+4:.1f}">{tk:,}</text>'
    if not yticks:
        o += f'<line x1="{x0}" x2="{x1}" y1="{y0}" y2="{y0}" stroke="var(--chart-base)"/>'
    for i, v in enumerate(vals):
        x = x0 + step * i + (step - bw) / 2
        bh = (y0 - y1) * v / top
        fill = "var(--chart-ghost)" if ghost else ("var(--chart-1)" if i == hi_idx else "var(--chart-3)")
        o += f'<path d="M{x:.1f},{y0} v{-max(bh-3,0):.1f} q0,-3 3,-3 h{bw-6:.1f} q3,0 3,3 v{max(bh-3,0):.1f} z" fill="{fill}"/>'
        if marks:
            my = y0 - (y0 - y1) * marks[i] / top
            o += f'<line x1="{x-3:.1f}" x2="{x+bw+3:.1f}" y1="{my:.1f}" y2="{my:.1f}" stroke="var(--text)" stroke-width="2"/>'
        if valuelabels and not ghost:
            o += f'<text class="{"axb" if i == hi_idx else "axn"}" x="{x+bw/2:.1f}" y="{y0-bh-6:.1f}" text-anchor="middle">{v:,}</text>'
        o += f'<text class="ax" x="{x+bw/2:.1f}" y="{h-6}" text-anchor="middle">{labels[i]}</text>'
    return o + "</svg>"

def chart_pairs(w, rows, hi=None, rowh=32, labelw=48, valw=84):
    """Sorted or ordered horizontal bars, two per row: context (neutral) over highlighted (accent). Values right-aligned."""
    h = rowh * len(rows)
    bw = w - labelw - valw
    top = max(max(a, b) for _, a, b in rows)
    o = f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
    for i, (lab, own, play) in enumerate(rows):
        y = i * rowh
        sel = lab == hi
        o += f'<text class="{"axb" if sel else "ax"}" x="0" y="{y+19}">{lab}</text>'
        o += f'<rect x="{labelw}" y="{y+8}" width="{bw*own/top:.1f}" height="6" rx="3" fill="var(--chart-3)"/>'
        o += f'<rect x="{labelw}" y="{y+17}" width="{bw*play/top:.1f}" height="6" rx="3" fill="var(--chart-1)" opacity="{1 if (hi is None or sel) else .45}"/>'
        o += f'<text class="axn" x="{w}" y="{y+14}" text-anchor="end">{own}%</text>'
        o += f'<text class="{"axb" if sel else "axn"}" x="{w}" y="{y+26}" text-anchor="end" {"" if sel else ""}>{play}%</text>'
    return o + "</svg>"

def chart_dumbbell(w, rows, top=20, rowh=40, labelw=96):
    """Before and after on one track: hollow neutral dot (all time) to filled accent dot (recent), with the direction arrow."""
    h = rowh * len(rows) + 20
    x0, x1 = labelw, w - 96
    o = f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
    for tk in range(0, top + 1, 5):
        x = x0 + (x1 - x0) * tk / top
        o += f'<line x1="{x:.1f}" x2="{x:.1f}" y1="0" y2="{h-20}" stroke="var(--chart-grid)"/>'
        o += f'<text class="axn" x="{x:.1f}" y="{h-4}" text-anchor="middle">{tk}%</text>'
    for i, (lab, a, b) in enumerate(rows):
        y = i * rowh + rowh / 2
        xa, xb = x0 + (x1 - x0) * a / top, x0 + (x1 - x0) * b / top
        up = b > a
        o += f'<text class="axb" x="0" y="{y+4}" style="font-size:13px">{lab}</text>'
        o += f'<line x1="{xa:.1f}" x2="{xb:.1f}" y1="{y}" y2="{y}" stroke="{"var(--chart-1)" if up else "var(--chart-2)"}" stroke-width="3" stroke-linecap="round"/>'
        o += f'<circle cx="{xa:.1f}" cy="{y}" r="5" fill="#F5F5F7" stroke="var(--chart-2)" stroke-width="2"/>'
        o += f'<circle cx="{xb:.1f}" cy="{y}" r="6" fill="{"var(--chart-1)" if up else "var(--text)"}"/>'
        arrow = "▲" if up else "▼"
        o += f'<text class="axb" x="{w}" y="{y+4}" text-anchor="end">{a}% → {b}%  {arrow}</text>'
    return o + "</svg>"

def chart_heat(weeks, seed=7, cell=12, gap=4, levels=("#ECECF0", "#F6C5D0", "#EE8FA5", "#E2537A", "#D61F4A")):
    import random
    rnd = random.Random(seed)
    w = weeks * (cell + gap) + 28; h = 7 * (cell + gap) + 20
    o = f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
    for d, lab in ((0, "Mon"), (2, "Wed"), (4, "Fri"), (6, "Sun")):
        o += f'<text class="ax" x="0" y="{d*(cell+gap)+10}">{lab}</text>'
    for wk in range(weeks):
        for d in range(7):
            base = 0.25 + 0.5 * (wk / weeks) + (0.25 if d >= 4 else 0)
            v = rnd.random() * base
            lv = 0 if v < .12 else 1 if v < .3 else 2 if v < .5 else 3 if v < .7 else 4
            o += f'<rect x="{28+wk*(cell+gap)}" y="{d*(cell+gap)}" width="{cell}" height="{cell}" rx="3" fill="{levels[lv]}"/>'
    months = ["Jun", "Jul", "Aug", "Sep", "Oct", "Nov"]
    for i, m in enumerate(months):
        o += f'<text class="ax" x="{28+i*(weeks/6)*(cell+gap):.0f}" y="{h-2}">{m}</text>'
    return o + "</svg>"

def stage_track(step, pct=None, failed=False, w=200):
    """Four-step acquisition tracker: Found, Downloading, Importing, In library."""
    names = ["Found", "Downloading", "Importing", "In library"]
    o = f'<div style="display:flex;gap:4px;width:{w}px">'
    for i in range(4):
        if i < step: bg = "var(--text)"
        elif i == step: bg = "var(--danger)" if failed else "var(--accent)"
        else: bg = "#DCDCE2"
        inner = ""
        if i == step and pct is not None and not failed:
            bg = "#DCDCE2"; inner = f'<i style="display:block;height:100%;width:{pct}%;background:var(--accent);border-radius:2px"></i>'
        o += f'<div style="flex:1;height:4px;border-radius:2px;background:{bg}">{inner}</div>'
    return o + "</div>"
