"""Android mockups, Day · Sand only (healthy states). Run: python3 build.py android"""
from common import *
from mac_shell import chart_line, chart_cols, chart_pairs, chart_dumbbell

import os
BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "android"))
PAGES = {}
OUTS = {BASE + "/day": PAGES}

def doc(title, body, cls=""):
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>{title}</title>\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<link rel="stylesheet" href="../android.css"></head>\n<body class="theme-day {cls}">\n<div class="board">\n{body}\n</div>\n</body></html>')

SB = '<div class="statusbar"><span>21:14</span><span>5G ▮▮▮ 82%</span></div>'
def topbar(title=None, back=False, actions=("download", "gear")):
    lead = f'<span class="tap" style="margin-left:-12px">{ico("back",24)}</span>' if back else ""
    t = f'<span class="t-h2 f1">{title}</span>' if title else '<span class="word">discair</span>'
    acts = "".join(f'<span class="tap">{ico(a,24)}{"<span class=dot>2</span>" if a == "download" else ""}</span>' for a in actions)
    return f'<div class="topbar">{lead}{t}{acts}</div>'
def island(on="Home"):
    items = [("home", "Home"), ("sparkles", "Discover"), ("library", "Library"), ("search", "Search")]
    return '<div class="island">' + "".join(f'<div class="d{" on" if l == on else ""}">{ico(i,20)}{l}</div>' for i, l in items) + '</div>'
MINI = (f'<div class="mini">{cover("laughing",40,20)}<div class="f1"><div class="t-body2 trunc" style="font-weight:600">After the Flood</div><div class="t-small c2 trunc">Talk Talk</div></div>'
        f'<span class="tap">{ico("pause",24)}</span></div>')
def phone(cap, content, nav="Home", mini=True, bar=None, overlay=""):
    n = (MINI if mini else "") + island(nav) if nav else ""
    return (f'<div class="framecol"><div class="cap">{cap}</div><div class="phone">{SB}{bar if bar is not None else topbar()}<div class="scroll">{content}</div>{n}{overlay}</div></div>')
def page(name, title, frames, w, h=780, cls=""):
    PAGES[name] = (doc(f"Discair Android · Day · {title}", "\n".join(frames), cls), w + 48, h + 48 + 24)
W3 = 3 * 360 + 2 * 32

def st(kind, text):
    icon = {"ok": "checkc", "wa": "warn", "da": "xc", "inf": "info"}[kind]
    return f'<span class="st {kind}">{ico(icon,16,2)}{text}</span>'
def track(step, pct=None):
    return '<div class="track">' + "".join(f'<i class="{"d" if i < step else ("c" if i == step else "")}"></i>' for i in range(4)) + '</div>'
def dumb(w, rows): return chart_dumbbell(w, rows, labelw=84).replace("#F5F5F7", "var(--surface)").replace("font-size:13px", "font-size:12px;font-family:'Open Sans'")

# ------------------------------------------------------------------ dashboard
hero = (f'<div class="hero" style="padding:8px 0 16px"><div class="t-eye">Your library</div><div class="row base g8"><span class="t-display">1,284</span><span class="t-title c2">albums</span></div>'
        f'<div class="row g4 center t-body2"><span class="ok">{ico("arrowu",16,2.4)}</span>12 added in the last 30 days · 7 in the 30 before</div></div>')
def chip_stat(eye, val, unit, ch, w=148):
    return (f'<div class="card" style="width:{w}px;flex:none;padding:16px"><div class="t-eye trunc">{eye}</div><div class="row base g4 mt4"><span class="t-num">{val}</span><span class="t-small c2">{unit}</span></div>'
            f'<div class="t-small mt4">{ch}</div></div>')
stats = (f'<div class="row g8" style="margin-right:-16px;overflow:hidden">{chip_stat("Listens · 7 days", "214", "plays", "▲ 18% vs the 7 before")}'
         f'{chip_stat("Never played", "96", "albums", "▼ 4 since 1 October")}{chip_stat("Waiting", "7", "picks", "2 arrivals unplayed")}</div>')
pick = (f'<div class="card mt16"><div class="row between center"><span class="tag">Today’s pick</span><span class="t-label c2">1 / 7</span></div>'
        f'<div class="row g16 mt16">{cover("hex",112,4)}<div class="f1"><div class="t-h2">Hex</div><div class="t-body2 c2 mt4">Bark Psychosis · 1994</div><div class="t-small c2 mt4">Post-rock · not in your library</div></div></div>'
        f'<div class="row g8 mt16"><span class="btn pri f1">{ico("cloud",20,2)}Get album</span><span class="btn" style="padding:0 16px">Save</span><span class="tap" style="margin-right:-8px">{ico("morev",24)}</span></div></div>')
