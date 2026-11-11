from mac_shell import *

def header(title, sub="", right=""):
    s = f'<div class="t-body c2 mt4 measure">{sub}</div>' if sub else ""
    return f'<div class="row between end" style="margin-bottom:24px"><div><div class="t-large">{title}</div>{s}</div><div class="row g8 center">{right}</div></div>'

def stat(eye, value, unit, change, hero=False, w="f1"):
    v = f'<span class="{"t-hero" if hero else "t-metric"}">{value}</span> <span class="{"t-title3" if hero else "t-body"} c2">{unit}</span>'
    return (f'<div class="col {w}" style="justify-content:flex-start"><div class="t-eye">{eye}</div><div class="{"mt4" if hero else "mt8"}">{v}</div>'
            f'<div class="row g4 center mt4">{change}</div></div>')

def band(listens=True, never=True):
    a = stat("Your library", "1,284", "albums", delta(True, "12 added in the last 30 days · 7 in the 30 before"), hero=True, w="f2")
    b = stat("Listens · last 7 days", "214", "plays", delta(True, "18% vs the 7 days before (181)")) if listens else \
        stat("Listens · last 7 days", "—", "", '<span class="t-call c2">Needs ListenBrainz.</span> <span class="link t-call">Connect</span>')
    c = stat("Never played", "96", "albums", delta(False, "4 fewer than on 1 October"))
    d = stat("Waiting for you", "7", "picks", '<span class="t-call c2">2 arrivals not played yet</span>')
    return f'<div class="row g24" style="margin-bottom:32px">{a}<div class="vr"></div>{b}<div class="vr"></div>{c}<div class="vr"></div>{d}</div>'

def pick_panel():
    keys = (f'<div class="row g16 center t-cap c2 mt16"><span><span class="key">→</span> Get</span><span><span class="key">↓</span> Save</span>'
            f'<span><span class="key">←</span> Not for me</span><span><span class="key">Space</span> Play the suggested track</span></div>')
    return (f'<div class="panel f2"><div class="row g24">{cover("hex", 232)}'
            f'<div class="col f1"><div class="row between center"><div class="t-eye">Today’s pick · 1 of 7</div>'
            f'<div class="row g4"><span class="iconbtn" style="color:var(--text-3)">{ico("chevl",16,2)}</span><span class="iconbtn">{ico("chevr",16,2)}</span></div></div>'
            f'<div class="t-title1 mt4">Hex</div><div class="t-body c2">Bark Psychosis · 1994 · Post-rock · not in your library</div>'
            f'<div class="t-body mt16 measure">You have played Talk Talk’s <i>Laughing Stock</i> 212 times. Hex was engineered in the same slow, room-first way, and listeners who keep one usually keep the other.</div>'
            f'<div class="row g8 center mt16"><span class="iconbtn" style="background:#E6E6EB;color:var(--text)">{ico("play",12)}</span>'
            f'<div><div class="t-head">The Loom</div><div class="t-call c2">Suggested track · 5:16</div></div></div>'
            f'<div style="flex:1"></div>'
            f'<div class="row g8 mt16"><span class="btn pri lg" style="padding:0 16px">{ico("cloud",16,2)}Get album</span><span class="btn lg">Save</span><span class="btn lg out" style="padding:0 16px">Not for me</span></div>'
            f'</div></div>{keys}</div>')

def arr_row(key, title, sub, right, tracker=""):
    t = f'<div class="mt4">{tracker}</div>' if tracker else ""
    return (f'<div class="lrow">{cover(key, 40, 8, "flat")}<div class="f1"><div class="ttl trunc">{title}</div>'
            f'<div class="sub trunc">{sub}</div>{t}</div>{right}</div>')

def arrivals_panel():
    rows = arr_row("pygmalion", "Pygmalion", "Slowdive · Downloading · 64%", "", stage_track(1, 64, w=196))
    rows += arr_row("tender", "Tender Buttons", "Broadcast · Looking for a source", "", stage_track(0, w=196))
    rows += arr_row("hats", "Hats", "The Blue Nile · Arrived today", f'<span class="btn sm">{ico("play",10)}Play</span>')
    rows += arr_row("rocknroll", "Sea Song", "Heard on FIP at 08:42", '<span class="btn sm">Get</span>')
    return (f'<div class="panel f1"><div class="panel-h"><div class="t-title2">Arrivals</div><span class="btn sm">All downloads</span></div>'
            f'<div style="margin-top:-8px">{rows}</div></div>')

