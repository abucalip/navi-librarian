"""Builds the Flow Home Threads and Shelf mixer spec (docs/plans/Home_threads_mixer.md).

Run from the repo root: python3 docs/design/android-art-themes/_src/build_home_threads_mixer.py
Then re-render the PNG (see the plan, section 1). The page is self-contained: shared.css, flow.css and the icon symbols are inlined."""
import math, sys, pathlib

DESIGN = pathlib.Path(__file__).resolve().parent.parent
OUT = DESIGN / "flow" / "home-threads-mixer" / "home-threads-mixer.html"
import re
shared = (DESIGN / "shared.css").read_text()
flow = (DESIGN / "flow.css").read_text()
defs = re.search(r'<svg width="0".*?</svg>', (DESIGN / "flow" / "home.html").read_text(), re.S).group(0)
# extra icons not in the Flow set
defs = defs.replace("</defs>", """<symbol id="i-person" viewBox="0 0 24 24"><circle cx="12" cy="8" r="3.500"/><path d="M5 20c.8-3.800 3.600-6 7-6s6.200 2.200 7 6"/></symbol><symbol id="i-pin" viewBox="0 0 24 24"><path d="M12 21s-6-5.600-6-11a6 6 0 0 1 12 0c0 5.400-6 11-6 11z"/><circle cx="12" cy="10" r="2.200"/></symbol><symbol id="i-tag" viewBox="0 0 24 24"><path d="M4 12V5a1 1 0 0 1 1-1h7l8 8-8 8z"/><circle cx="8.500" cy="8.500" r="1.300"/></symbol><symbol id="i-cal" viewBox="0 0 24 24"><rect x="4" y="5.500" width="16" height="14.500" rx="2"/><path d="M4 10h16M8.500 3.500v4M15.500 3.500v4"/></symbol><symbol id="i-dice" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="3"/><circle cx="9" cy="9" r="1.200"/><circle cx="15" cy="15" r="1.200"/><circle cx="15" cy="9" r="1.200"/><circle cx="9" cy="15" r="1.200"/></symbol></defs>""")

def ic(name, cls=""):
    return f'<svg class="{cls}"><use href="#i-{name}"/></svg>'

DOCK = ('<div class="dock"><div class="mini"><i class="cv k5"></i><div class="sp"><h4 class="el">After the Flood</h4><p class="mut sm">Talk Talk</p></div>'
        + ic("pause", "f") + '</div><div class="nav"><span class="on">' + ic("home") + 'Home</span><span>' + ic("disc") + 'Discover</span><span>'
        + ic("lib") + 'Library</span><span>' + ic("search") + 'Search</span></div></div>')
STATUS = '<div class="status"><span>21:14</span><span>5G 82%</span></div>'

def phone(caption, body, extra="", dock=True):
    return (f'<figure><figcaption>{caption}</figcaption><div class="phone fl">'
            f'<div class="scr">{STATUS}{body}</div>{extra}{DOCK if dock else ""}</div></figure>')

def head(title, link=None, eyebrow=None):
    eb = f'<span class="eb" style="display:block;margin-bottom:2px">{eyebrow}</span>' if eyebrow else ""
    return f'<div class="h"><div>{eb}<h3>{title}</h3></div>' + (f'<a>{link}</a>' if link else "") + '</div>'

ARTISTS_TAIL = ('<div class="hs" style="height:62px;align-items:flex-end;margin-top:-4px"><div class="pc" style="height:62px"><i class="ar a1" style="margin-top:-138px"></i><b>Alice Coltrane</b></div>'
                '<div class="pc" style="height:62px"><i class="ar a2" style="margin-top:-138px"></i><b>The Blue Nile</b></div><div class="pc" style="height:62px"><i class="ar a4" style="margin-top:-138px"></i><b>Slowdive</b></div></div>')

