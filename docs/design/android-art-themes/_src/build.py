#!/usr/bin/env python3
"""Writes the Android art-theme mockups (Soft Brut and Flow) and renders a PNG beside each.

    python3 build.py            # every page of both themes
    python3 build.py sb home    # one theme (sb or fl), named pages

Design tooling only: nothing imports it and no test collects it. The tokens and component looks live in
../shared.css, ../soft-brut.css and ../flow.css; this file holds only the page content, written once and
drawn by both themes. Home is the exception: each theme composes its own.
PNGs need Google Chrome at its default macOS path; the HTML is written either way.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
THEMES = {"sb": ("soft-brut", "Soft Brut · Lavender"), "fl": ("flow", "Flow · Warm white")}

ICONS = {
    "home": '<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z"/>',
    "disc": '<path d="M12 3l1.800 5.200L19 10l-5.200 1.800L12 17l-1.800-5.200L5 10l5.200-1.800zM18.500 16l.7 1.800 1.800.7-1.800.7-.7 1.800-.7-1.800-1.800-.7 1.800-.7z"/>',
    "lib": '<path d="M5 4v16M9.500 4v16M14 5l4.500 14.500"/>',
    "search": '<circle cx="11" cy="11" r="6.500"/><path d="M16 16l4.500 4.500"/>',
    "play": '<path d="M7 4.500v15l12.500-7.500z"/>',
    "pause": '<path d="M7 5h3.500v14H7zM13.500 5H17v14h-3.500z"/>',
    "next": '<path d="M5 5v14l10-7zM17 5h2.500v14H17z"/>',
    "prev": '<path d="M19 5v14L9 12zM4.500 5H7v14H4.500z"/>',
    "dl": '<circle cx="12" cy="12" r="8.500"/><path d="M12 7.500v8M8.500 12.500L12 16l3.500-3.500"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 2.500v3M12 18.500v3M2.500 12h3M18.500 12h3M5.300 5.300l2.100 2.100M16.600 16.600l2.100 2.100M5.300 18.700l2.100-2.100M16.600 7.400l2.100-2.100"/>',
    "more": '<circle cx="5" cy="12" r="1.600"/><circle cx="12" cy="12" r="1.600"/><circle cx="19" cy="12" r="1.600"/>',
    "chev": '<path d="M9 5l7 7-7 7"/>',
    "back": '<path d="M15 5l-7 7 7 7"/>',
    "down": '<path d="M5 9l7 7 7-7"/>',
    "radio": '<rect x="3" y="8" width="18" height="12" rx="2"/><path d="M7 8l9-4"/><circle cx="8.500" cy="14" r="2.500"/><path d="M14 12.500h4M14 15.500h4"/>',
    "get": '<path d="M7 18a4.500 4.500 0 0 1-.6-8.960 6 6 0 0 1 11.700 1.500A3.800 3.800 0 0 1 17.500 18M12 11v8M9 16.500l3 3 3-3"/>',
    "heart": '<path d="M12 20s-7-4.300-7-9.500A4 4 0 0 1 12 8a4 4 0 0 1 7 2.500C19 15.700 12 20 12 20z"/>',
    "check": '<path d="M5 12.500l4.500 4.500L19 7.500"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "queue": '<path d="M4 7h16M4 12h16M4 17h10"/>',
    "qadd": '<path d="M4 7h12M4 12h12M4 17h7M18 14v6M15 17h6"/>',
    "shuffle": '<path d="M4 7h3l10 10h3M4 17h3l3-3M14 10l3-3h3M18 5l2 2-2 2M18 15l2 2-2 2"/>',
    "repeat": '<path d="M5 11V9a2 2 0 0 1 2-2h11M16 4l3 3-3 3M19 13v2a2 2 0 0 1-2 2H6M8 20l-3-3 3-3"/>',
    "quote": '<path d="M5 6h14v10H10l-4 3v-3H5z"/>',
    "tune": '<path d="M6 4v16M12 4v16M18 4v16"/><circle cx="6" cy="9" r="2"/><circle cx="12" cy="15" r="2"/><circle cx="18" cy="8" r="2"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.600 5.600l1.400 1.400M17 17l1.400 1.400M5.600 18.400L7 17M17 7l1.400-1.400"/>',
    "server": '<rect x="4" y="4" width="16" height="7" rx="1.500"/><rect x="4" y="13" width="16" height="7" rx="1.500"/><path d="M7.500 7.500h.01M7.500 16.500h.01"/>',
    "swap": '<path d="M4 8h13M14 5l3 3-3 3M20 16H7M10 13l-3 3 3 3"/>',
    "wave": '<path d="M4 12h2l2-6 3 12 3-9 2 5 1-2h3"/>',
    "sort": '<path d="M7 5v14M4 16l3 3 3-3M14 7h6M14 12h4M14 17h2"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "path": '<circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/><path d="M8 18h5a3 3 0 0 0 0-6h-2a3 3 0 0 1 0-6h5"/>',
    "info": '<circle cx="12" cy="12" r="8.500"/><path d="M12 11v5M12 8h.01"/>',
    "out": '<path d="M10 5H5v14h5M14 8l4 4-4 4M18 12H9"/>',
}
SPRITE = '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>' + "".join(
    f'<symbol id="i-{k}" viewBox="0 0 24 24">{v}</symbol>' for k, v in ICONS.items()) + "</defs></svg>"


def ic(n, c=""): return f'<svg class="{c}"><use href="#i-{n}"/></svg>'
def cv(k, c="", s=""): return f'<i class="cv k{k} {c}" style="{s}"></i>'
def ar(a, c="", s=""): return f'<i class="ar a{a} {c}" style="{s}"></i>'
def btn(label, c="", icon=None): return f'<span class="btn {c}">{ic(icon) if icon else ""}{label}</span>'
def chips(names, on=0): return '<div class="hs" style="gap:8px">' + "".join(f'<span class="chip{" on" if i == on else ""}">{n}</span>' for i, n in enumerate(names)) + "</div>"
def tabs(names, on=0): return '<div class="tabs">' + "".join(f'<span class="{"on" if i == on else ""}">{n}</span>' for i, n in enumerate(names)) + "</div>"
def h(title, link=""): return f'<div class="h"><h3>{title}</h3>{f"<a>{link}</a>" if link else ""}</div>'
def li(lead, title, sub="", trail=None, c=""):
    trail = ic("chev", "chev") if trail is None else trail
    return f'<div class="li {c}">{lead}<div class="sp"><h4 class="el">{title}</h4>{f"<p class=\'mut sm el\'>{sub}</p>" if sub else ""}</div>{trail}</div>'
def icon(n): return f'<span class="ic">{ic(n)}</span>'
def cap(k, title, sub, c=""): return f'<div class="cap {c}">{cv(k, s="width:100%;margin-bottom:8px")}<b class="el">{title}</b><span class="el" style="display:block">{sub}</span></div>'
def who(a, name): return f'<div class="who">{ar(a, "rd")}{name}</div>'
def sw(on=True): return f'<i class="sw{" on" if on else ""}"></i>'
def status(): return '<div class="status"><span>21:14</span><span>5G 82%</span></div>'
def top(title, wm=False):
    return (f'<div class="top"><span class="lt{" wm" if wm else ""}">{title}</span><span class="sp"></span>'
            f'<span class="ib">{ic("dl")}<i class="bdg">2</i></span><span class="ib">{ic("gear")}</span></div>')
def bar(title="", action=""): return f'<div class="bar"><span class="ib">{ic("back")}</span><h4 class="sp el">{title}</h4>{action}</div>'
def trk(stage, bad=False):
    names = ["Found", "Downloading", "Importing", "In library"]
    segs = "".join(f'<i class="{"bad" if bad and i == stage else "on" if i <= stage else ""}"></i>' for i in range(4))
    return f'<div class="trk">{segs}</div><div class="trkn mut">' + "".join(f"<span>{n}</span>" for n in names) + "</div>"

MINI = f'<div class="mini">{cv(5)}<div class="sp"><h4 class="el">After the Flood</h4><p class="mut sm">Talk Talk</p></div>{ic("pause", "f")}</div>'
def nav(on=0):
    items = [("home", "Home"), ("disc", "Discover"), ("lib", "Library"), ("search", "Search")]
    return '<div class="nav">' + "".join(f'<span class="{"on" if i == on else ""}">{ic(n)}{l}</span>' for i, (n, l) in enumerate(items)) + "</div>"

def frame(t, caption, body, dock=0, cls="", over="", style=""):
    """dock: a tab index (0-3) draws the mini player and the navigation; 'stack' the mini player only; None nothing."""
    d = "" if dock is None else f'<div class="dock">{MINI}{"" if dock == "stack" else nav(dock)}</div>'
    return (f'<figure><figcaption>{caption}</figcaption><div class="phone {t} {cls}" style="{style}">'
            f'<div class="scr">{status()}{body}</div>{d}{over}</div></figure>')

PICK_ACTS = f'<div class="pad row">{btn("Get album", "p sp", "get")}{btn("Save", "t")}{btn(ic("more", "f"), "sq")}</div>'

# ---------------------------------------------------------------------------------------------------- Home (own per theme)

def sb_home():
    stack = f'<div class="stack">{cv(3, "b2")}{cv(2, "b1")}{cv(1, "f")}</div>'
    a = (top("discair", True) + '<div class="h"><span class="eb">Today\'s picks</span><span class="eb">1 / 7</span></div>' + stack
         + '<div class="pad"><h2>Hex</h2><p class="mut">Bark Psychosis · 1994 · Post-rock</p></div>' + PICK_ACTS
         + h("In rotation", "All artists")
         + '<div class="hs">' + who(1, "Alice Coltrane") + who(2, "The Blue Nile") + who(3, "Talk Talk") + who(4, "Slowdive") + who(5, "Portishead") + "</div>")
    arrival = (f'<div class="pad"><div class="card row">{cv(4, s="width:52px")}<div class="sp"><h4>Pygmalion</h4>'
               '<p class="mut sm" style="margin-bottom:6px">Slowdive · Downloading · 64%</p><div class="prog"><i style="width:64%"></i></div></div></div></div>')
    radio = (f'<div class="pad"><div class="tile radio row">{ic("radio")}<div class="sp"><h4>Radio</h4><p class="sm">Last heard: FIP, 08:42</p></div>{ic("chev")}</div></div>')
    b = (h("In rotation", "All artists")
         + '<div class="hs">' + who(1, "Alice Coltrane") + who(2, "The Blue Nile") + who(3, "Talk Talk") + who(4, "Slowdive") + who(5, "Portishead") + "</div>"
         + arrival + radio + h("Recently added", "Library")
         + '<div class="pad g2">' + cap(10, "Hats", "The Blue Nile") + cap(2, "Journey in Satchidananda", "Alice Coltrane") + cap(3, "Third", "Portishead") + cap(5, "Laughing Stock", "Talk Talk") + "</div>")
    insight = (f'<div class="pad"><div class="card col"><div class="row" style="align-items:flex-start">{cv(8, s="width:88px")}<div class="sp">'
               '<span class="tag y">Anniversary</span><h4 style="margin-top:6px">Closer turns 45 this week</h4><p class="mut sm">Joy Division · in your library, last played in March</p></div></div>'
               f'<div class="row">{btn("Play", "p sp", "play")}{btn("Why?")}</div></div></div>')
    c = (h("Recently played")
         + '<div class="hs">' + "".join(f'<div class="cap" style="width:112px">{cv(k, s="width:112px;margin-bottom:8px")}<b class="el">{n}</b><span class="el" style="display:block">{a_}</span></div>'
                                        for k, n, a_ in [(5, "Laughing Stock", "Talk Talk"), (12, "Spirit of Eden", "Talk Talk"), (7, "Promises", "Floating Points")]) + "</div>"
         + insight + h("Genres") + '<div class="pad wrapc"><span class="chip">Dream pop</span><span class="chip">Ambient</span><span class="chip">Post-rock</span></div>')
    e = (insight + h("Genres") + '<div class="pad wrapc"><span class="chip">Dream pop</span><span class="chip">Ambient</span><span class="chip">Post-rock</span><span class="chip">Spiritual jazz</span><span class="chip">Trip hop</span><span class="chip">Art rock</span></div>'
         + '<div class="pad"><div class="stat"><span>1,284 albums</span><span>12 new this month</span><span>Stats →</span></div></div>')
    d = (top("discair", True) + f'<div class="banner">{ic("info")}<p class="sm sp">ListenBrainz is not answering. Picks may be out of date.</p><a class="lk">Server</a></div>'
         + '<div class="h"><span class="eb">Today\'s picks</span><span class="eb">Loading</span></div>'
         + '<div class="stack"><i class="cv sk b2"></i><i class="cv sk b1"></i><i class="cv sk f"></i></div>'
         + '<div class="pad col" style="gap:8px"><i class="sk" style="width:120px;height:26px"></i><i class="sk" style="width:210px;height:16px"></i></div>'
         + f'<div class="pad row">{btn("Get album", "sp", "get")}{btn("Save")}{btn(ic("more", "f"), "sq")}</div>'
         + h("In rotation") + '<p class="pad mut">Play a few albums and the artists you return to appear here.</p>')
    return [("1 · Home, first screen", a, 0), ("2 · Home, scrolled: rotation, arrival, radio tile, recently added", b, 0),
            ("3 · Home, scrolled: recently played, insight", c, 0), ("4 · Home, end: insight, genres, stat strip", e, 0),
            ("5 · Home, picks loading, one service failing, no listening yet", d, 0)]

def fl_home():
    def carousel(seg, l, c, r, title, sub, acts):
        return (top("discair", True) + tabs(["Picks", "New", "Played"], seg) + f'<div class="flow">{cv(l, "s lf")}{cv(r, "s rt")}{cv(c, "c")}</div>'
                + f'<div class="pad ctr"><h2>{title}</h2><p class="mut">{sub}</p></div><div class="pad row ctr">{acts}</div>')
    pick = f'{btn("Get album", "p", "get")}{btn("Save", "t")}{btn(ic("more", "f"), "sq")}'
    artists = h("Artists", "All") + '<div class="hs">' + "".join(f'<div class="pc">{ar(a_)}<b>{n}</b></div>' for a_, n in [(1, "Alice Coltrane"), (2, "The Blue Nile"), (4, "Slowdive")]) + "</div>"
    a = carousel(0, 9, 1, 12, "Hex", "Bark Psychosis · 1994 · Post-rock", pick) + artists
    insight = (f'<div class="pad"><div class="card col"><div class="row" style="align-items:flex-start">{cv(8, s="width:88px;border-radius:10px")}<div class="sp">'
               '<span class="tag y">Anniversary</span><h4 style="margin-top:6px">Closer turns 45 this week</h4><p class="mut sm">Joy Division · in your library, last played in March</p></div></div>'
               f'<div class="row">{btn("Play", "p sp", "play")}{btn("Why?", "t")}</div></div></div>')
    grouped = ('<div class="list card">'
               + li(cv(4, s="width:32px"), "Pygmalion", "Downloading · 64%") + li(icon("radio"), "Radio", "Last heard: FIP, 08:42")
               + li(icon("lib"), "Library", "1,284 albums · 12 new this month") + "</div>")
    b = (artists + insight + h("Genres") + chips(["Dream pop", "Ambient", "Post-rock", "Spiritual jazz"], -1) + grouped)
    c = carousel(2, 12, 5, 7, "Laughing Stock", "Talk Talk · played an hour ago", f'{btn("Play", "p", "play")}{btn("Shuffle", "t")}{btn(ic("more", "f"), "sq")}') + artists
    d = (top("discair", True) + f'<div class="banner">{ic("info")}<p class="sm sp">ListenBrainz is not answering. Picks may be out of date.</p><a class="lk">Server</a></div>'
         + tabs(["Picks", "New", "Played"], 0)
         + '<div class="flow"><i class="cv sk s lf"></i><i class="cv sk s rt"></i><i class="cv sk c" style="box-shadow:none"></i></div>'
         + '<div class="pad col" style="gap:8px;align-items:center"><i class="sk" style="width:120px;height:26px"></i><i class="sk" style="width:210px;height:16px"></i></div>'
         + h("Artists") + '<p class="pad mut">Play a few albums and the artists you return to appear here.</p>')
    return [("1 · Home, first screen (Picks)", a, 0), ("2 · Home, scrolled: artists, insight, genres, grouped list", b, 0),
            ("3 · Home, Played selected", c, 0), ("4 · Home, picks loading, one service failing, no listening yet", d, 0)]

# ---------------------------------------------------------------------------------------------------- shared pages

def dc(k, title, artist, why):
    return (f'<div class="dc">{cv(k)}<h4 class="el">{title}</h4><p class="mut sm el">{artist}</p><p class="mut sm el">{why}</p>'
            f'<div class="acts">{btn("Get", "p", "get")}{btn("Save", "t")}{btn(ic("more", "f"), "sq")}</div></div>')

def discover(t):
    lists = (top("Discover") + tabs(["Lists", "Insights"]) + chips(["Recommendations", "New releases", "Personal"])
             + '<div class="cards">' + dc(1, "Hex", "Bark Psychosis · 1994", "Similar to: Talk Talk") + dc(9, "Ptah, the El Daoud", "Alice Coltrane · 1970", "Similar to: Pharoah Sanders")
             + dc(11, "Vespertine", "Björk · 2001", "Similar to: Portishead") + dc(6, "Loveless", "My Bloody Valentine · 1991", "Similar to: Slowdive")
             + dc(7, "Promises", "Floating Points · 2021", "Similar to: Alice Coltrane") + dc(8, "Closer", "Joy Division · 1980", "Similar to: The Cure") + "</div>")
    bars = ('<div class="bars">' + "".join(f'<div><span class="sm">{n}</span><i class="{"on" if i == 0 else ""}" style="width:{w}%"></i><span class="sm num mut">{w // 5}%</span></div>'
                                          for i, (n, w) in enumerate([("Ambient", 85), ("Dream pop", 70), ("Post-rock", 55), ("Post-punk", 40)])) + "</div>")
    ins = (top("Discover") + tabs(["Lists", "Insights"], 1)
           + f'<div class="pad"><div class="card col"><span class="eb">Your taste · last 90 days</span><h3>More ambient, less post-punk lately.</h3>{bars}'
           f'<div class="row"><p class="mut sm sp">1,240 listens against 48,912 overall</p><a class="lk">Details</a></div></div></div>'
           + f'<div class="pad"><div class="card col"><div class="row" style="align-items:flex-start">{cv(8, s="width:88px")}<div class="sp"><span class="tag y">Anniversary</span>'
           '<h4 style="margin-top:6px">Closer turns 45 this week</h4><p class="mut sm">Joy Division · in your library</p></div></div>'
           f'<div class="row">{btn("Play", "p sp", "play")}{btn("Why?", "t")}</div></div></div>'
           + f'<div class="pad"><div class="card col"><div class="row" style="align-items:flex-start">{cv(12, s="width:88px")}<div class="sp"><span class="tag">Never played</span>'
           '<h4 style="margin-top:6px">Spirit of Eden</h4><p class="mut sm">Talk Talk · added in June</p></div></div>'
           f'<div class="row">{btn("Play", "p sp", "play")}{btn("Not now", "t")}</div></div></div>')
    sheet = ('<div class="scrim"></div><div class="sheet"><h3>Your taste</h3>' + tabs(["30 days", "90 days", "All time"], 1).replace('class="tabs"', 'class="tabs" style="margin-inline:0"')
             + '<div class="row" style="gap:8px"><span class="chip on">Genres</span><span class="chip">Decades</span><span class="chip">Moods</span></div>' + bars
             + btn("Make a playlist from Ambient", "p", "play") + "</div>")
    return [("1 · Discover, lists", lists, 1), ("2 · Discover, Insights", ins, 1), ("3 · Taste sheet", ins, 1, "", sheet)]

def library(t):
    artists = (top("Library") + tabs(["Artists", "Albums"]) + f'<div class="pad row"><p class="mut sp">312 artists · by name</p>{btn("Sort", "sm t", "sort")}</div><div class="list">'
               + "".join(li(ar(a_, "rd"), n, s) for a_, n, s in [(1, "Alice Coltrane", "6 albums"), (6, "Bark Psychosis", "2 albums"), (2, "The Blue Nile", "4 albums"),
                                                               (5, "Portishead", "3 albums"), (4, "Slowdive", "5 albums"), (3, "Talk Talk", "5 albums"), (6, "This Mortal Coil", "3 albums")]) + "</div>")
    albums = (top("Library") + tabs(["Artists", "Albums"], 1) + f'<div class="pad row"><p class="mut sp">1,284 albums · newest first</p>{btn("Sort", "sm t", "sort")}</div><div class="pad g2">'
              + cap(10, "Hats", "The Blue Nile · 1989") + cap(2, "Journey in Satchidananda", "Alice Coltrane · 1971") + cap(3, "Third", "Portishead · 2008")
              + cap(5, "Laughing Stock", "Talk Talk · 1991") + cap(7, "Promises", "Floating Points · 2021") + cap(4, "Pygmalion", "Slowdive · 1995") + "</div>")
    search = (top("Search") + f'<div class="field">{ic("search")}<span class="sp">talk</span>{ic("close", "s")}</div>'
              + '<div class="h"><span class="eb">Artists</span></div><div class="list">' + li(ar(3, "rd"), "Talk Talk", "5 albums in your library") + "</div>"
              + '<div class="h"><span class="eb">Albums</span></div><div class="list">'
              + li(cv(5), "Laughing Stock", 'Talk Talk · 1991 · <span class="ok">In your library</span>')
              + li(cv(12), "Spirit of Eden", 'Talk Talk · 1988 · <span class="ok">In your library</span>')
              + li(cv(11), "The Colour of Spring", "Talk Talk · 1986 · Not in your library", btn("Get", "sm p")) + "</div>"
              + '<div class="h"><span class="eb">Songs</span></div><div class="list">'
              + li(cv(5), "After the Flood", "Talk Talk · Laughing Stock", ic("qadd")) + li(cv(12), "I Believe in You", "Talk Talk · Spirit of Eden", ic("qadd")) + "</div>")
    return [("1 · Library, artists", artists, 2), ("2 · Library, albums", albums, 2), ("3 · Search, results", search, 3)]

def trow(n, title, dur, on=False): return f'<div class="trow{" on" if on else ""}"><span class="mut num sm">{ic("wave", "s") if on else n}</span><span class="el">{title}</span><span class="mut num sm">{dur}</span></div>'

def pages_album(t):
    over = ' over' if t == "fl" else ""
    album = (bar("", f'<span class="ib">{ic("more", "f")}</span>')
             + f'<div class="hero"><div class="art">{cv(5)}</div><div><h2>Laughing Stock</h2><p><a class="lk">Talk Talk</a></p><p class="mut sm">1991 · Art rock · 6 songs · FLAC</p></div>'
             f'<div class="row">{btn("Play", "p", "play")}{btn("Shuffle", "t", "shuffle")}{btn(ic("dl"), "sq")}</div></div>'
             + '<div class="pad">' + trow(1, "Myrrhman", "5:33") + trow(2, "Ascension Day", "6:00") + trow(3, "After the Flood", "9:39", True) + trow(4, "Taphead", "7:30")
             + trow(5, "New Grass", "9:40") + trow(6, "Runeii", "4:58") + "</div>" + h("Similar albums")
             + '<div class="hs">' + "".join(cv(k, s="width:112px") for k in (12, 1, 10)) + "</div>")
    ah = (f'<div class="ahero">{ar(3, "rd" if t == "sb" else "")}<div class="{"ov" if t == "fl" else "sp"}"><div class="sp"><h2>Talk Talk</h2><p class="mut sm">5 albums in your library</p></div>'
          + (btn(ic("play", "f"), "p sq") if t == "fl" else "") + "</div></div>")
    artist = (f'<div class="bar{over}"><span class="ib">{ic("back")}</span><span class="sp"></span><span class="ib">{ic("more", "f")}</span></div>' + ah
              + (f'<div class="pad row">{btn("Play", "p sp", "play")}{btn("Shuffle", "", "shuffle")}</div>' if t == "sb" else "")
              + h("Top songs", "All top songs") + '<div class="list">' + li(cv(5), "After the Flood", "Laughing Stock", ic("more", "f"))
              + li(cv(12), "I Believe in You", "Spirit of Eden", ic("more", "f")) + li(cv(11), "Life's What You Make It", "The Colour of Spring", ic("more", "f")) + "</div>"
              + h("In your library") + '<div class="hs">' + "".join(cv(k, s="width:104px") for k in (5, 12, 11)) + "</div>"
              + h("Missing albums", "All missing albums") + '<div class="hs">' + "".join(
                  f'<div class="cap" style="width:104px">{cv(k, s="width:104px;margin-bottom:8px")}<b class="el">{n}</b>{btn("Get", "sm p")}</div>' for k, n in [(6, "It's My Life"), (9, "The Party's Over"), (8, "London 1986")]) + "</div>"
              + h("Similar artists") + '<div class="hs">' + who(2, "The Blue Nile") + who(6, "Bark Psychosis") + who(4, "Slowdive") + "</div>")
    genre = (bar("Ambient") + '<div class="pad"><span class="lt">Ambient</span><p class="mut">86 albums · 41 artists in your library</p></div>' + tabs(["Albums", "Artists"])
             + '<div class="pad g2">' + cap(7, "Promises", "Floating Points") + cap(4, "Pygmalion", "Slowdive") + cap(3, "Third", "Portishead") + cap(2, "Journey in Satchidananda", "Alice Coltrane")
             + cap(10, "Hats", "The Blue Nile") + cap(12, "Spirit of Eden", "Talk Talk") + "</div>")
    return [("1 · Album (owned)", album, "stack", "wash" if t == "fl" else ""), ("2 · Artist", artist, "stack", "ov" if t == "fl" else ""), ("3 · Genre", genre, "stack")]

def player(t):
    head = lambda title: f'<div class="bar"><span class="ib">{ic("down")}</span><span class="eb sp ctr" style="display:block">{title}</span><span class="ib">{ic("more", "f")}</span></div>'
    ctl = (f'<div class="pad ctl"><span class="cb flat">{ic("shuffle")}</span><span class="cb">{ic("prev", "f")}</span><span class="cb main">{ic("pause", "f")}</span>'
           f'<span class="cb">{ic("next", "f")}</span><span class="cb flat">{ic("repeat")}</span></div>')
    seek = '<div class="pad"><div class="seek"><i style="width:38%"></i><b style="left:38%"></b></div><div class="row num sm mut" style="justify-content:space-between;margin-top:10px"><span>3:41</span><span>9:39</span></div></div>'
    tools = (f'<div class="pad row" style="justify-content:space-around;margin-top:auto;padding-bottom:28px">'
             + "".join(f'<span class="col ctr sm mut" style="gap:2px;align-items:center">{ic(i)}{l}</span>' for i, l in [("queue", "Queue"), ("quote", "Lyrics"), ("path", "Sonic path"), ("tune", "Equalizer")]) + "</div>")
    np = (head("Now playing") + cv(5, "npc lgc") + '<div class="pad row"><div class="sp"><h2 class="el">After the Flood</h2><p class="mut el">Talk Talk · Laughing Stock</p></div>'
          + f'<span class="ib">{ic("heart")}</span></div>' + seek + ctl + tools)
    q = (head("Queue") + f'<div class="pad row">{cv(5, s="width:56px")}<div class="sp"><span class="eb">Playing</span><h4 class="el">After the Flood</h4><p class="mut sm">Talk Talk</p></div></div>'
         + '<div class="h"><span class="eb">Next up · 5 songs</span><a>Clear</a></div><div class="list">'
         + "".join(li(cv(k), n, a_, ic("close", "s")) for k, n, a_ in [(5, "Taphead", "Talk Talk"), (5, "New Grass", "Talk Talk"), (5, "Runeii", "Talk Talk"), (10, "The Downtown Lights", "The Blue Nile"), (1, "The Loom", "Bark Psychosis")])
         + f'</div><div class="pad">{btn("Add songs that sound like this", "", "wave")}</div>' + seek + ctl)
    ly = (head("Lyrics") + f'<div class="pad row">{cv(5, s="width:56px")}<div class="sp"><h4 class="el">After the Flood</h4><p class="mut sm">Talk Talk</p></div>'
          + f'<span class="row sm mut" style="gap:6px">Photos {sw(True)}</span></div>'
          + '<div class="pad lyr col" style="gap:14px"><p>Shake my head</p><p>Turn my face to the floor</p><div><p class="on">Dead to respect, to respect to be born</p></div><p>Lest we forget who lay</p><p>Slow as the tide</p><p>A wave upon the shore</p></div>'
          + '<div style="margin-top:auto"></div>' + seek + ctl + '<div style="height:20px"></div>')
    wash = "wash" if t == "fl" else ""
    return [("1 · Now Playing", np, None, "np " + wash), ("2 · Queue", q, None, "np " + wash), ("3 · Lyrics", ly, None, "np " + wash)]

def radio(t):
    st = [(1, "FIP", "Talk Talk · Life's What You Make It", True), (2, "NTS 1", "Live: Charlie Bones", False), (3, "KEXP", "Slowdive · Sugar for the Pill", False),
          (4, "BBC Radio 6 Music", "Live title not available", False), (5, "Radio Paradise", "Portishead · Roads", False), (2, "Worldwide FM", "Alice Coltrane · Blue Nile", False)]
    stations = (bar("Radio", '<a class="lk" style="padding-right:12px">Heard on radio</a>') + '<div class="pad"><span class="lt">Radio</span></div><div class="list">'
                + "".join(li(f'<i class="lg l{l}">{n[:3].upper()}</i>', n, s, ic("heart", "f" if on else ""), "on" if on else "") for l, n, s, on in st) + "</div>")
    now = (f'<div class="bar"><span class="ib">{ic("down")}</span><span class="eb sp ctr" style="display:block">Live radio</span><span class="ib">{ic("queue")}</span></div>'
           + '<i class="lg l1 npc lgc" style="aspect-ratio:1;height:auto;font-size:64px">FIP</i>'
           + '<div class="pad ctr"><span class="tag a">On air</span><h2 style="margin-top:8px">Life\'s What You Make It</h2><p class="mut">Talk Talk · heard on FIP</p></div>'
           + f'<div class="pad ctl" style="justify-content:center;gap:28px"><span class="cb">{ic("heart", "f")}</span><span class="cb main">{ic("pause", "f")}</span><span class="cb">{ic("queue")}</span></div>'
           + f'<div class="pad col">{btn("Get this song", "p", "get")}<p class="mut sm ctr">The Colour of Spring is not in your library.</p></div>')
    heard = (bar("Heard on radio") + '<div class="pad"><span class="lt">Heard on radio</span><p class="mut">Songs the stations played while you listened</p></div><div class="list">'
             + li(cv(11), "Life's What You Make It", "Talk Talk · FIP · 21:09", btn("Get", "sm p"))
             + li(cv(3), "Roads", 'Portishead · Radio Paradise · 20:41 · <span class="ok">In your library</span>', ic("check", "ok"))
             + li(cv(4), "Sugar for the Pill", "Slowdive · KEXP · 19:58 · Requested", ic("dl"))
             + li(cv(9), "Blue Nile", "Alice Coltrane · Worldwide FM · 18:30", btn("Get", "sm p"))
             + li('<i class="cv sk" style="width:48px"></i>', "Untitled", "Artist not named · NTS 1 · 17:12", "") + "</div>")
    return [("1 · Radio, stations", stations, "stack"), ("2 · Radio, now playing", now, None, "np"), ("3 · Heard on radio", heard, "stack")]

def line_chart():
    pts = [(0, 96), (30, 90), (60, 86), (90, 78), (120, 74), (150, 64), (180, 58), (210, 46), (240, 40), (270, 30), (300, 22), (328, 14)]
    p = " ".join(f"{x},{y}" for x, y in pts)
    return (f'<svg class="chart" viewBox="0 0 328 124"><path d="M0 14h328M0 55h328M0 96h328" stroke="var(--chart-grid)" stroke-width="1" fill="none"/>'
            f'<polygon points="0,110 {p} 328,110" fill="var(--chart1)" opacity=".18"/><path d="M0 110h328" stroke="var(--chart-base)" stroke-width="1.5"/>'
            f'<polyline points="{p}" fill="none" stroke="var(--text)" stroke-width="2"/><circle cx="240" cy="40" r="5" fill="var(--chart1)" stroke="var(--text)" stroke-width="1.5"/></svg>')

def col_chart():
    vals = [(18, 8), (34, 20), (62, 58), (88, 70), (74, 40), (52, 30), (40, 34)]
    out = ['<svg class="chart" viewBox="0 0 328 124"><path d="M0 110h328" stroke="var(--chart-base)" stroke-width="1.5"/>']
    for i, (a, b) in enumerate(vals):
        x = 8 + i * 46
        out.append(f'<rect x="{x}" y="{110 - a}" width="16" height="{a}" rx="3" fill="var(--chart3)" stroke="var(--chart-base)" stroke-width="1"/>'
                   f'<rect x="{x + 18}" y="{110 - b}" width="16" height="{b}" rx="3" fill="var(--chart1)" stroke="var(--chart-base)" stroke-width="1"/>')
    return "".join(out) + "</svg>"

def downloads(t):
    def job(k, title, sub, stage, state, acts, bad=False):
        return (f'<div class="card col"><div class="row" style="align-items:flex-start">{cv(k, s="width:64px")}<div class="sp"><h4 class="el">{title}</h4><p class="mut sm el">{sub}</p><p class="sm">{state}</p></div></div>'
                f'<div>{trk(stage, bad)}</div><div class="row">{acts}</div></div>')
    dl = (bar("Downloads") + '<div class="pad"><span class="lt">Downloads</span><p class="mut">2 in progress · 1 needs you</p></div><div class="pad col">'
          + job(4, "Pygmalion", "Slowdive · 1995", 1, "Downloading · 64% · 7 of 9 songs", btn("Skip this source", "sm") + btn("Dismiss", "sm d"))
          + job(11, "The Colour of Spring", "Talk Talk · 1986", 2, '<span class="dan">Import failed: two songs are missing</span>', btn("Try again", "sm p") + btn("Dismiss", "sm d"), True)
          + job(10, "Hats", "The Blue Nile · 1989", 3, '<span class="ok">In your library · arrived today</span>', btn("Play", "sm p", "play") + btn("Open album", "sm t")) + "</div>")
    stats = (bar("Library stats") + '<div class="pad"><span class="lt">Library stats</span></div>' + chips(["12 months", "5 years", "All time"])
             + f'<div class="pad"><div class="card col"><div class="row"><div class="sp"><span class="eb">Collection over time</span><p><span class="numeral">1,241</span> <span class="mut">albums · September</span></p></div></div>{line_chart()}'
             '<div class="row num sm mut" style="justify-content:space-between"><span>Dec</span><span>Jun</span><span>Nov</span></div></div></div>'
             + f'<div class="pad"><div class="card col"><span class="eb">Own and play by decade</span>{col_chart()}'
             '<div class="row num sm mut" style="justify-content:space-around"><span>60s</span><span>70s</span><span>80s</span><span>90s</span><span>00s</span><span>10s</span><span>20s</span></div>'
             '<p class="sm mut">Pale: albums you own. Filled: albums you played this year.</p></div></div>'
             + f'<div class="pad"><div class="card col"><span class="eb">Shelf life</span><p><span class="numeral">96</span> <span class="mut">albums never played</span></p>{btn("Play something unplayed", "p", "play")}</div></div>')
    def svc(name, state, c): return li(icon("server"), name, f'<span class="{c}">{state}</span>', "")
    server = (bar("Server") + '<div class="pad"><span class="lt">Server</span></div>'
              + f'<div class="pad"><div class="card row">{ic("info", "cau")}<div class="sp"><h4>One service needs attention</h4><p class="mut sm">Checked a minute ago</p></div>{btn("Check now", "sm t")}</div></div>'
              + '<div class="h"><span class="eb">Services</span></div><div class="list card">' + svc("Librarian", "Working", "ok") + svc("Navidrome", "Working", "ok") + svc("slskd", "Working", "ok")
              + svc("ListenBrainz", "Not answering since 20:50", "cau") + svc("MusicBrainz", "Working", "ok") + "</div>"
              + '<div class="h"><span class="eb">Server activity</span></div><div class="list card">' + li(icon("wave"), "Lens refresh", "Finished 18:02 · next at 06:00", "")
              + li(icon("lib"), "Library resync", "Finished 03:10", "") + "</div>")
    return [("1 · Downloads", dl, "stack"), ("2 · Library stats", stats, "stack"), ("3 · Server", server, "stack")]

def settings(t):
    s = (bar("Settings") + '<div class="pad"><span class="lt">Settings</span></div><div class="list card">'
         + li(icon("server"), "Server and services", '<span class="cau">One service needs attention</span>') + "</div>"
         + '<div class="h"><span class="eb">Look and sound</span></div><div class="list card">'
         + li(icon("sun"), "Appearance", THEMES[t][1]) + li(icon("tune"), "Equalizer", "On · Custom") + li(icon("swap"), "Crossfade", "6 seconds · albums stay gapless") + "</div>"
         + '<div class="h"><span class="eb">Listening</span></div><div class="list card">'
         + li(icon("radio"), "Radio", "Scrobble radio songs") + li(icon("wave"), "ListenBrainz", "Connected") + li(icon("lib"), "Resync the library nightly", "", sw(True)) + "</div>"
         + f'<div class="pad">{btn("Sign out", "d", "out")}</div>')
    def swatch(name, bg, fg, on=False): return f'<div class="{"on" if on else ""}"><i style="background:linear-gradient(135deg,{bg} 60%,{fg} 60%)"></i>{name}</div>'
    ap = (bar("Appearance") + '<div class="pad"><span class="lt">Appearance</span></div>' + tabs(["Follow the phone", "One theme"], 1)
          + '<p class="pad mut sm">One fixed theme, whatever the phone\'s setting is.</p>' + h("Theme") + chips(["All", "Light", "Dark", "Brutal"])
          + '<div class="pad swt">' + swatch("Sand", "#EFE6D3", "#AD4016") + swatch("Soft Brut", "#FBF7EE", "#C4B5FD", t == "sb") + swatch("Flow", "#FBFAF7", "#C2410C", t == "fl")
          + swatch("Tape · Lime", "#F1EEE3", "#C6F432") + swatch("Night", "#141211", "#F5D33F") + swatch("Sheet · Violet", "#15131F", "#FF6A3D") + "</div>"
          + h("Font") + '<div class="list card">' + li("", "Brut · Modern" if t == "sb" else "Flow", "Space Grotesk and Inter" if t == "sb" else "Inter", ic("check"))
          + li("", "Discair", "Peace Sans and Open Sans", "") + li("", "Editorial", "Fraunces and Inter", "") + "</div>")
    bands = [40, 55, 62, 50, 44, 50, 58, 66, 60, 48]
    eq = (bar("Equalizer") + '<div class="pad"><span class="lt">Equalizer</span></div>'
          + f'<div class="list card">{li("", "Equalizer", "On. The curve below shapes everything you play here.", sw(True))}</div>'
          + h("Preset") + chips(["Custom", "Flat", "Bass lift", "Vocal", "Night"]) + h("Bands")
          + '<div class="pad"><div class="eq">' + "".join(f'<i style="--v:{b}%"></i>' for b in bands) + '</div><div class="row num sm mut" style="justify-content:space-between;margin-top:8px"><span>31</span><span>125</span><span>500</span><span>2k</span><span>8k</span><span>16k</span></div></div>'
          + '<div class="list card">' + li("", "Headroom", "Automatic · −3.0 dB", "") + li("", "Volume change", "None", "") + f'</div><div class="pad">{btn("Reset to flat")}</div>')
    cf = (bar("Crossfade") + '<div class="pad"><span class="lt">Crossfade</span></div>' + f'<div class="list card">{li("", "Crossfade", "Songs blend into each other", sw(True))}</div>'
          + h("Length") + f'<div class="pad row ctr" style="gap:20px">{btn(ic("minus"), "sq")}<span class="numeral">6 s</span>{btn(ic("plus"), "sq")}</div>'
          + '<div class="pad"><div class="prog"><i style="width:50%"></i></div><div class="row num sm mut" style="justify-content:space-between;margin-top:6px"><span>1 s</span><span>12 s</span></div></div>'
          + h("Fade") + chips(["Smooth", "Even", "Quick"]) + h("Albums") + f'<div class="list card">{li("", "Keep albums gapless", "No fade between songs of the same album", sw(True))}</div>')
    return [("1 · Settings", s, "stack"), ("2 · Appearance", ap, "stack"), ("3 · Equalizer", eq, "stack"), ("4 · Crossfade", cf, "stack")]

def sheets(t, home_first):
    menu = ('<div class="scrim"></div><div class="sheet"><div><h3>Hex</h3><p class="mut">Bark Psychosis · 1994</p></div><div class="list" style="padding:0">'
            + li(icon("info"), "Why this pick?", "", "") + li(icon("close"), "Not this album", "", "") + li(icon("close"), "Never suggest this artist", "", "") + "</div></div>")
    confirm = ('<div class="scrim"></div><div class="sheet"><h3>Dismiss this download?</h3><p class="mut">The Colour of Spring leaves the list. Files already downloaded are removed; nothing in your library changes.</p>'
               + btn("Keep it") + btn("Dismiss the download", "d") + "</div>")
    snack = '<div class="snack"><span class="sp">Hex will not be suggested again.</span><a class="lk">Undo</a></div>'
    dl = downloads(t)[0][1]
    return [("1 · Pick menu (the three-dot button)", home_first, 0, "", menu), ("2 · Confirmation sheet (Dismiss)", dl, "stack", "", confirm),
            ("3 · Snackbar with Undo, above the mini player", home_first, 0, "", snack.replace('class="snack"', 'class="snack" style="bottom:142px"'))]

def components(t):
    """A flat board of the theme's tokens and controls, drawn by the same CSS the pages use."""
    css = open(os.path.join(OUT, THEMES[t][0] + ".css")).read()
    block = css[css.index("{", css.index("." + t + "{")) + 1:]
    block = block[:block.index("}")]
    toks = [x.strip().split(":", 1) for x in block.replace("\n", " ").split(";") if x.strip().startswith("--") or " --" in x]
    cols = []
    for part in block.split(";"):
        part = part.split("*/")[-1].strip()
        if part.startswith("--") and ":" in part:
            k, v = part.split(":", 1)
            if v.strip().startswith("#"):
                cols.append((k.strip(), v.strip()))
    sw_ = "".join(f'<div><i style="background:{v};border:1px solid rgba(0,0,0,.15)"></i><b>{k[2:]}</b><span class="mut">{v}</span></div>' for k, v in cols)
    type_ = ('<div class="col"><span class="lt">Large title</span><h2>Title, album and artist names</h2><h3>Section heading</h3><h4>Row title, 600</h4><p>Body 14/20. The quick brown fox.</p>'
             '<p class="mut sm">Small 12/18, muted</p><span class="eb">Eyebrow label</span><span class="numeral">1,284</span></div>')
    ctr = (f'<div class="col"><div class="row">{btn("Get album", "p", "get")}{btn("Save", "t")}{btn(ic("more", "f"), "sq")}{btn("Small", "sm")}{btn("Dismiss", "sm d")}</div>'
           '<div class="row"><span class="chip on">Chip on</span><span class="chip">Chip</span><span class="tag">Tag</span><span class="tag y">Tag</span><span class="tag a">Tag</span>'
           f'{sw(True)}{sw(False)}</div>' + tabs(["Artists", "Albums", "Songs"]).replace('class="tabs"', 'class="tabs" style="margin:0;width:300px"')
           + f'<div class="field" style="margin:0;width:300px">{ic("search")}<span class="mut">Search your library</span></div>'
           '<div style="width:300px"><div class="prog"><i style="width:64%"></i></div></div><div style="width:300px">' + trk(1) + "</div>"
           '<div style="width:300px"><div class="seek"><i style="width:38%"></i><b style="left:38%"></b></div></div>'
           f'<div class="row"><span class="cb">{ic("prev", "f")}</span><span class="cb main">{ic("pause", "f")}</span><span class="cb">{ic("next", "f")}</span></div></div>')
    dock = f'<div class="col" style="width:336px">{MINI}{nav(0)}<div class="card row">{cv(4, s="width:52px")}<div class="sp"><h4>Card</h4><p class="mut sm">Surface, radius and depth</p></div></div></div>'
    return (f'<div class="phone {t}" style="width:auto;height:auto;border:0;border-radius:16px;padding:24px;display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:28px;overflow:visible">'
            f'<div class="swt" style="grid-template-columns:repeat(4,1fr);align-content:start">{sw_}</div>{type_}{ctr}{dock}</div>')