d1 = hero + stats + pick

def arr(key, t, s, tr="", right=""):
    return f'<div class="lrow">{cover(key,48,4)}<div class="f1"><div class="t-title trunc">{t}</div><div class="t-small c2 trunc">{s}</div>{f"<div class=mt4>{tr}</div>" if tr else ""}</div>{right}</div>'
arrivals = (f'<div class="card"><div class="row between center"><span class="t-h2">Arrivals</span><span class="btn text sm">All downloads</span></div>'
            + arr("pygmalion", "Pygmalion", "Slowdive · Downloading · 64%", track(1)) + arr("hats", "Hats", "The Blue Nile · Arrived today", right=f'<span class="tap">{ico("play",24)}</span>') + '</div>')
taste = (f'<div class="card mt16"><div class="t-eye">Your taste · last 90 days</div><div class="t-headline mt8">More ambient, less post-punk lately.</div>'
         f'<div class="mt16">{dumb(294, [("Ambient", 9, 17), ("Post-punk", 14, 8)])}</div><div class="row between center mt8"><span class="t-small c2">1,240 listens against 48,912 overall</span><span class="btn text sm">Details</span></div></div>')
insight = (f'<div class="card mt16"><span class="tag">Anniversary</span><div class="row g16 mt16">{cover("loveless",64,4)}<div class="f1"><div class="t-title">Loveless turned 35 on 4 November</div>'
           f'<div class="t-small c2 mt4">In your library · last played 14 months ago</div></div></div><div class="row g8 mt16"><span class="btn tonal f1">{ico("play",16)}Play</span><span class="btn" style="padding:0 16px">Why?</span></div></div>')
d2 = '<div style="height:8px"></div>' + arrivals + taste + insight

spark, _ = chart_line(294, 96, GROWTH, ["Dec", "Jun", "Nov"], [1000, 1300], pad=(8, 40, 20, 0))
nums = (f'<div class="card"><div class="row between center"><span class="t-h2">Library in numbers</span><span class="btn text sm">Open stats</span></div>'
        f'<div class="t-small c2 mt4">Albums over the last 12 months</div><div class="mt8">{spark}</div></div>')
shelf = ('<div class="sech"><span class="t-h2">Recently added</span><span class="btn text sm">Library</span></div><div class="row g8" style="margin-right:-16px;overflow:hidden">'
         + "".join(f'<div style="width:112px;flex:none">{cover(k,112,4)}<div class="t-body2 trunc mt8" style="font-weight:600">{ALBUMS[k][0]}</div><div class="t-small c2 trunc">{ALBUMS[k][1]}</div></div>' for k in ["hats", "satchi", "third", "dots"]) + '</div>')
genres = ('<div class="sech"><span class="t-h2">Genres</span></div><div class="row g8" style="flex-wrap:wrap">' + "".join(f'<span class="chip">{g}</span>' for g in ["Dream pop", "Ambient", "Post-rock"]) + '</div>')
server = (f'<div class="lrow mt16" style="border-top:1px solid var(--edge)">{ico("radio",24)}<div class="f1"><div class="t-title">Radio</div><div class="t-small c2">Last heard: FIP, 08:42</div></div>{ico("chevr",20)}</div>'
          f'<div class="lrow"><span class="ok">{ico("checkc",24)}</span><div class="f1"><div class="t-title">Server: all quiet</div><div class="t-small c2">Lenses refreshed 2 hours ago</div></div>{ico("chevr",20)}</div>')
d3 = '<div style="height:8px"></div>' + nums + shelf + genres + server
page("dashboard", "Dashboard", [phone("1 · Dashboard, first screen", d1), phone("2 · scrolled: arrivals, taste, insight", d2), phone("3 · scrolled: numbers, shelves, radio, server", d3, mini=False)], W3)