# ---------------------------------------------------------------- A · Threads
def constellation(selected=1, centre="k5", orbit=("k2", "k8", "k3", "k10", "k12", "k7"),
                  labels=("Producer", "4AD", "Wessex", "Bass", "Island", "Engineer"), kinds=("p", "l", "s", "p", "l", "p"), show=None):
    cx, cy, rx, ry, R = 180, 146, 134, 112, 58
    svg, covers, pills = [], [], []
    for i, a in enumerate((-150, -90, -30, 30, 90, 150)):
        if show is not None and i not in show:
            continue
        t = math.radians(a)
        x, y = cx + rx * math.cos(t), cy + ry * math.sin(t)
        on = i == selected
        svg.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{"var(--accent)" if on else "var(--chart3)"}" stroke-width="{2.2 if on else 1.4}" {"" if kinds[i]=="p" else "stroke-dasharray=\"" + ("5 4" if kinds[i]=="l" else "1.5 4") + "\""} stroke-linecap="round"/>')
        covers.append(f'<i class="cv {orbit[i]} orb" style="left:{x-R/2:.0f}px;top:{y-R/2:.0f}px;{"box-shadow:0 0 0 3px var(--page),0 0 0 5px var(--accent),var(--e1)" if on else ""}"></i>')
        mx, my = cx + (x - cx) * .6, cy + (y - cy) * .6
        pills.append(f'<span class="lpill{" on" if on else ""}" style="left:{mx:.0f}px;top:{my:.0f}px">{labels[i]}</span>')
    return (f'<div class="const"><svg class="chart" viewBox="0 0 360 292" style="position:absolute;inset:0">{"".join(svg)}</svg>'
            + "".join(covers) + f'<i class="cv {centre} ctr-cv"></i>' + "".join(pills) + '</div>')


SHEET_A = ('<div class="scrim"></div><div class="sheet" style="gap:12px;padding-bottom:22px">'
    '<div class="row"><span class="eb sp">Why they connect</span>' + ic("close","s") + '</div>'
    '<div class="row" style="gap:0;justify-content:center"><i class="cv k5" style="width:92px;border-radius:12px;box-shadow:var(--e1)"></i>'
    '<div class="wire"><span>' + ic("person","s") + '</span></div><i class="cv k8" style="width:92px;border-radius:12px;box-shadow:var(--e1)"></i></div>'
    '<p style="font-size:15px;line-height:22px;text-align:center"><b>Tim Friese-Greene</b> produced <b>Laughing Stock</b> and <b>Spirit of Eden</b>, and played keyboards on both.</p>'
    '<div class="list card" style="margin:0;padding:0 12px"><div class="li" style="min-height:52px"><span class="ic">' + ic("person","s") + '</span><div class="sp"><h4>Also on 7 more of yours</h4><p class="mut sm">Lush, Catherine Wheel, Tight Fit…</p></div>' + ic("chev","chev") + '</div>'
    '<div class="li" style="min-height:52px"><span class="ic">' + ic("tag","s") + '</span><div class="sp"><h4>Both on Parlophone, Polydor</h4><p class="mut sm">Different labels, same circle</p></div>' + ic("chev","chev") + '</div></div>'
    '<div class="row"><span class="btn p sp">' + ic("play","s") + 'Play the thread</span><span class="btn">Centre here</span></div></div>')


# ---------------------------------------------------------------- C · Shelves
def drums(cols, sel):
    out = ['<div class="drums">']
    for name, vals in cols:
        k = sel[name]
        rows = "".join(f'<span class="d{abs(i-k)}">{v}</span>' for i, v in enumerate(vals) if abs(i - k) <= 2)
        out.append(f'<div class="drum"><span class="eb">{name}</span><div class="drum-w">{rows}</div></div>')
    out.append('</div>')
    return "".join(out)

DRUMS = [("Era", ["Any", "60s", "70s", "80s", "90s", "00s", "10s"]), ("Genre", ["Any", "Jazz", "Ambient", "Post-rock", "Dream pop", "Folk"]), ("Played", ["Any", "Never played", "Not in a year", "Rarely", "Favourites"])]

def mosaic(cs=("k12", "k3", "k7", "k10", "k1", "k6"), more="+8"):
    return ('<div class="mosaic">' + f'<i class="cv {cs[0]} big"></i>' + "".join(f'<i class="cv {c}"></i>' for c in cs[1:4])
            + f'<span class="more"><i class="cv {cs[5]}"></i><b>{more}</b></span></div>')