PAGES = ["home", "discover", "library-search", "album-artist-genre", "player", "radio", "downloads-stats-server", "settings", "sheets", "components"]
TITLES = {"home": "Home", "discover": "Discover, Insights and the taste sheet", "library-search": "Library and Search", "album-artist-genre": "Album, Artist and Genre",
          "player": "Now Playing, Queue and Lyrics", "radio": "Radio, live radio and Heard on radio", "downloads-stats-server": "Downloads, Library stats and Server",
          "settings": "Settings, Appearance, Equalizer and Crossfade", "sheets": "Sheets and the snackbar", "components": "Tokens and controls"}

def page(t, name):
    home = sb_home() if t == "sb" else fl_home()
    if name == "components":
        return components(t)
    frames = {"home": lambda: home, "discover": lambda: discover(t), "library-search": lambda: library(t), "album-artist-genre": lambda: pages_album(t),
              "player": lambda: player(t), "radio": lambda: radio(t), "downloads-stats-server": lambda: downloads(t), "settings": lambda: settings(t),
              "sheets": lambda: sheets(t, home[0][1])}[name]()
    return '<div class="frames">' + "".join(frame(t, f[0], f[1], f[2], f[3] if len(f) > 3 else "", f[4] if len(f) > 4 else "") for f in frames) + "</div>"