def growth_panel(ghost=False):
    svg, (xs, ys) = chart_line(604, 232, GROWTH, ["Dec", "Feb", "Apr", "Jun", "Aug", "Oct", "Nov"], [1000, 1100, 1200, 1300], sel=None if ghost else 19,
                               annot=None if ghost else (12, "Biggest month: March, 31 added"), ghost=ghost)
    tip = "" if ghost else (f'<div class="tip" style="left:{xs[19]+28:.0f}px;top:{ys[19]-8:.0f}px"><b>1,171 albums</b>'
                            f'<span class="c2">12 July 2026 · 5 added that week</span></div>')
    empty = ('<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center">'
             '<div class="t-head">Not enough history yet</div><div class="t-call c2 mt4">The line appears once albums have been added in at least 3 different months.</div></div>') if ghost else ""
    return (f'<div class="panel f2"><div class="panel-h"><div><div class="t-title2">Collection over time</div>'
            f'<div class="t-call c2 mt4">Albums in your library, from the date each was added · 1 December 2025 to today</div></div>'
            f'<div class="row g8"><div class="seg"><span class="on">Total</span><span>Added</span></div>'
            f'<div class="seg"><span>3M</span><span class="on">1Y</span><span>5Y</span><span>All</span></div></div></div>'
            f'<div style="position:relative">{svg}{tip}{empty}</div></div>')

ERAS = [("1960s", 6, 4), ("1970s", 17, 12), ("1980s", 21, 19), ("1990s", 27, 38), ("2000s", 15, 14), ("2010s", 10, 9), ("2020s", 4, 4)]
def era_panel():
    return (f'<div class="panel f1"><div class="panel-h" style="margin-bottom:8px"><div><div class="t-title2">Own and play, by decade</div>'
            f'<div class="t-call c2 mt4">Share of albums against share of listens, last 90 days</div></div></div>'
            f'{chart_pairs(292, ERAS, hi="1990s")}'
            f'<div class="legend mt8"><span><i class="sq n"></i>Albums you own</span><span><i class="sq"></i>Listens</span></div></div>')

def taste_panel(empty=False):
    if empty:
        body = ('<div class="t-title1 mt4">Taste needs listening history.</div>'
                '<div class="t-body c2 mt8 measure">Connect ListenBrainz in Services, or keep playing. A window is described once it holds 100 listens.</div>'
                '<div class="mt16" style="height:8px;border-radius:4px;background:#E6E6EB"><i style="display:block;width:0;height:100%"></i></div>'
                '<div class="t-call c2 mt8">0 of 100 listens</div><div class="mt16"><span class="btn">Open Services</span></div>')
    else:
        body = (f'<div class="t-title1 mt4">More ambient, less post-punk lately.</div>'
                f'<div class="mt16">{chart_dumbbell(450, [("Ambient", 9, 17), ("Post-punk", 14, 8)])}</div>'
                f'<div class="legend mt8"><span><svg width="12" height="12"><circle cx="6" cy="6" r="4" fill="#F5F5F7" stroke="#8E8E93" stroke-width="2"/></svg> All time, 48,912 listens</span>'
                f'<span><svg width="12" height="12"><circle cx="6" cy="6" r="5" fill="#D61F4A"/></svg> Last 90 days, 1,240 listens</span></div>')
    return (f'<div class="panel f1"><div class="row between center"><div class="t-eye">Your taste · last 90 days against all time</div>'
            f'{"" if empty else "<span class=\'btn sm\'>Open Insights</span>"}</div>{body}</div>')

def lens_row(lead, title, sub, action):
    return f'<div class="lrow">{lead}<div class="f1"><div class="ttl trunc">{title}</div><div class="sub trunc">{sub}</div></div>{action}</div>'

def countbadge(big, small):
    return (f'<div style="width:48px;height:48px;border-radius:8px;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center">'
            f'<b class="num" style="font:700 17px/20px var(--font)">{big}</b><span class="t-cap c2" style="line-height:12px">{small}</span></div>')