CSS = """

:root{--pg:#E9E7E1;--pg-text:#1B1B1F;--pg-mut:#55535C;--pg-card:#F5F3EE;--pg-line:#D6D2C8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--pg:#1A1917;--pg-text:#EDEBE6;--pg-mut:#A8A49B;--pg-card:#24221F;--pg-line:#3A3733}}
:root[data-theme="dark"]{--pg:#1A1917;--pg-text:#EDEBE6;--pg-mut:#A8A49B;--pg-card:#24221F;--pg-line:#3A3733}
body{background:var(--pg);color:var(--pg-text)}
.doc h1{font-family:Inter,system-ui,sans-serif;font-weight:800;letter-spacing:-.03em}
.doc p,figcaption{color:var(--pg-mut)}
.prop{margin:44px 0 0;padding-top:28px;border-top:1px solid var(--pg-line)}
.prop h2{font:800 30px/1.1 Inter,system-ui,sans-serif;letter-spacing:-.03em;margin:0 0 4px;display:flex;gap:14px;align-items:baseline}
.prop h2 .lt2{display:inline-grid;place-items:center;width:40px;height:40px;border-radius:12px;background:#C2410C;color:#fff;font-size:22px}
.prop .sub{font:600 16px/1.3 Inter,system-ui,sans-serif;color:var(--pg-mut);margin:0 0 12px}
.prop .what{max-width:80ch;margin:0 0 10px;font-size:15px;line-height:1.55}
.prop ul{margin:0 0 22px;padding-left:18px;max-width:80ch;font-size:14px;line-height:1.55}
.costs{border-collapse:collapse;margin:26px 0 0;font-size:13px;max-width:900px;width:100%;background:var(--pg-card);border-radius:12px;overflow:hidden}
.costs th,.costs td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--pg-line);vertical-align:top}
.costs th{font:600 11px/1 'JetBrains Mono',monospace;text-transform:uppercase;letter-spacing:.05em;color:var(--pg-mut)}
.costs code{font:12px 'JetBrains Mono',monospace}
.cost{display:inline-block;font:600 11px/16px Inter,system-ui,sans-serif;padding:2px 8px;border-radius:6px;white-space:nowrap;margin:1px 0}
.c1{background:#DCEEDF;color:#1E5A30}.c2{background:#DCE7F8;color:#1F4F9F}.c3{background:#F8E8CC;color:#7A4A00}
.legend{display:flex;gap:10px;flex-wrap:wrap;align-items:center;font-size:13px;color:var(--pg-mut);margin:0 0 6px}
.toc{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 4px}
.toc a{font:600 14px Inter,system-ui,sans-serif;color:var(--pg-text);text-decoration:none;background:var(--pg-card);padding:8px 14px;border-radius:999px}
@media (max-width:420px){body{padding:16px}.phone{transform:scale(.86);transform-origin:top left;margin-bottom:-110px;margin-right:-52px}}

/* A · constellation, bridge, fan */
.fl .const{position:relative;height:292px;margin:-6px 0 -4px}
.fl .const .orb{position:absolute;width:58px;border-radius:10px;box-shadow:var(--e1)}
.fl .const .ctr-cv{position:absolute;width:100px;left:130px;top:96px;border-radius:var(--r-cover);box-shadow:var(--e3);z-index:2}
.fl .lpill{position:absolute;transform:translate(-50%,-50%);font:600 10px/14px Inter,system-ui,sans-serif;padding:2px 7px;border-radius:999px;background:var(--surface);color:var(--muted);box-shadow:var(--e1);z-index:3;white-space:nowrap}
.fl .lpill.on{background:var(--accent);color:var(--on-accent)}
.fl .bridge{position:relative;height:150px;margin:0 0 -6px}
.fl .bridge .end{position:absolute;width:76px;border-radius:12px;box-shadow:var(--e3);z-index:2}
.fl .bridge .bead{position:absolute;width:34px;border-radius:7px;box-shadow:0 0 0 2.5px var(--page),var(--e1)}
.fl .endlab{position:absolute;bottom:2px;font:600 11px Inter,system-ui,sans-serif;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);width:90px}
.fl .fan{position:relative;height:178px;margin:-4px 0 0}
.fl .fan .cv{position:absolute;left:122px;top:14px;width:116px;border-radius:12px;transform-origin:50% 190%;box-shadow:var(--e1)}
.fl .fan .cv:nth-child(3){box-shadow:var(--e3)}
.fl .wire{width:70px;height:2px;background:var(--accent);position:relative;display:grid;place-items:center}
.fl .wire span{width:30px;height:30px;border-radius:50%;background:var(--accent);color:var(--on-accent);display:grid;place-items:center}
.fl .sheet{background:var(--surface)}

/* B · week, dial, timeline, tide */
.fl .week{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;padding-inline:12px}
.fl .wk{display:flex;flex-direction:column;align-items:center;gap:2px;padding:6px 0 8px;border-radius:14px;position:relative;min-height:104px}
.fl .wk b{font:700 17px/22px Inter,system-ui,sans-serif;letter-spacing:-.02em}
.fl .wk.on{background:var(--surface);box-shadow:var(--e1)}
.fl .wk.on b{color:var(--accent)}
.fl .wk-cv{width:40px;border-radius:7px;margin-top:6px;box-shadow:var(--e1)}
.fl .wk-dot{width:5px;height:5px;border-radius:50%;background:var(--chart3);margin-top:22px}
.fl .yrs{position:absolute;bottom:2px;font:700 10px/14px Inter,system-ui,sans-serif;background:var(--accent);color:var(--on-accent);padding:0 5px;border-radius:7px}
.fl .dial{position:relative;height:214px;margin:-6px 0 0}
.fl .dial .dcv{position:absolute;width:66px;border-radius:12px;box-shadow:var(--e1);transform-origin:50% 100%}
.fl .lg-sw{width:10px;height:10px;border-radius:3px;display:inline-block}
.fl .who-s{width:62px;display:flex;flex-direction:column;align-items:center;gap:4px;font:500 11px/14px Inter,system-ui,sans-serif;color:var(--muted)}
.fl .who-s .ar{width:52px;border-radius:50%}
.fl .who-s.on{color:var(--text);font-weight:600}
.fl .who-s.on .ar{box-shadow:0 0 0 2px var(--page),0 0 0 4px var(--accent)}
.fl .tl{position:relative;height:150px;margin:0 0 -6px}
.fl .tl-axis{position:absolute;left:12px;right:12px;top:74px;height:2px;border-radius:1px;background:var(--chart3)}
.fl .tl-cv{position:absolute;top:8px;width:54px;border-radius:8px;box-shadow:var(--e1)}
.fl .tl-gh{position:absolute;top:100px;width:42px;height:42px;border-radius:8px;background:var(--raised);display:grid;place-items:center;color:var(--accent)}
.fl .tl-tick{position:absolute;top:70px;width:2px;height:10px;border-radius:1px;background:var(--text)}
.fl .tl-yr{position:absolute;top:84px;width:28px;text-align:center;font:500 10px Inter,system-ui,sans-serif;color:var(--muted)}
.fl .tl-ev{position:absolute;top:104px;font:600 10px Inter,system-ui,sans-serif;color:var(--info);display:flex;align-items:center;gap:4px;white-space:nowrap}
.fl .tl-ev i{width:7px;height:7px;border-radius:50%;background:var(--info)}
.fl .tide{position:relative;margin:4px 16px 0;height:64px}
.fl .tide svg{position:absolute;inset:0}
.fl .tide-cv{position:absolute;width:30px;border-radius:6px;box-shadow:0 0 0 2px var(--page),var(--e1)}

/* C · mixer, atlas, gaps */
.fl .mosaic{display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:repeat(2,1fr);gap:6px;padding-inline:16px;height:166px}
.fl .mosaic .cv,.fl .mosaic .sk{width:100%;height:100%;border-radius:10px;box-shadow:var(--e1)}
.fl .mosaic .big{grid-column:1/3;grid-row:1/3;border-radius:var(--r-cover);box-shadow:var(--e3)}
.fl .mosaic .more{position:relative;display:block}
.fl .mosaic .more b{position:absolute;inset:0;display:grid;place-items:center;color:#fff;font:700 18px Inter,system-ui,sans-serif;background:rgba(21,19,15,.55);border-radius:10px}
.fl .mosaic.empty .big{box-shadow:none}.fl .mosaic.empty .sk{box-shadow:none}
.fl .drums{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding-inline:16px}
.fl .drum{display:flex;flex-direction:column;align-items:center;gap:4px}
.fl .drum-w{width:100%;background:var(--surface);border-radius:16px;box-shadow:var(--e1);display:flex;flex-direction:column;align-items:center;padding:6px 4px;position:relative;overflow:hidden}
.fl .drum-w span{height:26px;display:grid;place-items:center;white-space:nowrap;font-weight:500}
.fl .drum-w .d0{font:700 15px Inter,system-ui,sans-serif;color:var(--text);background:var(--raised);border-radius:10px;width:100%;height:32px}
.fl .drum-w .d1{font-size:13px;color:var(--muted);transform:scaleY(.86)}
.fl .drum-w .d2{font-size:12px;color:var(--muted);opacity:.45;transform:scaleY(.7)}
.fl .atlas{position:relative;height:236px;margin:0 16px;border-radius:var(--r-card);background:var(--surface);box-shadow:var(--e1);overflow:hidden}
.fl .land{position:absolute;background:radial-gradient(circle,var(--chart3) 1.1px,#0000 1.4px) 0 0/6px 6px}
.fl .pin{position:absolute;width:22px;height:22px;border-radius:50%;background:var(--text);color:var(--page);font:700 10px/22px Inter,system-ui,sans-serif;text-align:center;box-shadow:0 0 0 2px var(--surface)}
.fl .pin.on{background:var(--accent);color:var(--on-accent);width:24px;height:24px;line-height:24px}
.fl .pinstack{position:absolute;width:72px;height:80px}
.fl .pinstack .cv{position:absolute;width:58px;border-radius:8px;box-shadow:var(--e1)}
.fl .pinstack .cv:nth-child(1){left:0;top:10px;transform:rotate(-8deg)}
.fl .pinstack .cv:nth-child(2){left:14px;top:0;z-index:2;box-shadow:var(--e3)}
.fl .pinstack .cv:nth-child(3){left:26px;top:12px;transform:rotate(8deg)}
.fl .gaps{display:grid;grid-template-columns:repeat(6,1fr);gap:6px;padding-inline:16px}
.fl .gaps div{display:flex;flex-direction:column;align-items:center;gap:4px;font:500 11px Inter,system-ui,sans-serif;color:var(--muted)}
.fl .gaps .cv{width:100%;border-radius:8px;box-shadow:var(--e1)}
.fl .gaps .gh{width:100%;aspect-ratio:1;border-radius:8px;background:var(--raised);display:grid;place-items:center;color:var(--accent)}
.fl .gaps .acc{color:var(--accent);font-weight:600}
"""