def write(t, name):
    folder, label = THEMES[t]
    html = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{label} · {TITLES[name]}</title>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&family=Space+Grotesk:wght@700&display=swap">'
            f'<link rel="stylesheet" href="../shared.css"><link rel="stylesheet" href="../{folder}.css"></head><body>{SPRITE}'
            f'<div class="doc"><h1>{label} · {TITLES[name]}</h1><p>Android, 360 × 780 dp, 1 px = 1 dp. Covers, artist photos and station logos are drawn stand-ins. '
            f'Spec: docs/ANDROID_ART_THEMES_PROPOSAL.md.</p></div>{page(t, name)}</body></html>')
    path = os.path.join(OUT, folder, name + ".html")
    open(path, "w").write(html)
    if os.path.exists(CHROME):
        n = html.count("<figure>")
        w = 56 + max(n, 1) * 406 if n else 1500
        hgt = 1010 if n else 760
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{hgt}", "--virtual-time-budget=5000",
                        f"--screenshot={path[:-5]}.png", "file://" + path], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

if __name__ == "__main__":
    args = sys.argv[1:]
    themes = [a for a in args if a in THEMES] or list(THEMES)
    names = [a for a in args if a in PAGES] or PAGES
    for t in themes:
        for n in names:
            write(t, n)
            print(THEMES[t][0] + "/" + n)