def lenses_panel(off=False):
    if off:
        rows = ('<div class="t-body c2 measure">No lens is on yet. The server turns a lens on only after it passes its own check, so nothing here is a guess.</div>'
                f'<div class="row g8 mt16" style="flex-wrap:wrap">{pill("", "Forgotten Gems · off")}{pill("", "Series · off")}{pill("", "Blind Spots · off")}{pill("", "Hidden Canon · off")}{pill("", "Anniversaries · off")}</div>')
    else:
        rows = lens_row(cover("loveless", 48, 8, "flat"), "Loveless turned 35 on 4 November", "Anniversaries · in your library · last played 14 months ago", f'<span class="btn sm">{ico("play",10)}Play</span>')
        rows += lens_row(countbadge("4/5", "owned"), "Talk Talk studio albums", "Series · missing The Party’s Over (1982)", '<span class="btn sm">Get</span>')
        rows += lens_row(cover("echo", 48, 8, "flat"), "World of Echo", "Forgotten Gems · played 41 times, not since March 2024", f'<span class="btn sm">{ico("play",10)}Play</span>')
    return (f'<div class="panel f1"><div class="panel-h"><div class="t-title2">From the lenses</div>'
            f'<div class="row g8 center"><span class="t-call c2">{"0" if off else "3"} of 5 on</span>{"" if off else "<span class=\'btn sm\'>All insights</span>"}</div></div>'
            f'<div style="margin-top:-8px">{rows}</div></div>')

SHELF = [212, 318, 204, 263, 191, 96]
SHELF_L = ["This month", "1–6 mo", "6–12 mo", "1–2 years", "2+ years", "Never"]
def shelf_panel():
    dust = "".join(f'<div class="col g4" style="width:48px">{cover(k, 48, 8, "flat")}<div class="t-cap c2 trunc">{t}</div></div>'
                   for k, t in [("karma", "4 y 1 m"), ("tindrum", "3 y 8 m"), ("neu75", "3 y 2 m"), ("beehive", "2 y 11 m")])
    return (f'<div class="panel f2"><div class="panel-h" style="margin-bottom:8px"><div><div class="t-title2">Shelf life</div>'
            f'<div class="t-call c2 mt4">Albums by time since the last play · today, from Navidrome’s latest play of each album</div></div>'
            f'<span class="btn sm">Play something unplayed</span></div>'
            f'<div class="row g24 end">{chart_cols(400, 184, SHELF, SHELF_L, hi_idx=5, valuelabels=True, pad=(24, 0, 24, 0))}'
            f'<div class="col g8"><div class="t-eye">Longest since a play</div><div class="row g8">{dust}</div></div></div></div>')

def job(icon, name, state, detail, action=""):
    return (f'<div class="lrow" style="min-height:40px;padding:4px 0;gap:8px"><span class="c2">{ico(icon,16)}</span><div class="f1"><div class="row g8 center"><span class="t-head">{name}</span>{state}</div>'
            f'<div class="t-call c2 trunc">{detail}</div></div>{action}</div>')

def activity_panel():
    rows = job("bulb", "Insight lenses", st("ok", "Done"), "Refreshed 2 hours ago · next in 4 hours")
    rows += job("wave", "Taste profile", st("ok", "Done"), "At launch · 1,240 listens in the recent window")
    rows += job("person", "Artist popularity", st("inf", "Paused"), "340 artists left · runs only when asked", '<span class="btn sm">Continue</span>')
    rows += job("graph", "MusicBrainz data", st("ok", "Loaded"), "Graph coverage: broad")
    return (f'<div class="panel f1"><div class="panel-h" style="margin-bottom:8px"><div class="t-title2">Server activity</div><span class="btn sm">Services</span></div>{rows}</div>')

def recent_shelf():
    tiles = "".join(f'<div class="col" style="width:150px">{cover(k, 150, 8)}<div class="t-head trunc mt8">{ALBUMS[k][0]}</div><div class="t-call c2 trunc">{ALBUMS[k][1]}</div></div>'
                    for k in ["hats", "satchi", "third", "dots", "deer", "future"])
    return (f'<div class="row between center mt32" style="margin-bottom:16px"><div class="t-title2">Recently added</div><span class="btn sm">Library</span></div>'
            f'<div class="row g16">{tiles}</div>')

DATE = '<span class="t-body c2">Wednesday 11 November</span>'

