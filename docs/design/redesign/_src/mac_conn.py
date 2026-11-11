from mac_shell import *
from mac_home import header
import math

CW, CH = 664, 560
CX, CY = 332, 276

def pos(angle, r):
    a = math.radians(angle)
    return CX + r * math.cos(a), CY - r * math.sin(a)

# (id, kind, label, owned, angle, ring, credit, via, coverkey)
NODES = [
 ("tfg", "person", "Tim Friese-Greene", False, 105, 1, True, "c", None),
 ("pb", "person", "Phill Brown", False, 132, 1, True, "c", None),
 ("lh", "person", "Lee Harris", True, 159, 1, True, "c", None),
 ("pw", "person", "Paul Webb", True, 186, 1, True, "c", None),
 ("dt", "person", "Danny Thompson", True, 213, 1, True, "c", None),
 ("mf", "person", "Mark Feltham", False, 240, 1, True, "c", None),
 ("eden", "album", "Spirit of Eden", True, 296, 1, True, "c", "eden"),
 ("laugh", "album", "Laughing Stock", True, 326, 1, True, "c", "laughing"),
 ("colour", "album", "The Colour of Spring", True, 356, 1, True, "c", "colour"),
 ("solo", "album", "Mark Hollis", True, 26, 1, True, "c", "hollis"),
 ("anja", "album", "Smiling & Waving", False, 56, 1, False, "c", "deer"),
 ("wessex", "place", "Wessex Studios", False, 268, 1, True, "c", None),
 ("verve", "label", "Verve", False, 80, 1, True, "c", None),
 ("orang", "album", "Herd of Instinct", False, 153, 2, True, "lh", "orang"),
 ("rustin", "album", "Out of Season", True, 183, 2, True, "pw", "rustin"),
 ("pent", "person", "Pentangle", False, 214, 2, False, "dt", None),
]
KIND_ICON = {"place": "pin", "label": "tag", "work": "note", "event": "calendar"}

def face(kind, label, owned, size, cover_key=None, centre=False, sel=False):
    grey = "" if owned else "filter:grayscale(1);"
    border = f"box-shadow:inset 0 0 0 2px {'#1D1D1F' if owned else 'transparent'};" + ("" if owned else "outline:2px dashed #636368;outline-offset:-2px;")
    if kind == "person":
        inner = f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:{avatar_bg(label)};{grey}{border}"></div>'
    elif kind == "album":
        r = round(size * .16)
        inner = f'<div style="width:{size}px;height:{size}px;border-radius:{r}px;background:{cover_bg(cover_key)};{grey}{border}"></div>'
    else:
        inner = (f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;color:var(--text-2);{border}">'
                 f'{ico(KIND_ICON[kind], round(size*.44))}</div>')
    ring = f'<div style="position:absolute;inset:-6px;border-radius:{"50%" if kind != "album" else "14px"};box-shadow:0 0 0 3px var(--accent)"></div>' if sel else ""
    return f'<div style="position:relative;width:{size}px;height:{size}px">{inner}{ring}</div>'

def graph(selected="tfg", nodes=NODES, centre=("Mark Hollis", "person")):
    P = {"c": (CX, CY)}
    for n in nodes:
        P[n[0]] = pos(n[4], 188 if n[5] == 1 else 292)
    svg = f'<svg width="{CW}" height="{CH}" style="position:absolute;left:0;top:0">'
    for r in (188, 292):
        svg += f'<circle cx="{CX}" cy="{CY}" r="{r}" fill="none" stroke="var(--sep)" stroke-width="1" stroke-dasharray="{"0" if r == 188 else "2 6"}"/>'
    for n in nodes:
        (x1, y1), (x2, y2) = P[n[7]], P[n[0]]
        sel = n[0] == selected
        svg += (f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{"var(--accent)" if sel else "#AEAEB2"}" stroke-width="{2.5 if sel else 1.5}" '
                f'stroke-dasharray="{"0" if n[6] else "4 4"}"/>')
    svg += "</svg>"
    h = svg
    for n in nodes:
        x, y = P[n[0]]
        size = 48 if n[5] == 1 else 32
        lab = f'<div class="t-cap" style="font-weight:600;width:96px;text-align:center;margin-top:4px;line-height:14px;background:rgba(255,255,255,.88);border-radius:4px;{"color:var(--accent-strong)" if n[0] == selected else ""}">{n[2]}</div>'
        h += (f'<div style="position:absolute;left:{x-48:.0f}px;top:{y-size/2:.0f}px;width:96px;display:flex;flex-direction:column;align-items:center">'
              f'{face(n[1], n[2], n[3], size, n[8], sel=n[0] == selected)}{lab}</div>')
    h += (f'<div style="position:absolute;left:{CX-48}px;top:{CY-36}px;width:96px;display:flex;flex-direction:column;align-items:center">'
          f'{face(centre[1], centre[0], True, 72)}<div class="t-head" style="margin-top:4px;text-align:center;background:#fff;border-radius:8px;padding:0 4px">{centre[0]}</div></div>')
    for text, ang, r in (("People", 172, 118), ("Albums", 10, 118), ("Place", 268, 252), ("Label", 80, 244)):
        x, y = pos(ang, r)
        h += f'<div class="t-eye" style="position:absolute;left:{x-30:.0f}px;top:{y-8:.0f}px;width:60px;text-align:center;color:var(--text-3)">{text}</div>'
    return f'<div style="position:relative;width:{CW}px;height:{CH}px">{h}</div>'