# ------------------------------------------------------------------ stats (new screen)
ERAS = [("1960s", 6, 4), ("1970s", 17, 12), ("1980s", 21, 19), ("1990s", 27, 38), ("2000s", 15, 14), ("2010s", 10, 9), ("2020s", 4, 4)]
line, _ = chart_line(294, 176, GROWTH, ["Dec", "Mar", "Jun", "Sep", "Nov"], [1000, 1100, 1200, 1300], sel=19, pad=(8, 40, 24, 0))
s1 = (f'<div class="row g8" style="margin-bottom:16px"><span class="chip">3M</span><span class="chip on">1Y</span><span class="chip">5Y</span><span class="chip">All</span></div>'
      f'<div class="card"><div class="t-title">Collection over time</div><div class="t-small c2">Albums in your library · Dec 2025 to today</div>'
      f'<div class="row base g8 mt8"><span class="t-num">1,171</span><span class="t-small c2">albums on 12 July 2026</span></div><div class="mt8">{line}</div>'
      f'<div class="t-small c2 mt4">Touch and drag the chart to read a date.</div></div>'
      f'<div class="card mt16"><div class="t-title">Own and play, by decade</div><div class="t-small c2">Share of albums against share of listens, 90 days</div><div class="mt8">{chart_pairs(294, ERAS, hi="1990s", rowh=28, valw=40)}</div>'
      f'<div class="row g16 t-small c2 mt8"><span>▬ Albums you own</span><span class="ca">▬ Listens</span></div></div>')
s2 = (f'<div class="card"><div class="t-title">Shelf life</div><div class="t-small c2">Albums by time since the last play · today</div>'
      f'<div class="mt8">{chart_cols(294, 176, [212, 318, 204, 263, 191, 96], ["Month", "1–6m", "6–12m", "1–2y", "2y+", "Never"], hi_idx=5, valuelabels=True, pad=(24, 0, 24, 0))}</div>'
      f'<div class="mt16"><span class="btn tonal" style="width:100%">Play something unplayed</span></div></div>'
      f'<div class="card mt16"><div class="t-title">When you listen</div><div class="t-small c2">Share of listens by time of day, UTC · all time</div>'
      f'<div class="mt8">{chart_cols(294, 152, [9, 31, 22, 38], ["Night", "Morning", "Afternoon", "Evening"], hi_idx=3, valuelabels=True, pad=(24, 0, 24, 0), barw=.5)}</div></div>')
page("stats", "Library stats", [phone("1 · Stats: growth and decades", s1, None, bar=topbar("Library stats", True, ())), phone("2 · Stats: shelf life and rhythm", s2, None, bar=topbar("Library stats", True, ()))], 2 * 360 + 32)

# ------------------------------------------------------------------ discover, insights, taste sheet
tabs = lambda on: '<div class="row g8" style="margin:0 -16px 16px 0;overflow:hidden">' + "".join(f'<span class="chip{" on" if t == on else ""}">{t}</span>' for t in ["For you", "New releases", "Classics", "Insights", "Saved"]) + '</div>'
def dcard(k):
    t, a, y, *_ = ALBUMS[k]
    return (f'<div class="card" style="padding:0;overflow:hidden;width:156px"><div style="position:relative">{cover(k,154,0)}<span class="tap" style="position:absolute;right:4px;bottom:4px;background:rgba(20,18,17,.72);color:#fff;border-radius:24px">{ico("cloud",24)}</span></div>'
            f'<div style="padding:8px 16px 16px"><div class="t-title trunc">{t}</div><div class="t-small c2 trunc">{a}</div><div class="t-label ca mt4">{y}</div></div></div>')
disc = tabs("For you") + '<div class="row g16" style="flex-wrap:wrap">' + "".join(dcard(k) for k in ["hex", "treasure", "karma", "tnt"]) + '</div>'
lens = (f'<div class="card mt16"><div class="row between center"><span class="tag">Series</span><span class="t-label c2">4 / 5 OWNED</span></div><div class="t-title mt8">Talk Talk studio albums</div><div class="t-small c2">Missing: The Party’s Over (1982)</div>'
        f'<div class="track mt8"><i></i><i class="d"></i><i class="d"></i><i class="d"></i><i class="d"></i></div><div class="row g8 mt16"><span class="btn tonal f1">Get</span><span class="btn" style="padding:0 16px">Why?</span><span class="tap">{ico("morev",24)}</span></div></div>')
ins = tabs("Insights") + taste.replace("card mt16", "card", 1) + lens + '<div class="t-small c2 mt16">Blind Spots and Hidden Canon are off. The server turns a lens on only after it passes its check.</div>'
GEN = [("Dream pop", 19), ("Ambient", 17), ("Post-rock", 14), ("Spiritual jazz", 11), ("Krautrock", 9)]
gbars = "".join(f'<div class="row center g8" style="height:32px"><span class="t-body2" style="width:104px;{"font-weight:600" if i == 1 else ""}">{g}</span><div class="f1" style="height:8px;border-radius:4px;background:var(--chart-ghost)">'
                f'<div class="barx" style="height:100%;width:{v*5}%;border-radius:4px;background:{"var(--chart-1)" if i == 1 else "var(--chart-2)"}"></div></div><span class="t-label num" style="width:32px;text-align:right">{v}%</span></div>' for i, (g, v) in enumerate(GEN))