# ---------------------------------------------------------------- frames
def row_sel(title, sub, extra=""):
    return (f'<div class="pad row" style="margin-top:-2px"><div class="sp"><h4 class="el">{title}</h4><p class="mut sm el">{sub}</p></div>{extra}'
            '<span class="btn sm p">' + ic("play", "s") + 'Play</span></div>')

def tabs(items, on=0, style="margin-top:-4px"):
    return f'<div class="tabs" style="{style}">' + "".join(f'<span class="{"on" if i == on else ""}">{t}</span>' for i, t in enumerate(items)) + '</div>'

T1 = phone("T1 · Home after Artists: Threads around the album played most recently. All selected; the line to Spirit of Eden is selected",
    ARTISTS_TAIL + head("Threads", "Change", "Around Laughing Stock")
    + constellation()
    + tabs(("All", "People", "Labels", "Places"))
    + row_sel("Spirit of Eden · Talk Talk", "Same producer: Tim Friese-Greene", '<span class="btn sm t">Centre</span>'))

T2 = phone("T2 · Labels selected: only label links, up to six; empty slots are not drawn",
    ARTISTS_TAIL + head("Threads", "Change", "Around Laughing Stock")
    + constellation(selected=0, orbit=("k9", "k8", "k3", "k10", "k12", "k7"), labels=("Polydor", "4AD", "Parlophone", "", "", ""),
                    kinds=("l", "l", "l", "l", "l", "l"), show={0, 1, 2})
    + tabs(("All", "People", "Labels", "Places"), on=2)
    + row_sel("Hex · Bark Psychosis", "Same label: Polydor, 1994", '<span class="btn sm t">Centre</span>'))