KEY = (f'<div class="row g16 center t-cap c2"><span class="row g4 center"><svg width="14" height="14"><circle cx="7" cy="7" r="5" fill="#C9B79C" stroke="#1D1D1F" stroke-width="2"/></svg>In your library</span>'
       f'<span class="row g4 center"><svg width="14" height="14"><circle cx="7" cy="7" r="5" fill="#D1D1D6" stroke="#636368" stroke-width="2" stroke-dasharray="3 2"/></svg>Not in your library</span>'
       f'<span class="row g4 center"><svg width="20" height="6"><line x1="0" x2="20" y1="3" y2="3" stroke="#8E8E93" stroke-width="1.5"/></svg>Stated credit</span>'
       f'<span class="row g4 center"><svg width="20" height="6"><line x1="0" x2="20" y1="3" y2="3" stroke="#8E8E93" stroke-width="1.5" stroke-dasharray="4 4"/></svg>Link, not a credit</span></div>')

def controls(name="Mark Hollis", view="Graph", depth=2, credits=False, back=True, focus=False):
    field = (f'<div class="field"><label>Start from</label><div class="inp{" focus" if focus else ""}" style="width:240px;height:32px;gap:8px">'
             + (f'<div style="width:20px;height:20px;border-radius:50%;background:{avatar_bg(name)}"></div><span class="f1">{name}</span>' if name else f'<span class="c3 f1">{ico("search",14)}&nbsp; Artist name</span>')
             + f'<span class="c2">{ico("chevd",12,2.2)}</span></div></div>')
    seg = lambda items, on: '<div class="seg" style="padding:2px">' + "".join(f'<span class="{"on" if i == on else ""}" style="height:28px">{i}</span>' for i in items) + '</div>'
    dep = f'<div class="field"><label>Reach</label>{seg(["1 step", "2 steps", "3 steps"], f"{depth} step" + ("s" if depth > 1 else ""))}</div>'
    cred = f'<div class="field"><label>Credits only</label><div class="row center" style="height:32px"><div class="sw{" on" if credits else ""}"></div></div></div>'
    vw = f'<div class="field"><label>View</label>{seg(["Graph", "List"], view)}</div>'
    bk = f'<div class="field"><label>&nbsp;</label><span class="btn" style="padding:0 8px">{ico("chevl",14,2.2)}Talk Talk</span></div>' if back else ""
    return f'<div class="row g16 end" style="margin-bottom:16px">{bk}{field}{dep}{cred}<div style="flex:1"></div>{vw}</div>'

def ev(rel, on, src="MusicBrainz", credit=True, quality="exact match"):
    return (f'<div style="background:#fff;border-radius:8px;padding:8px"><div class="row between center"><span class="t-head">{rel}</span>{pill("ok" if credit else "", "Credit" if credit else "Link", "check" if credit else None)}</div>'
            f'<div class="t-call">{on}</div><div class="t-cap c2 mt4">Source: {src} · {quality}</div></div>')

def inspector_sel():
    return (f'<div class="panel" style="width:300px;display:flex;flex-direction:column;gap:16px">'
            f'<div class="row g16 center"><div style="width:56px;height:56px;border-radius:50%;background:{avatar_bg("Tim Friese-Greene")};filter:grayscale(1);outline:2px dashed #636368;outline-offset:-2px"></div>'
            f'<div><div class="t-title3">Tim Friese-Greene</div><div class="t-call c2">Person · 1 step from Mark Hollis</div></div></div>'
            f'<div class="row g8"><span class="btn pri">Re-centre here</span><span class="btn dis">Open artist</span></div>'
            f'<div class="t-cap c2" style="margin-top:-8px">No albums under this name in your library, so there is no artist page to open.</div>'
            f'<div><div class="t-eye" style="margin-bottom:8px">How they connect · 3</div><div class="col g8">'
            + ev("Producer", "Spirit of Eden · Talk Talk · 1988") + ev("Producer", "Laughing Stock · Talk Talk · 1991") + ev("Co-writer", "After the Flood · and 11 more works")
            + f'</div></div><div><div class="t-eye" style="margin-bottom:8px">Also on, in your library</div><div class="row g8">{cover("eden",48,8,"flat")}{cover("laughing",48,8,"flat")}{cover("colour",48,8,"flat")}</div></div></div>')