tsheet = (f'<div class="scrim"></div><div class="bsheet"><div class="grab"></div><div class="t-h2">Your taste</div><div class="seg mt16"><span class="on">90 days</span><span>Year</span><span>All time</span></div>'
          f'<div class="row g8 mt16">{"".join(f"<span class=\'chip{' on' if d == 'Genre' else ''}\'>{d}</span>" for d in ["Genre", "Decade", "Area", "Label"])}</div>'
          f'<div class="mt16">{gbars}</div><div class="t-small c2 mt8">Share of 1,240 listens · 1,102 carried a genre</div><div class="mt16"><span class="btn pri" style="width:100%">Make an Ambient playlist</span></div></div>')
page("discover", "Discover, Insights and the taste sheet", [phone("1 · Discover: For you", disc, "Discover"), phone("2 · Discover: Insights", ins, "Discover"), phone("3 · Taste bottom sheet", ins, "Discover", overlay=tsheet)], W3)

# ------------------------------------------------------------------ library, albums, search
def arow(n, c): return f'<div class="lrow"><div style="width:48px;height:48px;border-radius:24px;background:{avatar_bg(n)}"></div><div class="f1"><div class="t-title trunc">{n}</div><div class="t-small c2">{c} albums</div></div>{ico("chevr",20)}</div>'
libhead = lambda on: (f'<div class="t-h1" style="padding:8px 0 16px">Library</div><div class="seg"><span class="{"on" if on == "Artists" else ""}">Artists</span><span class="{"on" if on == "Albums" else ""}">Albums</span></div>'
                      f'<div class="row between center" style="min-height:48px"><span class="t-small c2">{"733 artists" if on == "Artists" else "1,284 albums"} · A to Z</span><span class="row g4 center t-body2" style="font-weight:600">{ico("sort",20)}Sort</span></div>')
lib1 = libhead("Artists") + "".join(arow(n, c) for n, c in [("Alice Coltrane", 6), ("Arthur Russell", 4), ("Bark Psychosis", 2), ("Boards of Canada", 5), ("Broadcast", 4), ("Can", 7)])
lib2 = libhead("Albums") + '<div class="row g16" style="flex-wrap:wrap">' + "".join(
    f'<div style="width:156px">{cover(k,156,4)}<div class="t-body2 trunc mt8" style="font-weight:600">{ALBUMS[k][0]}</div><div class="t-small c2 trunc">{ALBUMS[k][1]} · {ALBUMS[k][2]}</div></div>' for k in ["satchi", "echo", "hex", "mhtrtc", "tender", "future"]) + '</div>'
srch = (f'<div class="row center g8" style="height:56px;border-radius:28px;background:var(--surface);border:2px solid var(--accent);padding:0 16px;margin-top:8px">{ico("search",24)}<span class="t-body f1">talk talk</span>{ico("x",24)}</div>'
        f'<div class="t-small c2" style="padding:8px 0">In your library first, then everything else.</div><div class="t-eye mt8">Artists</div>{arow("Talk Talk", 4)}<div class="t-eye mt16">Albums</div>'
        + "".join(f'<div class="lrow">{cover(k,48,4)}<div class="f1"><div class="t-title trunc">{ALBUMS[k][0]}</div><div class="t-small c2">{ALBUMS[k][1]} · {ALBUMS[k][2]}</div></div>{r}</div>'
                  for k, r in [("eden", st("ok", "Owned")), ("laughing", st("ok", "Owned")), ("hope", f'<span class="tap">{ico("cloud",24)}</span>')]))
srch = srch.replace("I Could Live in Hope", "The Party’s Over").replace("Low · 1994", "Talk Talk · 1982")
page("library-search", "Library and Search", [phone("1 · Library: artists", lib1, "Library"), phone("2 · Library: albums", lib2, "Library"), phone("3 · Search", srch, "Search", mini=False, bar="")], W3)

# ------------------------------------------------------------------ downloads, settings, server
def drow(k, t, s, tr, words, acts=""):
    return (f'<div class="card mt16"><div class="row g16">{cover(k,56,4)}<div class="f1"><div class="t-title trunc">{t}</div><div class="t-small c2 trunc">{s}</div></div></div>'
            f'<div class="mt16">{tr}</div><div class="row between t-label c2 mt4"><span>Found</span><span>Download</span><span>Import</span><span>Library</span></div><div class="t-body2 mt8">{words}</div>{acts}</div>')