T3 = phone("T3 · Tap a line or a label pill: Why they connect (server sentences, the two covers, more of yours)",
    ARTISTS_TAIL + head("Threads", "Change", "Around Laughing Stock") + constellation(), extra=SHEET_A, dock=False)

PICK = ('<div class="scrim"></div><div class="sheet" style="gap:12px;padding-bottom:22px">'
    '<div class="row"><h3 class="sp">Start from</h3>' + ic("close", "s") + '</div>'
    + tabs(("Played lately", "Most played"), style="margin:0") +
    '<div class="pickgrid">' + "".join(f'<i class="cv {c}{" on" if i == 0 else ""}"></i>' for i, c in enumerate(("k5", "k1", "k10", "k3", "k9", "k7", "k12", "k6"))) + '</div>'
    '<p class="mut sm">Threads start from an album you own. Pick one; it is remembered until you change it.</p></div>')

T4 = phone("T4 · Change: pick the centre from Played lately or Most played", ARTISTS_TAIL + head("Threads", "Change", "Around Laughing Stock") + constellation(), extra=PICK, dock=False)

T5 = phone("T5 · Loading (grey orbit slots, centre already drawn) and Nothing in the store yet",
    head("Threads", "Change", "Around Laughing Stock")
    + '<div class="const">' + "".join(f'<i class="sk orb" style="left:{180+134*math.cos(math.radians(a))-29:.0f}px;top:{146+112*math.sin(math.radians(a))-29:.0f}px;width:58px;height:58px;border-radius:10px"></i>' for a in (-150, -90, -30, 30, 90, 150))
    + '<i class="cv k5 ctr-cv"></i></div>'
    + '<div class="pad col" style="gap:10px;margin-top:-6px"><h4>No links for Laughing Stock yet</h4><p class="mut sm">The store has no credits, label or studio for this album. Ask it to read them, or start from another album.</p>'
    '<div class="row"><span class="btn sm p">' + ic("server", "s") + 'Update the store</span><span class="btn sm">Change</span></div></div>')