def inspector_idle(name="Mark Hollis"):
    return (f'<div class="panel" style="width:300px;display:flex;flex-direction:column;gap:16px"><div><div class="t-title3">{name}</div>'
            f'<div class="t-call c2">16 connections within 2 steps · 9 in your library</div></div>'
            f'<div class="t-body c2">Choose a person, album, place or label to see how it connects and where each link comes from.</div>'
            f'<div><div class="t-eye" style="margin-bottom:8px">Kinds</div><div class="col g4 t-call">'
            f'<div class="row between"><span>People</span><span class="num">7</span></div><div class="row between"><span>Albums</span><span class="num">7</span></div>'
            f'<div class="row between"><span>Places</span><span class="num">1</span></div><div class="row between"><span>Labels</span><span class="num">1</span></div></div></div>'
            f'<div class="t-cap c2">MusicBrainz data: loaded on the server.</div></div>')

foot = (f'<div class="row between center mt8" style="white-space:nowrap">{KEY.replace("g16","g8")}</div><div class="row g8 center mt8" style="justify-content:flex-end"><span class="t-cap c2">16 of 43 connections</span><span class="btn sm">Load more</span></div>')

sub = "Who played, produced and recorded with whom, from stated MusicBrainz credits."
# graph, node selected
body = header("Connections", sub) + controls() + f'<div class="row g16"><div class="f1"><div style="margin:-8px 0 0 -4px">{graph()}</div>{foot}</div>{inspector_sel()}</div>'
window("connections--graph-selected", "Connections, graph, a node selected", "connections", body, h=960, playing=False)
# graph idle
body = header("Connections", sub) + controls() + f'<div class="row g16"><div class="f1"><div style="margin:-8px 0 0 -4px">{graph(selected=None)}</div>{foot}</div>{inspector_idle()}</div>'
window("connections--graph", "Connections, graph, nothing selected", "connections", body, h=960, playing=False)

# list view
def lrow(kind, name, conn, owned, steps, sel=False, key=None):
    lead = cover(key, 32, 6, "flat") if key else (f'<div style="width:32px;height:32px;border-radius:50%;background:{avatar_bg(name)};{"" if owned else "filter:grayscale(1)"}"></div>' if kind == "Person"
            else f'<div style="width:32px;height:32px;border-radius:50%;background:#fff;box-shadow:inset 0 0 0 1px var(--sep-strong);display:flex;align-items:center;justify-content:center" class="c2">{ico("pin" if kind == "Place" else "tag",14)}</div>')
    own = st("ok", "In library", 12) if owned else '<span class="t-call c2">Not in library</span>'
    return (f'<div class="row g16 center" style="height:48px;padding:0 8px;border-radius:8px;{"background:var(--accent-tint)" if sel else ""}">{lead}'
            f'<div style="width:176px" class="t-head trunc">{name}</div><div class="f1 t-body trunc">{conn}</div><div style="width:96px">{own}</div>'
            f'<div style="width:48px;text-align:right" class="t-body num c2">{steps}</div></div>')
def lgroup(title, n, rows):
    return f'<div class="t-eye" style="padding:16px 8px 4px">{title} · {n}</div>' + rows
lhead = ('<div class="row g16 t-cap c2" style="padding:0 8px 4px;font-weight:600"><div style="width:32px"></div><div style="width:176px">Name</div><div class="f1">Connection to Mark Hollis</div>'
         '<div style="width:96px">Library</div><div style="width:48px;text-align:right">Steps</div></div><div class="hr"></div>')