# ---- default, full length
home = (header("Home", right=DATE) + band()
        + f'<div class="row">{pick_panel()}{arrivals_panel()}</div>'
        + f'<div class="row mt16">{growth_panel()}{era_panel()}</div>'
        + f'<div class="row mt16">{taste_panel()}{lenses_panel()}</div>'
        + f'<div class="row mt16">{shelf_panel()}{activity_panel()}</div>'
        + recent_shelf())
window("home--default-full", "Home, default, full length", "home", home, h=1990)
window("home--default", "Home, default, first screen", "home", home, h=832)

# ---- handoff banner (dependency: Android must save its play queue)
handoff = (f'<div class="notice inf" style="margin-bottom:24px;align-items:center">{ico("phone",16)}<div><b>Playing on your phone:</b> Ascension Day, Talk Talk · 2:41 of 6:00</div>'
           f'<span class="btn sm">{ico("play",10)}Continue on this Mac</span></div>')
window("home--handoff", "Home, pick up from phone", "home", header("Home", right=DATE) + handoff + band() + f'<div class="row">{pick_panel()}{arrivals_panel()}</div>', h=832, playing=False)

# ---- loading
def skel(w, h, r=8, mt=0): return f'<div class="sk" style="width:{w};height:{h}px;border-radius:{r}px;margin-top:{mt}px"></div>'
sband = '<div class="row g24" style="margin-bottom:32px">' + "".join(
    f'<div class="col {"f2" if i == 0 else "f1"}">{skel("96px", 16)}{skel("160px" if i == 0 else "72px", 48 if i == 0 else 32, 8, 8)}{skel("80%", 16, 8, 8)}</div>' + ('<div class="vr"></div>' if i < 3 else "")
    for i in range(4)) + '</div>'
spick = (f'<div class="panel f2"><div class="row g24">{skel("232px", 232)}<div class="col f1">{skel("120px", 16)}{skel("200px", 32, 8, 8)}{skel("260px", 16, 8, 8)}'
         f'{skel("100%", 16, 8, 24)}{skel("92%", 16, 8, 8)}{skel("60%", 16, 8, 8)}<div style="flex:1"></div><div class="row g8">{skel("128px", 40, 20)}{skel("72px", 40, 20)}{skel("112px", 40, 20)}</div></div></div>'
         f'<div class="mt16">{skel("420px", 24)}</div></div>')
sarr = '<div class="panel f1">' + skel("96px", 24) + "".join(f'<div class="row g16 center mt16">{skel("40px", 40)}<div class="f1">{skel("70%", 16)}{skel("90%", 12, 6, 8)}</div></div>' for _ in range(4)) + '</div>'
schart = f'<div class="panel f2">{skel("200px", 24)}{skel("100%", 200, 16, 16)}</div><div class="panel f1">{skel("180px", 24)}{skel("100%", 200, 16, 16)}</div>'
loading = (header("Home", right=DATE) + sband + f'<div class="row">{spick}{sarr}</div><div class="row mt16">{schart}</div>')
window("home--loading", "Home, loading", "home", loading, h=832, playing=False, status=("off", "Checking…"))

# ---- first run: no ListenBrainz, no lenses, no picks
nopick = (f'<div class="panel f2"><div class="t-eye">Today’s pick</div><div class="t-title1 mt4">No picks yet.</div>'
          f'<div class="t-body c2 mt8 measure">Picks come from your listening history. Connect Last.fm or ListenBrainz in Services and the first list is built within a few minutes. Nothing is suggested from guesses.</div>'
          f'<div class="row g8 mt16"><span class="btn pri lg">Open Services</span><span class="btn lg">Browse New releases</span></div></div>')
noarr = (f'<div class="panel f1"><div class="panel-h"><div class="t-title2">Arrivals</div></div><div class="t-body c2">Nothing on its way. Albums you Get appear here while they download, and stay until you have played them.</div></div>')
first = (header("Home", right=DATE)
         + f'<div class="row g24" style="margin-bottom:32px">{stat("Your library", "1,284", "albums", delta(True, "12 added in the last 30 days · 7 in the 30 before"), hero=True, w="f2")}<div class="vr"></div>'
         + stat("Listens · last 7 days", "—", "", '<span class="t-call c2">Needs ListenBrainz.</span>&nbsp;<span class="link t-call">Connect</span>') + '<div class="vr"></div>'
         + stat("Never played", "96", "albums", '<span class="t-call c2">First count today, no change yet</span>') + '<div class="vr"></div>'
         + stat("Waiting for you", "0", "picks", '<span class="t-call c2">Nothing on its way</span>') + '</div>'
         + f'<div class="row">{nopick}{noarr}</div><div class="row mt16">{taste_panel(True)}{lenses_panel(True)}</div>')