M1 = phone("M1 · Home after Threads: the Shelf mixer. Three wheels, a mosaic of the albums they match, Play and Save",
    head("Shelf mixer", "Saved", "Pull from your own shelves")
    + mosaic()
    + '<div class="pad row" style="margin-top:-4px"><div class="sp"><h4>14 albums · 9 h 40 min</h4><p class="mut sm">90s post-rock you have not played in a year</p></div><span class="ib dice">' + ic("dice") + '</span></div>'
    + drums(DRUMS, {"Era": 4, "Genre": 3, "Played": 2})
    + '<div class="pad row"><span class="btn p sp">' + ic("play", "s") + 'Play</span><span class="btn">' + ic("plus", "s") + 'Save</span></div>')

def mini_stack(cs):
    return '<span class="mstack">' + "".join(f'<i class="cv {c}"></i>' for c in cs) + '</span>'

SAVED = ('<div class="scrim"></div><div class="sheet" style="gap:12px;padding-bottom:22px;background:var(--rail)">'
    '<div class="row"><h3 class="sp">Saved mixes</h3>' + ic("close", "s") + '</div>'
    '<div class="list card" style="margin:0;padding:0 12px">'
    + "".join(f'<div class="li">{mini_stack(cs)}<div class="sp"><h4 class="el">{t}</h4><p class="mut sm el">{d}</p></div><span class="btn sm sq">{ic("play","s")}</span></div>'
              for cs, t, d in ((("k12", "k3", "k7"), "90s post-rock, not in a year", "14 albums · saved 12 Nov"),
                               (("k8", "k1", "k9"), "80s, never played", "6 albums · saved 2 Nov"),
                               (("k4", "k6", "k10"), "Dream pop favourites", "21 albums · saved 28 Oct")))
    + '</div><p class="mut sm">Saved mixes are smart playlists on the server, so they also appear on the Mac. Long-press to rename or delete.</p></div>')

M2 = phone("M2 · Saved: the sheet of saved mixes (stored smart playlists); tap Play or the row to load its wheels",
    head("Shelf mixer", "Saved", "Pull from your own shelves") + mosaic() + drums(DRUMS, {"Era": 4, "Genre": 3, "Played": 2}), extra=SAVED, dock=False)

M3 = phone("M3 · Nothing matches: the mosaic stays empty and the server says which wheel to loosen",
    head("Shelf mixer", "Saved", "Pull from your own shelves")
    + '<div class="mosaic empty"><i class="sk big"></i><i class="sk"></i><i class="sk"></i><i class="sk"></i><span class="more"><i class="sk"></i></span></div>'
    + '<div class="pad col" style="gap:8px;margin-top:-4px"><h4>Nothing on your shelves matches</h4><div class="row" style="gap:8px;flex-wrap:wrap">'
    '<span class="chip">Era: Any · 6 albums</span><span class="chip">Played: Any · 3 albums</span></div></div>'
    + drums(DRUMS, {"Era": 1, "Genre": 4, "Played": 1})
    + '<div class="pad row"><span class="btn p sp" style="opacity:.4">' + ic("play", "s") + 'Play</span><span class="btn" style="opacity:.4">' + ic("plus", "s") + 'Save</span></div>')