lst = (lhead + lgroup("Produced and engineered", 2, lrow("Person", "Tim Friese-Greene", "Producer on Spirit of Eden and Laughing Stock", False, 1, True) + lrow("Person", "Phill Brown", "Engineer on Spirit of Eden and Laughing Stock", False, 1))
       + lgroup("Played with", 4, lrow("Person", "Lee Harris", "Drums on 5 albums · member of Talk Talk", True, 1) + lrow("Person", "Paul Webb", "Bass on 3 albums · member of Talk Talk", True, 1)
                + lrow("Person", "Danny Thompson", "Double bass on Spirit of Eden", True, 1) + lrow("Person", "Mark Feltham", "Harmonica on 3 albums", False, 1))
       + lgroup("Albums", 5, lrow("Album", "Spirit of Eden", "Lead vocals, guitar, piano · Talk Talk · 1988", True, 1, key="eden") + lrow("Album", "Laughing Stock", "Lead vocals, guitar, organ · Talk Talk · 1991", True, 1, key="laughing")
                + lrow("Album", "Smiling & Waving", "Link: producer on 2 tracks, not confirmed as a credit · Anja Garbarek · 2001", False, 1, key="deer")))
body = header("Connections", sub) + controls(view="List") + f'<div class="row g16"><div class="f1">{lst}<div class="row between center mt8"><span class="t-cap c2">Showing 11 of 16 · sorted by kind, then steps</span><span class="btn sm">Load more</span></div></div>{inspector_sel()}</div>'
window("connections--list", "Connections, list view", "connections", body, h=960, playing=False)

# empty: no start chosen
sugg = "".join(f'<div class="col center g8" style="width:112px"><div style="width:72px;height:72px;border-radius:50%;background:{avatar_bg(n)};box-shadow:inset 0 0 0 2px #1D1D1F"></div>'
               f'<div class="t-head" style="text-align:center">{n}</div><div class="t-cap c2">{c} albums</div></div>'
               for n, c in [("Talk Talk", 5), ("Cocteau Twins", 9), ("Can", 7), ("Alice Coltrane", 6), ("Stereolab", 8), ("Low", 11)])
empty = (header("Connections", sub) + controls(name="", back=False, focus=True)
         + f'<div class="panel" style="padding:32px"><div class="t-title2">Start from an artist you own</div>'
         f'<div class="t-body c2 mt8 measure">Type a name above, or pick one of the artists you have the most albums by. The graph shows people, albums, places and labels within the reach you choose.</div>'
         f'<div class="row g16 mt24">{sugg}</div><div class="hr mt24"></div><div class="mt16">{KEY}</div></div>')
window("connections--empty", "Connections, no start chosen", "connections", empty, h=832, playing=False)

# not loaded for this artist + request update
nl = (header("Connections", sub) + controls(name="Bark Psychosis", back=False)
      + f'<div class="row g16"><div class="f1"><div class="notice inf" style="align-items:center">{ico("info",16,2,"inf")}<div><b>Not loaded.</b> The server has no MusicBrainz data for Bark Psychosis yet. This says nothing about the artist.</div>'
      f'<span class="btn sm">Request update</span></div>'
      f'<div class="notice ok mt8" style="align-items:center">{ico("checkc",16,2,"ok")}<div><b>Requested.</b> The server fetches it on its next run. Come back later; this page does not need to stay open.</div></div>'
      f'<div style="height:400px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px">{face("person", "Bark Psychosis", True, 72)}<div class="t-head">Bark Psychosis</div>'
      f'<div class="t-call c2">No connections to draw yet.</div></div></div>{inspector_idle("Bark Psychosis").replace("16 connections within 2 steps · 9 in your library", "In your library · 2 albums").replace("MusicBrainz data: loaded on the server.", "MusicBrainz data: not on the server yet.")}</div>')
window("connections--not-loaded", "Connections, data not loaded, update requested", "connections", nl, h=832, playing=False)

# truncated at 3 steps, and the request failed
tr = (header("Connections", sub) + controls(depth=3)
      + f'<div class="notice wa" style="align-items:center;margin-bottom:8px">{ico("warn",16,2,"wa")}<div><b>Showing the first 200 connections.</b> The server stops a walk at 200 rows or 2 seconds. Turn on Credits only, lower the reach, or use List to page through the rest.</div>'
      f'<span class="btn sm">Switch to List</span></div>'
      + f'<div class="notice da" style="align-items:center;margin-bottom:8px">{ico("xc",16,2,"da")}<div><b>Couldn’t load more.</b> Librarian did not answer in time. The connections already shown are kept.</div><span class="btn sm">Try again</span></div>'
      + f'<div class="row g16"><div class="f1"><div style="margin:-8px 0 0 -4px">{graph(selected=None)}</div>{foot.replace("16 of 43 connections", "200 of 200+ connections")}</div>{inspector_idle()}</div>')
window("connections--truncated-error", "Connections, truncated walk and a failed load", "connections", tr, h=1056, playing=False)