window("home--first-run", "Home, first run and empty data", "home", first, h=832, playing=False, status=("wa", "2 not set up"))

# ---- degraded, with the status popover open
def svc_line(icon, name, state, note=""):
    n = f'<div class="t-call c2">{note}</div>' if note else ""
    return f'<div class="row g8" style="padding:8px 0;align-items:flex-start"><span class="c2" style="margin-top:2px">{ico(icon,16)}</span><div class="f1"><div class="row between center"><span class="t-head">{name}</span>{state}</div>{n}</div></div>'
popover = (f'<div class="pop" style="top:64px;right:232px;width:340px"><div class="t-title3">One service needs attention</div>'
           f'<div class="t-call c2 mt4">Playback and Get are not affected.</div><div class="hr mt8"></div>'
           + svc_line("server", "Librarian", st("ok", "Connected")) + svc_line("note", "Navidrome", st("ok", "Connected"))
           + svc_line("cloud", "slskd", st("ok", "Connected"))
           + svc_line("wave", "ListenBrainz", st("da", "Token rejected"), "Taste and popularity are showing the last good data, from 9 November.")
           + svc_line("graph", "MusicBrainz data", st("ok", "Loaded"))
           + f'<div class="hr"></div><div class="row g8 mt16"><span class="btn pri">Fix ListenBrainz</span><span class="btn">Open Services</span></div></div>')
degr_notice = (f'<div class="notice wa" style="margin-bottom:24px;align-items:center">{ico("warn",16,2,"wa")}<div><b>Taste could not refresh.</b> ListenBrainz rejected the saved token. Figures marked “as of 9 November” are the last good ones.</div>'
               f'<span class="btn sm">Fix in Services</span></div>')
dband = (f'<div class="row g24" style="margin-bottom:32px">{stat("Your library", "1,284", "albums", delta(True, "12 added in the last 30 days · 7 in the 30 before"), hero=True, w="f2")}<div class="vr"></div>'
         + stat("Listens · as of 9 November", "198", "plays", f'<span class="st wa">{ico("warn",12,2.2)}</span><span class="t-call">Not updating</span>') + '<div class="vr"></div>'
         + stat("Never played", "96", "albums", delta(False, "4 fewer than on 1 October")) + '<div class="vr"></div>'
         + stat("Waiting for you", "7", "picks", '<span class="t-call c2">2 arrivals not played yet</span>') + '</div>')
window("home--degraded", "Home, a service degraded, status popover open", "home",
       header("Home", right=DATE) + degr_notice + dband + f'<div class="row">{pick_panel()}{arrivals_panel()}</div>',
       h=832, status=("wa", "1 needs attention"), overlay=popover)

# ---- Librarian unreachable: Navidrome-only content stays
off_banner = (f'<div class="notice da" style="margin-bottom:24px;align-items:center">{ico("xc",16,2,"da")}<div><b>Can’t reach Librarian.</b> Your library still plays from Navidrome. Picks, arrivals, taste and insights return when the server answers.</div>'
              f'<span class="btn sm">Try again</span></div>')
oband = (f'<div class="row g24" style="margin-bottom:32px">{stat("Your library", "1,284", "albums", delta(True, "12 added in the last 30 days · 7 in the 30 before"), hero=True, w="f2")}<div class="vr"></div>'
         + stat("Never played", "96", "albums", delta(False, "4 fewer than on 1 October")) + '<div class="vr"></div>'
         + stat("Listens · Waiting", "—", "", '<span class="t-call c2">Unavailable without Librarian</span>', w="f2") + '</div>')
offline = header("Home", right=DATE) + off_banner + oband + f'<div class="row">{shelf_panel()}<div class="panel f1"><div class="t-title2">Server activity</div><div class="t-body c2 mt16">Unknown. The app asks Librarian for this, and Librarian is not answering at 100.92.14.7:8080.</div><div class="mt16"><span class="btn">Open Services</span></div></div></div>' + recent_shelf()
window("home--librarian-unreachable", "Home, Librarian unreachable", "home", offline, h=832, playing=False, status=("da", "Librarian unreachable"))