dl = ('<div class="t-small c2">1 on its way · 1 arrived today</div>'
      + drow("pygmalion", "Pygmalion", "Slowdive · FLAC 16/44", track(1), '<b>64%</b> · 7 of 9 files', '<div class="row g8 mt16"><span class="btn f1">Use next source</span></div>').replace("card mt16", "card mt8", 1)
      + drow("hats", "Hats", "The Blue Nile · FLAC 16/44", track(4), st("ok", "In your library") + " · arrived 17:26", f'<div class="row g8 mt16"><span class="btn pri f1">{ico("play",16)}Play</span></div>'))
def srow(i, t, s, r=None): return f'<div class="lrow">{ico(i,24)}<div class="f1"><div class="t-title">{t}</div><div class="t-small c2">{s}</div></div>{r or ico("chevr",20)}</div>'
sett = (srow("server", "Server and services", st("ok", "All working")) + srow("sun", "Appearance", "Day · Sand / Night · Discair fonts") + srow("wave", "Streaming quality", "Original")
        + srow("note", "Scrobble plays", "Reports plays to Navidrome", '<div class="sw on"></div>') + srow("tune", "Equalizer", "Off") + srow("radio", "Radio", "12 stations") + srow("wave", "ListenBrainz", "Connected as the-owner")
        + '<div class="mt32"><span class="btn dng" style="width:100%">Sign out…</span></div>')
def svc(i, t, s, state): return f'<div class="lrow">{ico(i,24)}<div class="f1"><div class="t-title">{t}</div><div class="t-small c2">{s}</div></div>{state}</div>'
srv = (f'<div class="card" style="background:var(--ok-dim);border-color:var(--ok-dim)"><div class="row g16 center"><span class="ok">{ico("checkc",32)}</span><div><div class="t-title">Everything is working</div><div class="t-small">Checked at 21:14</div></div></div></div>'
       '<div class="t-eye mt24">Services</div>' + svc("server", "Librarian", "Picks, downloads, insights", st("ok", "Connected")) + svc("note", "Navidrome", "Library and playback", st("ok", "Connected"))
       + svc("cloud", "slskd", "Downloads", st("ok", "Connected")) + svc("wave", "ListenBrainz", "Taste, popularity", st("ok", "Connected")) + svc("graph", "MusicBrainz data", "Paths", st("ok", "Loaded"))
       + '<div class="t-eye mt24">Server activity</div>' + svc("bulb", "Insight lenses", "Refreshed 2 hours ago", st("ok", "Done")) + svc("person", "Artist popularity", "340 artists left", st("inf", "Paused")))
page("downloads-settings-server", "Downloads, Settings and Server status",
     [phone("1 · Downloads", dl, None, bar=topbar("Downloads", True, ())), phone("2 · Settings", sett, None, bar=topbar("Settings", True, ())), phone("3 · Server and services (new)", srv, None, bar=topbar("Server", True, ("refresh",)))], W3)

# ------------------------------------------------------------------ tablet, 840dp: rail and two panes
rail = '<div class="rail">' + "".join(f'<div class="d{" on" if l == "Home" else ""}">{ico(i,24)}{l}</div>' for i, l in [("home", "Home"), ("sparkles", "Discover"), ("library", "Library"), ("search", "Search")]) + '</div>'
tab = (f'<div class="framecol"><div class="cap">Dashboard at 840dp: navigation rail, two panes (primary 2/3, secondary 1/3)</div><div class="tablet">{rail}<div class="f1">{SB}{topbar()}'
       f'<div class="row g16" style="padding:0 16px"><div style="flex:2;min-width:0">{hero}{pick.replace("card mt16", "card", 1)}</div><div style="flex:1;min-width:0" class="col g8">'
       f'{chip_stat("Listens · 7 days", "214", "plays", "▲ 18% vs the 7 before", w="auto")}{chip_stat("Never played", "96", "albums", "▼ 4 since 1 October", w="auto")}{chip_stat("Waiting", "7", "picks", "2 arrivals unplayed", w="auto")}</div></div></div></div></div>')
PAGES["dashboard-tablet"] = (doc("Discair Android · Day · Dashboard at 840dp", tab), 840 + 48, 600 + 72)

# ------------------------------------------------------------------ motion: the HTML animates, the PNG is a still
PAGES["motion"] = (doc("Discair Android · Day · Motion demo (open the HTML; reload to replay)",
                       "\n".join([phone("Enter: hero rises, cards stagger 50 ms", d1), phone("Charts: bars and tracks grow 400 ms", ins, "Discover", overlay=tsheet)]), "motion"), 2 * 360 + 32 + 48, 780 + 72)