# ---------------------------------------------------------------- components board
SW = [("--page", "rail", "#FBFAF7", "Page behind both sections"), ("--surface", "surface", "#FFFFFF", "Wheel well, label pill, sheet"),
      ("--raised", "raised", "#EFECE5", "Selected wheel row, chips, skeletons"), ("--chart3", "chart3", "#D9D4C8", "Thread lines (not selected)"),
      ("--text", "text", "#15130F", "Titles, selected wheel value"), ("--muted", "textMuted", "#645F55", "Eyebrows, wheel neighbours, pills"),
      ("--accent", "accent", "#C2410C", "Selected line, ring, pill; Play"), ("--on-accent", "onAccent", "#FFFFFF", "Text on accent")]

def board():
    sw = "".join(f'<div class="swr"><i style="background:var({v})"></i><div><b>{role}</b> <code>{hexv}</code><br><span>{use}</span></div></div>' for v, role, hexv, use in SW)
    lines = ("".join(f'<div class="lnr"><svg viewBox="0 0 120 10"><line x1="4" y1="5" x2="116" y2="5" stroke="{c}" stroke-width="{w}" stroke-linecap="round" {d}/></svg><span>{t}</span></div>'
             for c, w, d, t in (("var(--chart3)", 1.4, "", "People (crew, guests): solid 1.4 dp"),
                                ("var(--chart3)", 1.4, 'stroke-dasharray="5 4"', "Labels: dash 5 dp, gap 4 dp"),
                                ("var(--chart3)", 1.4, 'stroke-dasharray="1.5 4"', "Places (studio): dot 1.5 dp, gap 4 dp"),
                                ("var(--accent)", 2.2, "", "Selected link (any kind keeps its dash): 2.2 dp, accent"))))
    icons = "".join(f'<div class="icr"><span>{ic(n)}</span><b>{label}</b><em>{state}</em></div>' for n, label, state in (
        ("person", "Person", "new"), ("tag", "Label", "new"), ("dice", "Dice", "new"), ("pin", "Place", "ArtIcons.Place"),
        ("play", "Play", "ArtIcons.Play"), ("plus", "Plus", "ArtIcons.Plus"), ("close", "Close", "ArtIcons.Close"),
        ("chev", "Chevron", "ArtIcons.Chevron"), ("server", "Server", "ArtIcons.Server"), ("path", "Paths", "ArtIcons.Paths")))
    geo = (constellation(selected=1)
           .replace('<div class="const">', '<div class="const geo">'))
    return ('<figure class="wide"><figcaption>K · Components and tokens (warm white values; every role comes from the active Flow palette)</figcaption><div class="board fl">'
        '<div class="bcol"><h5>Colour roles</h5>' + sw + '<h5>Thread lines</h5>' + lines
        + '<h5>Label pill</h5><div class="row" style="gap:12px;position:relative;height:30px"><span class="lpill" style="position:static;transform:none">Producer</span><span class="lpill on" style="position:static;transform:none">4AD</span><span class="sm mut">Inter 600 10/14 sp, padding 2×7 dp, depth 1</span></div>'
        + '<h5>Icons (24 dp grid, 1.8 stroke)</h5><div class="icg">' + icons + '</div></div>'
        '<div class="bcol"><h5>Threads geometry (360 × 292 dp box)</h5><div class="geowrap">' + geo
        + '<span class="dim" style="left:130px;top:150px">centre 100 dp, r14, depth 3</span><span class="dim" style="left:250px;top:8px">orbit 58 dp, r10, depth 1</span>'
        '<span class="dim" style="left:6px;top:270px">ellipse rx 134 · ry 112 · angles −150 −90 −30 30 90 150°</span></div>'
        '<h5>Wheel (one column)</h5><div style="width:130px">'
        + drums([("Era", ["70s", "80s", "90s", "00s", "10s"])], {"Era": 2}).replace('<div class="drums">', '<div class="drums" style="padding:0;grid-template-columns:1fr">') + '</div>'
        '<p class="sm mut" style="margin:0">Selected row 32 dp, Inter 700 15 sp, text on raised, r10. Neighbours ±1: 13 sp textMuted, scaled 0.86 high; ±2: 12 sp, 45% alpha, scaled 0.7 high. Well: surface, r16, depth 1. Eyebrow above: 12 sp caps.</p></div>'
        '<h5>Mosaic</h5><div style="width:328px">' + mosaic().replace('padding-inline:16px', '') + '</div>'
        '<p class="sm mut" style="margin:0">4 × 2 grid, gap 6 dp, height 166 dp. Big cover spans 2 × 2 (r14, depth 3); three covers r10 depth 1; the last cell shows the next cover under ink 55% and “+n”.</p>'
        '</div></div></figure>')

BOARD = board()

EXTRA_CSS = """
.fl .pickgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.fl .pickgrid .cv{width:100%;border-radius:10px;box-shadow:var(--e1)}
.fl .pickgrid .cv.on{box-shadow:0 0 0 3px var(--surface),0 0 0 5px var(--accent)}
.fl .mstack{position:relative;width:52px;height:44px;flex:none}
.fl .mstack .cv{position:absolute;width:36px;border-radius:6px;box-shadow:var(--e1)}
.fl .mstack .cv:nth-child(1){left:0;top:6px}.fl .mstack .cv:nth-child(2){left:8px;top:3px}.fl .mstack .cv:nth-child(3){left:16px;top:0;box-shadow:var(--e3)}
.fl .ib.dice{width:44px;height:44px;border-radius:50%;background:var(--raised);color:var(--text)}
figure.wide{flex-basis:100%}
.board{background:var(--page);color:var(--text);border-radius:24px;padding:24px;display:grid;grid-template-columns:minmax(0,420px) minmax(0,380px);gap:32px;max-width:900px;font-family:Inter,system-ui,sans-serif;font-size:13px;line-height:18px}
.board h5{font:600 12px/16px Inter,system-ui,sans-serif;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);margin:18px 0 8px}
.board h5:first-child{margin-top:0}
.board .bcol{display:flex;flex-direction:column;gap:6px;min-width:0}
.board .swr{display:flex;gap:10px;align-items:center}
.board .swr i{width:34px;height:34px;border-radius:10px;flex:none;box-shadow:inset 0 0 0 .5px rgba(0,0,0,.15)}
.board .swr span,.board .lnr span{color:var(--muted)}
.board code{font:12px 'JetBrains Mono',monospace}
.board .lnr{display:flex;gap:10px;align-items:center}
.board .lnr svg{width:120px;height:10px;flex:none}
.board .icg{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}
.board .icr{display:flex;flex-direction:column;align-items:center;gap:2px;font-size:11px}
.board .icr span{width:40px;height:40px;border-radius:10px;background:var(--surface);display:grid;place-items:center;box-shadow:var(--e1)}
.board .icr svg{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.board .icr em{font-style:normal;color:var(--muted);font-size:10px}
.board .geowrap{position:relative;width:360px;max-width:100%;background:repeating-linear-gradient(0deg,#0000 0 19px,var(--chart-grid) 19px 20px),repeating-linear-gradient(90deg,#0000 0 19px,var(--chart-grid) 19px 20px);border-radius:12px}
.board .geo{margin:0}
.board .dim{position:absolute;font:600 10px/14px 'JetBrains Mono',monospace;background:var(--text);color:var(--page);padding:1px 6px;border-radius:4px;z-index:4;white-space:nowrap}
.board .drum{width:120px}
@media (max-width:820px){.board{grid-template-columns:1fr}}
"""

parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Flow Home Threads Mixer</title>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap">'
         f'<style>{shared}\n{flow}\n{CSS}\n{EXTRA_CSS}</style></head><body>{defs}'
         '<div class="doc"><h1>Flow · Home: Threads and Shelf mixer</h1>'
         '<p>The spec for docs/plans/Home_threads_mixer.md. Android, Flow warm white, 360 × 780 dp, 1 px = 1 dp. Covers are drawn stand-ins. Both sections sit on Home after Artists and the Insight card, before Genres: Threads first, then the Shelf mixer. Frames T are Threads, M the Shelf mixer, K the components board. The mockups are the spec; where the plan and a frame disagree, ask the owner.</p></div>'
         '<section class="prop" style="margin-top:8px;border:0;padding-top:0"><h2><span class="lt2">T</span>Threads</h2><div class="frames">' + T1 + T2 + T3 + T4 + T5 + '</div></section>'
         '<section class="prop"><h2><span class="lt2">M</span>Shelf mixer</h2><div class="frames">' + M1 + M2 + M3 + '</div></section>'
         '<section class="prop"><h2><span class="lt2">K</span>Components</h2><div class="frames">' + BOARD + '</div></section>'
         '</body></html>']
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("".join(parts))
print("wrote", OUT, OUT.stat().st_size)
