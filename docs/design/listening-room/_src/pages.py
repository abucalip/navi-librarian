#!/usr/bin/env python3
"""Writes the Listening Room page mockups beyond Home into ../pages/<name>.html.

Every page is built from the same parts below (shell, reason panel, ranked row, card, track row...),
so the menu, the reason panel and the tools are identical everywhere. The written HTML is the spec;
this file only keeps the pages consistent. build.py imports it, then inlines the icon sprite and
renders the PNGs. Spec: docs/LISTENING_ROOM_WEB.md section 8.

    python3 pages.py            # write every page

Design tooling only: nothing imports it except build.py, and no test collects it. Home, reasons and
states are hand-written pages and are not touched here.
"""
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.normpath(os.path.join(HERE, "..", "pages"))


def e(text):
    """HTML-escaped text."""
    return html.escape(str(text), quote=True)


def icon(name, small=False):
    """One sprite icon."""
    return f'<svg class="lr-icon{"-sm" if small else ""}" aria-hidden="true"><use href="#lr-{name}"/></svg>'


# --- Shell ------------------------------------------------------------------------------------

RAIL = [("home", "Home"), ("discover", "Discover"), ("library", "Library"), ("saved", "Saved"), ("radio", "Radio"),
        ("acquisitions", "Acquisitions"), None, ("block", "Blocklist"), ("settings", "Settings")]
TABS = [("home", "Home"), ("discover", "Discover"), ("library", "Library"), ("acquisitions", "Getting"), ("menu", "More")]
MORE = {"saved", "radio", "block", "settings"}

GETTING = '''    <section class="lr-getting" aria-label="Getting now">
      <p class="lr-eyebrow">Getting now</p>
      <div class="lr-getting-row">
        <div class="lr-cover art-khru" style="width: 40px;"></div>
        <div style="min-width: 0;">
          <p class="lr-card-title" style="font-size: 13px;">Con Todo El Mundo</p>
          <div class="lr-progress" role="progressbar" aria-label="Con Todo El Mundo download" aria-valuenow="62" aria-valuemin="0" aria-valuemax="100"><span style="width: 62%;"></span></div>
        </div>
      </div>
      <p class="lr-meta">1 downloading · 1 importing</p>
    </section>
'''


def rail(current, getting):
    """The side menu (desktop) / icon rail (tablet). `current` is an icon key from RAIL."""
    out = ['  <nav class="lr-rail" aria-label="Main">',
           '    <a class="lr-brand" href="#"><svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true"><circle cx="14" cy="14" r="13" fill="#F5B544"/>'
           '<circle cx="14" cy="14" r="4" fill="#0C0D10"/></svg><span class="lr-brand-word">discair</span></a>']
    for item in RAIL:
        if item is None:
            out.append('    <span class="lr-rail-sep" aria-hidden="true"></span>')
            continue
        key, label = item
        cur = ' aria-current="page"' if key == current else ""
        if key == "acquisitions":
            out.append(f'    <a class="lr-nav lr-badge-host" href="#"{cur} aria-label="Acquisitions, 2 active">{icon(key)}'
                       f'<span class="lr-nav-label">{label}</span><span class="lr-badge lr-badge-rail" aria-hidden="true">2</span></a>')
        else:
            out.append(f'    <a class="lr-nav" href="#"{cur} aria-label="{label}">{icon(key)}<span class="lr-nav-label">{label}</span></a>')
    if getting:
        out.append(GETTING.rstrip("\n"))
    out.append("  </nav>")
    return "\n".join(out)


def tabbar(current):
    """Phone bottom tab bar. Pages reached from More mark More as current."""
    cur_key = "menu" if current in MORE else current
    out = ['  <nav class="lr-tabbar" aria-label="Main">']
    for key, label in TABS:
        cur = ' aria-current="page"' if key == cur_key else ""
        if key == "acquisitions":
            out.append(f'    <a href="#" class="lr-badge-host"{cur} aria-label="Getting, 2 active">{icon(key)}{label}<span class="lr-badge" aria-hidden="true">2</span></a>')
        else:
            out.append(f'    <a href="#"{cur}>{icon(key)}{label}</a>')
    out.append("  </nav>")
    return "\n".join(out)


def topbar(mode=False, query=""):
    """Search, and the Discovery mode switch on discovery pages only."""
    value = f' value="{e(query)}"' if query else ""
    out = ['      <header class="lr-topbar">',
           f'        <label class="lr-search">{icon("search")}<span class="lr-sr">Search your library or discover new music</span>'
           f'<input type="search" placeholder="Artists, albums, genres"{value}><span class="lr-kbd" aria-hidden="true">/</span></label>']
    if mode:
        out += ['        <div class="lr-mode">',
                '          <span class="lr-mode-label" id="mode-label">Discovery mode</span>',
                '          <div class="lr-segment" role="group" aria-labelledby="mode-label">',
                '            <button type="button" aria-pressed="false">Safer</button>',
                '            <button type="button" aria-pressed="true">Balanced</button>',
                '            <button type="button" aria-pressed="false">Deeper</button>',
                '          </div>', '        </div>']
    out.append("      </header>")
    return "\n".join(out)


def page(name, title, current, body, mode=False, getting=True, query="", extra_css=""):
    """A whole page in the shell."""
    style = f"\n<style>\n{extra_css}\n</style>" if extra_css else ""
    doc = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Listening Room · {e(title)}</title>
<link rel="stylesheet" href="../tokens.css">
<link rel="stylesheet" href="../components.css">
<link rel="stylesheet" href="../art.css">{style}
</head>
<body>
<!--sprite-->
<!--/sprite-->
<a class="lr-skip" href="#content">Skip to content</a>
<div class="lr-shell">

{rail(current, getting)}

  <main class="lr-main" id="content">
    <div class="lr-column">

{topbar(mode, query)}

{body}
    </div>
  </main>

{tabbar(current)}
</div>
</body>
</html>
'''
    write(name, doc)


def write(name, doc):
    """Write ../pages/<name>.html, keeping an already inlined sprite out of the diff noise."""
    with open(os.path.join(PAGES, f"{name}.html"), "w", encoding="utf-8") as handle:
        handle.write(doc)


# --- Parts ------------------------------------------------------------------------------------

def chip(label, key=None, ico=None, avatar=None, link=True, title=None):
    """One evidence chip. Links when it leads somewhere (tag -> genre page, artist -> artist page)."""
    inner = ""
    if avatar:
        inner += f'<span class="lr-chip-avatar {avatar}" aria-hidden="true"></span>'
    if ico:
        inner += icon(ico, small=True)
    if key:
        inner += f'<span class="lr-chip-k">{e(key)}</span>'
    inner += e(label)
    extra = f' title="{e(title)}" aria-label="{e(title)}"' if title else ""
    tag = "a" if link else "span"
    href = ' href="#"' if link else ""
    return f'<li><{tag} class="lr-chip"{href}{extra}>{inner}</{tag}></li>'


def reason(kind, sentence, chips=(), size="card", label="Why this pick"):
    """The reason panel: label with the kind's icon, the sentence, the evidence chips."""
    cls = "lr-reason-hero" if size == "hero" else "lr-reason-text"
    ev = f'<ul class="lr-evidence" aria-label="{e(label)}">{"".join(chips)}</ul>' if chips else ""
    return (f'<div class="lr-reason"><p class="lr-reason-label">{icon(kind, small=True)}{e(label)}</p>'
            f'<p class="lr-reason-head"><span class="{cls}">{e(sentence)}</span></p>{ev}</div>')


def tools(title, get=True, save=True, more=True, extra=""):
    """Card and row tools: Get, Save and the "..." menu, icon-only with labels."""
    out = []
    if get:
        out.append(f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet lr-card-get" aria-label="Get {e(title)}">{icon("get")}</button>')
    if save:
        out.append(f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="Save {e(title)}">{icon("saved")}</button>')
    out.append(extra)
    if more:
        out.append(f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="More actions for {e(title)}">{icon("more")}</button>')
    return f'<div class="lr-rank-tools">{"".join(out)}</div>'


def rank(n, art, title, artist, year, why=None, meta=None, row_tools=None, mark=""):
    """A ranked row. n=None draws the row without a rank number."""
    cls = "lr-rank" if n is not None else "lr-rank lr-rank-norank"
    num = f'<span class="lr-rank-n">{n}</span>' if n is not None else ""
    metas = "".join(f'<p class="lr-meta">{e(m)}</p>' for m in (meta or []))
    return (f'          <li class="{cls}">{num}<div class="lr-cover {art}">{mark}</div>'
            f'<div class="lr-rank-main"><p class="lr-card-title"><a href="#">{e(title)}</a></p>'
            f'<p class="lr-meta"><a href="#" style="color: inherit;">{e(artist)}</a>{" · " + e(year) if year else ""}</p>{metas}</div>'
            f'{why or ""}{row_tools if row_tools is not None else tools(title)}</li>')


def ranked(rows, label):
    """An ordered list of ranked rows."""
    return f'        <ol class="lr-ranked" aria-label="{e(label)}">\n' + "\n".join(rows) + "\n        </ol>"


def card(art, title, meta, line=None, evidence=None, card_tools=True, mark="", get=True):
    """Grid album card (5.8): cover, title, meta, reason strip, one evidence value, tools."""
    out = f'<article class="lr-card"><div class="lr-cover {art}">{mark}</div><p class="lr-card-title"><a href="#">{e(title)}</a></p><p class="lr-meta">{e(meta)}</p>'
    if line:
        out += f'<p class="lr-reason-line">{e(line)}</p>'
    if evidence:
        out += f'<p class="lr-meta">{e(evidence)}</p>'
    if card_tools:
        get_btn = (f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet lr-card-get" aria-label="Get {e(title)}">{icon("get")}</button>' if get else "")
        out += (f'<div class="lr-card-tools">{get_btn}'
                f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="More actions for {e(title)}">{icon("more")}</button></div>')
    return out + "</article>"


OWNED = f'<span class="lr-owned-mark" title="In your library">{icon("check")}<span class="lr-sr">In your library</span></span>'


def person(photo, name, meta, initials=None):
    """An artist link with a 64 photo (or initials when no photo loads)."""
    face = (f'<span class="lr-person-photo lr-initials" aria-hidden="true">{e(initials)}</span>' if initials
            else f'<span class="lr-person-photo {photo}" aria-hidden="true"></span>')
    return f'<li><a class="lr-person" href="#">{face}<span><span class="lr-card-title">{e(name)}</span><span class="lr-meta" style="display: block;">{e(meta)}</span></span></a></li>'


def section(ident, title, sub=None, body="", right=""):
    """A section with its head (5.4)."""
    sub_html = f'<p class="lr-section-sub">{e(sub)}</p>' if sub else ""
    return (f'      <section class="lr-section" aria-labelledby="{ident}">\n'
            f'        <div class="lr-section-head"><div><h2 class="lr-section-title" id="{ident}">{e(title)}</h2>{sub_html}</div>{right}</div>\n'
            f'{body}\n      </section>\n')


def pagehead(title, sub=None, right="", eyebrow=None, back=None):
    """Page title block (5.14)."""
    out = ""
    if back:
        out += f'      <a class="lr-btn lr-btn-quiet lr-back" href="#">{icon("back")}{e(back)}</a>\n'
    eb = f'<p class="lr-eyebrow">{e(eyebrow)}</p>' if eyebrow else ""
    sub_html = f'<p class="lr-page-sub">{e(sub)}</p>' if sub else ""
    out += f'      <div class="lr-pagehead"><div>{eb}<h1 class="lr-page-title">{e(title)}</h1>{sub_html}</div>{right}</div>\n'
    return out


def track(n, title, time, owned, album_title=None):
    """A track row: number, title, duration, then the owned check or the song's own Get."""
    state = (f'<span class="lr-track-owned" title="In your library">{icon("check")}<span class="lr-sr">In your library</span></span>' if owned
             else f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="Get {e(title)}">{icon("get")}</button>')
    return (f'<li class="lr-track"><span class="lr-track-n">{n}</span><span class="lr-track-title">{e(title)}</span>'
            f'<span class="lr-track-time">{e(time)}</span>{state}</li>')


LISTS = [("discover", "Discover music", 10), ("layers", "Daily picks", 20), ("people", "Personal Discoveries", 12),
         ("disc", "Artist Deep Dives", 8), ("library", "Add to your collection", 15), ("calendar", "New releases", 9)]


def listswitch(selected):
    """The Discover list switch: one tablist across the six lists."""
    out = ['      <div class="lr-listswitch" role="tablist" aria-label="Discovery list">']
    for ico, label, _count in LISTS:
        sel = "true" if label == selected else "false"
        out.append(f'        <button type="button" class="lr-tab" role="tab" aria-selected="{sel}">{icon(ico, small=True)}{e(label)}'
                   "</button>")
    out.append("      </div>")
    return "\n".join(out)


def refresh_button(label="Refresh"):
    """The quiet refresh action that every list keeps."""
    return f'<button type="button" class="lr-btn">{icon("refresh")}{e(label)}</button>'


# --- Pages: Discover --------------------------------------------------------------------------

LISTENERS = lambda n, full: chip(n + " listeners", ico="listeners", link=False, title=f"{full} Last.fm listeners")  # noqa: E731


def discover_music():
    """Discover music: generate, refine, ranked rows with R11/R4 reasons, diagnostics."""
    rows = [
        rank(1, "art-stereo", "Dots and Loops", "Stereolab", "1997",
             reason("discover", "Close to genres you already love", [chip("Broadcast", key="Similar to", avatar="photo-b"), LISTENERS("52k", "52,114")])),
        rank(2, "art-tina", "Amassakoul", "Tinariwen", "2004",
             reason("compass-spread", "A bridge between rock and African music, both in your listening", [chip("rock"), chip("african")])),
        rank(3, "art-floating", "Promises", "Floating Points", "2021",
             reason("spark", "A step away from your usual genres", [chip("electronic"), LISTENERS("47k", "47,302")])),
        rank(4, "art-broadcast", "Tender Buttons", "Broadcast", "2005",
             reason("people", "Shares genres with Stereolab, Grouper and 2 more", [chip("Stereolab", avatar="photo-b"), chip("Grouper", avatar="photo-d"), chip("+2", link=False)])),
        rank(5, "art-can", "Ege Bamyasi", "Can", "1972",
             reason("info", "Few genre tags, so the fit is a guess", [LISTENERS("118k", "118,560")])),
        rank(6, "art-yussef", "Black Classical Music", "Yussef Dayes", "2023",
             reason("discover", "Close to genres you already love", [chip("Nala Sinephro", key="Similar to", avatar="photo-c"), LISTENERS("22k", "22,048")])),
    ]
    body = (pagehead("Discover", "Every discovery list in one place. Each album says why it is here.")
            + listswitch("Discover music") + "\n"
            + section("list", "Discover music", "Generate a set of album suggestions, then narrow it by category, reorder it or search it.",
                      f'''        <div class="lr-row" style="align-items: end; gap: var(--lr-space-16);">
          <label class="lr-field"><span class="lr-field-label">Albums</span><select class="lr-select"><option>5</option><option selected>10</option><option>15</option><option>20</option></select></label>
          <button type="button" class="lr-btn lr-btn-primary">{icon("refresh")}Generate recommendations</button>
        </div>
        <div class="lr-toolbar" role="group" aria-labelledby="refine">
          <p class="lr-field-label" id="refine" style="flex-basis: 100%;">Refine results</p>
          <label class="lr-field" style="flex: 2 1 280px;"><span class="lr-sr">Search recommendations</span><span class="lr-input-wrap lr-input-icon">{icon("search")}<input class="lr-input" type="search" placeholder="Search artist, album, or genre"></span></label>
          <label class="lr-field" style="flex: 1 1 200px;"><span class="lr-sr">Filter by discovery category</span><select class="lr-select"><option>All categories</option><option>Adjacent</option><option>Cross-genre</option><option>Adventurous discovery</option><option>Unclassified</option></select></label>
          <label class="lr-field" style="flex: 1 1 200px;"><span class="lr-sr">Sort recommendations</span><select class="lr-select"><option>Recommended order</option><option>Most popular artists</option><option>Highest discovery score</option><option>Artist A–Z</option></select></label>
        </div>
        <p class="lr-status-line" role="status">10 albums · recommended order</p>
{ranked(rows, "Discover music")}
        <details class="lr-details"><summary>{icon("chev-down")}Recommendation diagnostics</summary><div class="lr-details-body"><pre class="lr-mono">candidates 412 · after filters 96 · returned 10 · mode balanced</pre></div></details>'''))
    page("discover", "Discover", "discover", body, mode=True)


def discover_daily():
    """Daily picks: lens tabs, ranked rows with R5/R1/R6 reasons."""
    lens_tabs = "".join(
        f'<button type="button" class="lr-tab" role="tab" aria-selected="{"true" if i == 0 else "false"}">{icon(ico, small=True)}{label}</button>'
        for i, (ico, label) in enumerate([("layers", "Deep cuts"), ("spark", "Current tastes"), ("compass-spread", "Genre spread"),
                                          ("repeat", "Repeated tracks"), ("flame", "Obsessions")]))
    rows = [
        rank(1, "art-alice", "Journey in Satchidananda", "Alice Coltrane", "1971",
             reason("layers", "A lesser-known record from the spiritual jazz you play", [chip("spiritual jazz", key="Seed tag", ico="tag"), LISTENERS("41k", "41,220"), chip("free jazz", key="Tag"), chip("harp", key="Tag")])),
        rank(2, "art-broadcast", "Tender Buttons", "Broadcast", "2005",
             reason("layers", "A lesser-known record from the dream pop you play", [chip("dream pop", key="Seed tag", ico="tag"), LISTENERS("38k", "38,410")])),
        rank(3, "art-russ2", "Another Thought", "Arthur Russell", "1994",
             reason("disc", "Discover more Arthur Russell", [])),
        rank(4, "art-grouper", "Ruins", "Grouper", "2014",
             reason("layers", "A lesser-known record from the ambient you play", [chip("ambient", key="Seed tag", ico="tag"), LISTENERS("29k", "29,876")])),
        rank(5, "art-cleo", "Mother", "Cleo Sol", "2021",
             reason("layers", "From your Deep cuts lens", [LISTENERS("9.6k", "9,612")])),
    ]
    body = (pagehead("Discover", "Every discovery list in one place. Each album says why it is here.")
            + listswitch("Daily picks") + "\n"
            + section("list", "Daily picks", "One list per lens, built each morning and fixed for the day. An album appears in at most one of them.",
                      f'''        <div class="lr-tabs" role="tablist" aria-label="Lens">{lens_tabs}</div>
        <p class="lr-status-line" role="status">20 albums in Deep cuts</p>
{ranked(rows, "Deep cuts")}'''))
    page("discover-daily", "Discover · Daily picks", "discover", body, mode=True)


def discover_dives():
    """Artist Deep Dives: one panel per artist, R7 (missing album) and R8 (similar artist)."""
    def dive(photo, name, kind, sentence, chips, albums):
        tiles = "".join(card(a, t, y, card_tools=True) for a, t, y in albums)
        return f'''      <section class="lr-panel" aria-labelledby="dive-{photo}">
        <div class="lr-row" style="gap: var(--lr-space-16); flex-wrap: nowrap;"><span class="lr-person-photo {photo}" aria-hidden="true"></span><div style="min-width: 0;"><p class="lr-eyebrow">Artist</p><h2 class="lr-section-title" id="dive-{photo}"><a href="#" style="color: inherit; text-decoration: none;">{e(name)}</a></h2></div></div>
        {reason(kind, sentence, chips, label="Why this artist")}
        <div class="lr-dive-albums">{tiles}</div>
      </section>'''
    body = (pagehead("Discover", "Every discovery list in one place. Each album says why it is here.")
            + listswitch("Artist Deep Dives") + "\n"
            + f'''      <div class="lr-section-head"><div><h2 class="lr-section-title">Artist Deep Dives</h2><p class="lr-section-sub">Missing albums by artists in your library, and artists close to them.</p></div>{refresh_button()}</div>
''' + dive("photo-dive", "Arthur Russell", "library", "You have 3 albums by Arthur Russell. These are the ones not in your library yet.",
                [chip("3 in your library", ico="disc", link=False), chip("avant-garde", key="Tag"), chip("disco", key="Tag")],
                [("art-russ2", "Another Thought", "1994"), ("art-russ3", "Calling Out of Context", "2004"), ("art-russ4", "Love Is Overtaking Me", "2008"), ("art-russ5", "Iowa Dream", "2019")]) + "\n"
            + dive("photo-b", "Broadcast", "people", "Close to Stereolab, who is well covered in your library. Nothing by this artist yet.",
                   [chip("Stereolab", key="Close to", avatar="photo-b")],
                   [("art-broadcast", "Tender Buttons", "2005"), ("art-grouper2", "Haha Sound", "2003"), ("art-nala2", "The Noise Made by People", "2000"), ("art-talk", "Work and Non Work", "1997")]) + "\n")
    page("discover-dives", "Discover · Artist Deep Dives", "discover", body, mode=True)


def discover_simple(name, selected, sub, rows, extra_head=""):
    """Personal Discoveries, Add to your collection, New releases: ranked rows with Refresh."""
    body = (pagehead("Discover", "Every discovery list in one place. Each album says why it is here.")
            + listswitch(selected) + "\n"
            + section("list", selected, sub, f'        <p class="lr-status-line" role="status">{extra_head}</p>\n' + ranked(rows, selected),
                      right=refresh_button()))
    page(name, "Discover · " + selected, "discover", body, mode=True)


def discover_others():
    discover_simple("discover-personal", "Personal Discoveries", "Recommendations based on your listening and musical interests.", [
        rank(1, "art-nala", "Space 1.8", "Nala Sinephro", "2021",
             reason("tag", "Because you listen to spiritual jazz and ambient", [chip("spiritual jazz"), chip("ambient")])),
        rank(2, "art-broadcast", "Tender Buttons", "Broadcast", "2005",
             reason("people", "Shares genres with Stereolab and Grouper", [chip("Stereolab", avatar="photo-b"), chip("Grouper", avatar="photo-d")])),
        rank(3, "art-khru", "Con Todo El Mundo", "Khruangbin", "2018",
             reason("people", "Shares genres with Mdou Moctar, Tinariwen and 1 more", [chip("Mdou Moctar", avatar="photo-c"), chip("Tinariwen", avatar="photo-a"), chip("+1", link=False)])),
        rank(4, "art-yussef", "Black Classical Music", "Yussef Dayes", "2023",
             reason("tag", "Because you listen to jazz", [chip("jazz")])),
    ], "12 albums · refreshed in the background")
    discover_simple("discover-collection", "Add to your collection", "Acclaimed albums by artists you already keep.", [
        rank(1, "art-talk", "Spirit of Eden", "Talk Talk", "1988",
             reason("library", "A well-known album; you have 2 albums by this artist", [LISTENERS("402k", "402,118")])),
        rank(2, "art-can", "Ege Bamyasi", "Can", "1972",
             reason("library", "A well-known album; you have 4 albums by this artist", [LISTENERS("318k", "318,004")])),
        rank(3, "art-fela", "Zombie", "Fela Kuti", "1976",
             reason("library", "A well-known album; you have 1 album by this artist", [LISTENERS("211k", "211,470")])),
        rank(4, "art-russ3", "World of Echo", "Arthur Russell", "1986",
             reason("disc", "Discover more Arthur Russell", [])),
    ], "15 albums")
    discover_simple("discover-new", "New releases", "Full albums from the last 24 months by artists with a full album in your library.", [
        rank(1, "art-nala2", "Endlessness", "Nala Sinephro", "2026",
             reason("calendar", "New in 2026 from an artist with a full album in your library", [chip("1 album in your library", ico="disc", link=False)])),
        rank(2, "art-mdou2", "Funeral for Justice", "Mdou Moctar", "2026",
             reason("calendar", "New in 2026 from an artist with a full album in your library", [chip("2 albums in your library", ico="disc", link=False)])),
        rank(3, "art-grouper2", "Shine a Light", "Grouper", "2025",
             reason("calendar", "New in 2025 from an artist with a full album in your library", [chip("5 albums in your library", ico="disc", link=False)])),
    ], "9 albums")


# --- Pages: Library, artist, album, genre ------------------------------------------------------

SHELF_ART = [("art-talk", "Spirit of Eden", "Talk Talk"), ("art-alice", "Ptah, the El Daoud", "Alice Coltrane"), ("art-can", "Tago Mago", "Can"),
             ("art-fela", "Expensive Shit", "Fela Kuti"), ("art-grouper", "Dragging a Dead Deer", "Grouper"), ("art-russ3", "World of Echo", "Arthur Russell")]


def shelf(ident, title, sub, items):
    cards = "".join(card(a, t, m, card_tools=False) for a, t, m in items)
    return section(ident, title, sub, f'        <div class="lr-grid">{cards}</div>')


def library_toolbar(tab, display):
    a_sel, b_sel = ("true", "false") if tab == "artists" else ("false", "true")
    l_sel, g_sel = ("true", "false") if display == "list" else ("false", "true")
    sorts = ("<option>Name</option><option>Album count</option><option>Date added</option>" if tab == "artists"
             else "<option>Album name</option><option>Artist</option><option>Album year</option><option selected>Date added</option><option>Track count</option>")
    size = ('<label class="lr-field"><span class="lr-field-label">Thumbnail size</span><input class="lr-range" type="range" min="110" max="320" step="10" value="180" aria-valuetext="180 pixels"></label>'
            if display == "grid" else "")
    return f'''        <div class="lr-toolbar">
          <label class="lr-field" style="flex: 2 1 280px;"><span class="lr-field-label">Search your library</span><span class="lr-input-wrap lr-input-icon">{icon("search")}<input class="lr-input" type="search" placeholder="Search your library"></span></label>
          <div class="lr-field"><span class="lr-field-label" id="show">Show</span><div class="lr-segment" role="group" aria-labelledby="show"><button type="button" aria-pressed="{a_sel}">Artists</button><button type="button" aria-pressed="{b_sel}">Albums</button></div></div>
          <div class="lr-field"><span class="lr-field-label">Sort by</span><div class="lr-row" style="flex-wrap: nowrap;"><select class="lr-select" aria-label="Sort by">{sorts}</select><button type="button" class="lr-btn lr-btn-icon" aria-label="Sort direction: newest first">{icon("sort")}</button></div></div>
          <div class="lr-field"><span class="lr-field-label" id="display">Display</span><div class="lr-iconseg" role="group" aria-labelledby="display"><button type="button" aria-pressed="{l_sel}" aria-label="List">{icon("list")}</button><button type="button" aria-pressed="{g_sel}" aria-label="Grid">{icon("grid")}</button></div></div>
          {size}
        </div>'''


def library_artists():
    rows = [("photo-a", "Alice Coltrane", "4 albums · added 3 Nov 2026"), ("photo-dive", "Arthur Russell", "3 albums · added 28 Oct 2026"),
            ("photo-b", "Broadcast", "2 albums · added 12 Oct 2026"), ("photo-c", "Can", "4 albums · added 1 Sep 2026"),
            ("photo-d", "Cleo Sol", "1 album · added 30 Aug 2026"), (None, "Fela Kuti", "1 album · added 2 Aug 2026"),
            ("photo-a", "Grouper", "5 albums · added 14 Jul 2026"), ("photo-c", "Khruangbin", "2 albums · added 1 Jul 2026")]
    items = "".join(
        f'<li><a class="lr-librow" href="#">'
        + (f'<span class="lr-person-photo {p}" aria-hidden="true"></span>' if p else f'<span class="lr-person-photo lr-initials" aria-hidden="true" style="font-size: 14px;">FK</span>')
        + f'<span><span class="lr-card-title">{e(n)}</span><span class="lr-meta" style="display: block;">{e(m)}</span></span>{icon("next")}</a></li>'
        for p, n, m in rows)
    body = (pagehead("Library", "Your Navidrome library by artist or album. Select one to see its page.")
            + shelf("recent", "Recently played", "What you played last, newest first.", SHELF_ART)
            + shelf("most", "Most played", "Your most played albums.", SHELF_ART[3:] + SHELF_ART[:3])
            + shelf("added", "Newly added", "The last albums imported into your library.", SHELF_ART[1:] + SHELF_ART[:1])
            + section("browse", "Browse", None, library_toolbar("artists", "list")
                      + '\n        <p class="lr-status-line" role="status">412 artists · by name, A to Z</p>\n'
                      + f'        <ul class="lr-liblist">{items}</ul>\n'
                      + f'        <button type="button" class="lr-btn" style="align-self: center;">Load more</button>'))
    page("library", "Library", "library", body)


def library_albums():
    albums = [("art-talk", "Spirit of Eden", "Talk Talk · 1988"), ("art-alice", "Ptah, the El Daoud", "Alice Coltrane · 1970"),
              ("art-can", "Tago Mago", "Can · 1971"), ("art-fela", "Expensive Shit", "Fela Kuti · 1975"),
              ("art-grouper", "Dragging a Dead Deer", "Grouper · 2008"), ("art-russ3", "World of Echo", "Arthur Russell · 1986"),
              ("art-cleo", "Rose in the Dark", "Cleo Sol · 2020"), ("art-khru", "Mordechai", "Khruangbin · 2020"),
              ("art-mdou", "Ilana", "Mdou Moctar · 2019"), ("art-nala", "Space 1.8", "Nala Sinephro · 2021"),
              ("art-stereo", "Emperor Tomato Ketchup", "Stereolab · 1996"), ("art-sault", "Nine", "Sault · 2021")]
    tiles = "".join(card(a, t, m, card_tools=False) for a, t, m in albums)
    body = (pagehead("Library", "Your Navidrome library by artist or album. Select one to see its page.")
            + section("browse", "Browse", None, library_toolbar("albums", "grid")
                      + '\n        <p class="lr-status-line" role="status">1,284 albums · by date added, newest first</p>\n'
                      + f'        <div class="lr-tiles" style="--tile: 180px;">{tiles}</div>\n'
                      + '        <button type="button" class="lr-btn" style="align-self: center;">Load more</button>'))
    page("library-albums", "Library · Albums", "library", body)


def artist_page():
    top = "".join(
        f'<a href="#"><div class="lr-cover {a}"></div><div style="min-width: 0;"><p class="lr-card-title">{n}. {e(t)}</p><p class="lr-meta" style="color: var(--lr-hero-text-soft);">{e(al)}</p></div></a>'
        for n, a, t, al in [(1, "art-alice", "Journey in Satchidananda", "Journey in Satchidananda"), (2, "art-russ4", "Turiya and Ramakrishna", "Ptah, the El Daoud"),
                            (3, "art-khru", "Blue Nile", "Ptah, the El Daoud"), (4, "art-nala2", "Galaxy in Turiya", "Universal Consciousness"),
                            (5, "art-floating", "Om Supreme", "World Galaxy")])
    owned = "".join(card(a, t, y, card_tools=False, mark=OWNED) for a, t, y in [
        ("art-alice", "Journey in Satchidananda", "1971"), ("art-russ4", "Ptah, the El Daoud", "1970"),
        ("art-nala2", "Universal Consciousness", "1971"), ("art-floating", "World Galaxy", "1972")])
    missing = [
        rank(None, "art-khru", "Turiya Sings", "Alice Coltrane", "1982",
             reason("library", "You have 4 albums by Alice Coltrane. This one is not in your library yet.", [LISTENERS("18k", "18,204")])),
        rank(None, "art-grouper2", "Transfiguration", "Alice Coltrane", "1978",
             reason("library", "You have 4 albums by Alice Coltrane. This one is not in your library yet.", [LISTENERS("9.1k", "9,140")])),
    ]
    similar = "".join([person("photo-c", "Pharoah Sanders", "2 albums in your library"), person("photo-b", "Sun Ra", "Not in your library"),
                       person("photo-d", "Dorothy Ashby", "Not in your library"), person(None, "Don Cherry", "1 album in your library", initials="DC")])
    body = (f'      <a class="lr-btn lr-btn-quiet lr-back" href="#">{icon("back")}Back to Library</a>\n'
            + f'''      <section class="lr-hero lr-hero-artistpage" aria-labelledby="artist-name" style="--lr-hero-tint: #2B1C2F;">
        <div class="lr-artist-photo photo-a" role="img" aria-label="Alice Coltrane"></div>
        <div class="lr-hero-body">
          <p class="lr-eyebrow">Artist</p>
          <h1 class="lr-hero-title" id="artist-name">Alice Coltrane</h1>
          <ul class="lr-tagrow" aria-label="Genres">{chip("spiritual jazz")}{chip("free jazz")}{chip("harp")}{chip("devotional")}</ul>
          <p class="lr-hero-meta">4 albums in your library · 2 missing</p>
          <p class="lr-bio">Alice Coltrane was an American jazz pianist, organist, harpist and composer. Her records from the late 1960s and 1970s joined modal jazz, Indian devotional music and the harp into a style later called spiritual jazz.</p>
          <div class="lr-actions"><button type="button" class="lr-btn" aria-expanded="false">Read more</button><button type="button" class="lr-btn">{icon("lean-more")}More like this</button><button type="button" class="lr-btn lr-btn-icon" aria-label="More actions for Alice Coltrane">{icon("more")}</button></div>
        </div>
        <aside class="lr-upnext" aria-label="Top songs">
          <p class="lr-eyebrow">Top songs</p>
          {top}
          <button type="button" class="lr-btn" style="margin-top: var(--lr-space-8);">All top songs</button>
        </aside>
      </section>
'''
            + section("owned", "In your library", None, f'        <div class="lr-grid">{owned}</div>')
            + section("missing", "Missing albums", "Albums by this artist that are not in your library, most listened first.", ranked(missing, "Missing albums")
                      + '\n        <button type="button" class="lr-btn" style="align-self: start;">All missing albums</button>')
            + section("similar", "Similar artists", None, f'        <ul class="lr-people">{similar}</ul>'))
    page("artist", "Artist", "library", body)


def album_page(name, owned):
    """Album page, not owned (Info tab) or owned (Reviews tab)."""
    tracks_data = [("Journey in Satchidananda", "6:39"), ("Shiva-Loka", "6:33"), ("Stopover Bombay", "2:52"), ("Something About John Coltrane", "10:41"), ("Isis and Osiris", "11:44")]
    have = [True] * 5 if owned else [True, False, False, True, False]
    tracks = "".join(track(i + 1, t, d, have[i]) for i, (t, d) in enumerate(tracks_data))
    summary = "5 songs, 38 minutes" + ("" if owned else " · 2 in your library")
    if owned:
        actions = f'<span class="lr-btn lr-btn-done">{icon("check")}In your library</span><button type="button" class="lr-btn">{icon("lean-more")}More like this</button>'
        status = '<span class="lr-pill">FLAC</span>'
        why = ""
    else:
        actions = (f'<button type="button" class="lr-btn lr-btn-primary">{icon("get")}Get this album</button><button type="button" class="lr-btn">{icon("saved")}Save</button>'
                   f'<button type="button" class="lr-btn">{icon("lean-more")}More like this</button>')
        status = '<span class="lr-pill">Not in your library</span>'
        why = reason("layers", "A lesser-known record from the spiritual jazz you play", [chip("spiritual jazz", key="Seed tag", ico="tag"), LISTENERS("41k", "41,220"), chip("free jazz", key="Tag")], size="hero",
                     label="Why this pick · Daily picks, Deep cuts")
    info_sel, rev_sel = ("false", "true") if owned else ("true", "false")
    if owned:
        about = f'''<ul class="lr-list">
            <li class="lr-review"><p class="lr-review-head">{icon("quote")}Pitchfork<span class="lr-score" aria-label="Score 9.1 out of 10">9.1</span></p><p class="lr-review-text">“A record that sounds like a prayer and a jam session at once, with Coltrane’s harp leading Pharoah Sanders and a tanpura drone.”</p><a href="#" class="lr-source">Read on Pitchfork</a></li>
            <li class="lr-review"><p class="lr-review-head">{icon("quote")}AllMusic<span class="lr-score" aria-label="4.5 out of 5 stars">4.5/5</span></p><p class="lr-review-text">“The title piece is among the most beautiful things in her catalogue.”</p><a href="#" class="lr-source">Read on AllMusic</a></li>
          </ul>'''
    else:
        about = '''<p style="color: var(--lr-text-soft);">Recorded in November 1970 with Pharoah Sanders, Cecil McBee and Rashied Ali, the album joins modal jazz to the drone of the tanpura and the oud. It was Coltrane’s first record after travelling to India.</p>
          <button type="button" class="lr-btn" aria-expanded="false" style="align-self: start;">Read more</button>
          <p class="lr-source">Description from <a href="#">Apple Music</a></p>'''
    platforms = "".join(f'<a class="lr-btn" href="#">{icon("external")}{p}</a>' for p in ["Apple Music", "Spotify", "Deezer", "Qobuz", "Bandcamp"])
    similar = "".join([card("art-nala", "Space 1.8", "Nala Sinephro · 2021"), card("art-floating", "Promises", "Floating Points · 2021"),
                       card("art-yussef", "Karma", "Pharoah Sanders · 1969", mark=OWNED, get=False), card("art-grouper2", "Afro-Harping", "Dorothy Ashby · 1968"),
                       card("art-russ4", "Lanquidity", "Sun Ra · 1978"), card("art-cleo", "Mother", "Cleo Sol · 2021")])
    people = "".join([person("photo-c", "Pharoah Sanders", "2 albums in your library"), person("photo-b", "Sun Ra", "Not in your library"),
                      person("photo-d", "Dorothy Ashby", "Not in your library")])
    body = (f'      <a class="lr-btn lr-btn-quiet lr-back" href="#">{icon("back")}Back</a>\n'
            + f'''      <section class="lr-hero lr-hero-page" aria-labelledby="album-title" style="--lr-hero-tint: #311E48;">
        <div class="lr-hero-cover art-alice"><span class="art-mark" style="color: #F2C14E;">ALICE COLTRANE</span></div>
        <div class="lr-hero-body">
          <p class="lr-eyebrow">Album</p>
          <h1 class="lr-hero-title" id="album-title">Journey in Satchidananda</h1>
          <p class="lr-hero-artist"><span class="lr-chip-avatar photo-a" style="width: 44px; height: 44px; margin: 0;" aria-hidden="true"></span><a href="#">Alice Coltrane</a></p>
          <p class="lr-hero-meta"><a href="#">Spiritual jazz</a><span>· 1971</span>{status}</p>
          {why}
          <div class="lr-actions">{actions}<button type="button" class="lr-btn lr-btn-icon" aria-label="More actions for Journey in Satchidananda">{icon("more")}</button></div>
        </div>
      </section>
      <div class="lr-album-body">
        <section class="lr-section" aria-labelledby="tracks">
          <h2 class="lr-section-title" id="tracks">Tracklist</h2>
          <ol class="lr-tracks">{tracks}</ol>
          <p class="lr-meta">{summary}</p>
          <div class="lr-stack" style="gap: var(--lr-space-8);"><p class="lr-field-label" id="services">Open this album on music services</p><div class="lr-platforms" role="group" aria-labelledby="services">{platforms}</div></div>
        </section>
        <section class="lr-section lr-panel" aria-label="About this album">
          <div class="lr-tabs" role="tablist" aria-label="About this album"><button type="button" class="lr-tab" role="tab" aria-selected="{info_sel}">{icon("info", True)}Info</button><button type="button" class="lr-tab" role="tab" aria-selected="{rev_sel}">{icon("quote", True)}Reviews</button></div>
          {about}
        </section>
      </div>
'''
            + section("simalbums", "Similar albums", None, f'        <div class="lr-grid">{similar}</div>' + '\n        <button type="button" class="lr-btn" style="align-self: start;">All albums</button>')
            + section("simartists", "Similar artists", None, f'        <ul class="lr-people">{people}</ul>'))
    page(name, "Album" + (" · in your library" if owned else ""), "discover" if not owned else "library", body)


def album_modal():
    """The album modal (quick view from any card), over a dimmed page."""
    platforms = "".join(f'<a class="lr-btn" href="#">{icon("external")}{p}</a>' for p in ["Apple Music", "Spotify", "Deezer", "Qobuz", "Bandcamp"])
    doc = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Listening Room · Album modal</title>
<link rel="stylesheet" href="../tokens.css">
<link rel="stylesheet" href="../components.css">
<link rel="stylesheet" href="../art.css">
<style>
  .backdrop {{ min-height: 100vh; display: grid; place-items: center; padding: var(--lr-space-32); background: var(--lr-bg); position: relative; }}
  .backdrop .lr-scrim {{ position: absolute; }}
  .backdrop .lr-dialog {{ z-index: 21; }}
  .ghost {{ position: absolute; inset: 0; display: grid; grid-template-columns: repeat(6, 1fr); gap: 24px; padding: 32px 32px 32px 280px; opacity: 0.6; }}
  @media (max-width: 719px) {{ .backdrop {{ padding: 64px 0 0; align-items: end; }} .ghost {{ padding: 16px; grid-template-columns: repeat(2, 1fr); }} }}
</style>
</head>
<body>
<!--sprite-->
<!--/sprite-->
<div class="backdrop">
  <div class="ghost" aria-hidden="true"><div class="lr-cover art-mdou"></div><div class="lr-cover art-cleo"></div><div class="lr-cover art-yussef"></div><div class="lr-cover art-sault"></div><div class="lr-cover art-floating"></div><div class="lr-cover art-tina"></div></div>
  <div class="lr-scrim"></div>
  <section class="lr-dialog" role="dialog" aria-modal="true" aria-labelledby="modal-title" style="--lr-hero-tint: #2E1A12;">
    <button type="button" class="lr-btn lr-btn-icon lr-dialog-close lr-hero-close" aria-label="Close album details" style="background: var(--lr-hero-button-fill); border-color: var(--lr-hero-button-edge); color: var(--lr-hero-text);">{icon("close")}</button>
    <div class="lr-stack">
      <div class="lr-hero-cover art-mdou"></div>
      <div class="lr-platforms" role="group" aria-label="Find this album on music services" style="--x: 0;">{platforms}</div>
    </div>
    <div class="lr-stack lr-hero" style="display: flex; padding: 0; background: none; gap: var(--lr-space-16);">
      <p class="lr-eyebrow">Album · Daily picks</p>
      <h2 class="lr-hero-title" id="modal-title" style="font-size: 40px;">Afrique Victime</h2>
      <p class="lr-hero-artist"><span class="lr-chip-avatar photo-c" style="width: 44px; height: 44px; margin: 0;" aria-hidden="true"></span><a href="#">Mdou Moctar</a><span>· 2021</span></p>
      {reason("layers", "A lesser-known record from the desert blues you play", [chip("desert blues", key="Seed tag", ico="tag"), LISTENERS("18k", "18,330"), chip("tuareg", key="Tag")], size="hero")}
      <p class="lr-bio">Mdou Moctar’s fifth album, recorded on tour, with the band’s guitar-led Tuareg rock at its loudest.</p>
      <div class="lr-actions"><button type="button" class="lr-btn lr-btn-primary">{icon("get")}Get this album</button><button type="button" class="lr-btn">{icon("saved")}Save</button><button type="button" class="lr-btn">{icon("lean-more")}More like this</button><button type="button" class="lr-btn lr-btn-icon" aria-label="More actions for Afrique Victime">{icon("more")}</button></div>
      <a href="#">Open the album page</a>
    </div>
  </section>
</div>
</body>
</html>
'''
    write("album-modal", doc)


def genre_page():
    people = "".join([person("photo-a", "Alice Coltrane", "4 albums in your library"), person("photo-c", "Pharoah Sanders", "2 albums in your library"),
                      person("photo-b", "Nala Sinephro", "1 album in your library"), person("photo-d", "Dorothy Ashby", "Not in your library"),
                      person(None, "Don Cherry", "1 album in your library", initials="DC"), person("photo-dive", "Sun Ra", "Not in your library")])
    albums = [("art-alice", "Journey in Satchidananda", "Alice Coltrane · 1971", True), ("art-nala", "Space 1.8", "Nala Sinephro · 2021", True),
              ("art-yussef", "Karma", "Pharoah Sanders · 1969", True), ("art-floating", "Promises", "Floating Points · 2021", False),
              ("art-grouper2", "Afro-Harping", "Dorothy Ashby · 1968", False), ("art-russ4", "Lanquidity", "Sun Ra · 1978", False)]
    tiles = "".join(card(a, t, m, card_tools=True, mark=OWNED if o else "", get=not o) for a, t, m, o in albums)
    body = (f'      <a class="lr-btn lr-btn-quiet lr-back" href="#">{icon("back")}Back</a>\n'
            + pagehead("Spiritual jazz", "Artists and albums with this genre. Those in your library are marked.", eyebrow="Genre",
                       right=f'<button type="button" class="lr-btn">{icon("block")}Block this genre</button>')
            + section("gartists", "Artists", None, f'        <ul class="lr-people">{people}</ul>')
            + section("galbums", "Albums", None, f'        <div class="lr-grid">{tiles}</div>'))
    page("genre", "Genre", "library", body)


# --- Pages: Search, Saved, Blocklist --------------------------------------------------------------

def search_page():
    def res(face, title, meta, kind, tool=""):
        # The title is the link; a row's Get is a sibling button, never inside the link.
        return (f'<li class="lr-sres" role="option">{face}<span style="min-width: 0;"><a class="lr-card-title" href="#" style="color: var(--lr-text); text-decoration: none;">{title}</a>'
                f'<span class="lr-meta" style="display: block;">{e(meta)}</span></span><span class="lr-row">{tool}<span class="lr-pill">{e(kind)}</span></span></li>')
    get = lambda t: f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="Get {e(t)}">{icon("get")}</button>'  # noqa: E731
    mark = lambda s: s.replace("Alice", "<mark>Alice</mark>")  # noqa: E731
    panel = f'''      <div class="lr-searchpanel" role="region" aria-label="Search results">
        <p class="lr-status-line" role="status" style="padding: 8px 16px 0;">9 results for “alice”</p>
        <div class="lr-sgroup"><p class="lr-eyebrow lr-sgroup-head">Artists in your library</p><ul class="lr-list" role="listbox" aria-label="Artists">
          {res('<span class="lr-person-photo photo-a" aria-hidden="true"></span>', mark("Alice Coltrane"), "4 albums", "Artist")}
          {res('<span class="lr-person-photo photo-d" aria-hidden="true"></span>', mark("Alice Phoebe Lou"), "1 album", "Artist")}
        </ul></div>
        <div class="lr-sgroup"><p class="lr-eyebrow lr-sgroup-head">Albums in your library</p><ul class="lr-list" role="listbox" aria-label="Albums">
          {res('<span class="lr-cover art-alice"></span>', "Journey in Satchidananda", "Alice Coltrane · 1971", "Album")}
          {res('<span class="lr-cover art-russ4"></span>', "Ptah, the El Daoud", "Alice Coltrane · 1970", "Album")}
        </ul></div>
        <div class="lr-sgroup"><p class="lr-eyebrow lr-sgroup-head">Songs in your library</p><ul class="lr-list" role="listbox" aria-label="Songs">
          {res('<span class="lr-logo" style="width: 40px; height: 40px; border-radius: 4px;">' + icon("note") + '</span>', "Blue Nile", "Alice Coltrane · Ptah, the El Daoud", "Song")}
        </ul></div>
        <div class="lr-sgroup"><p class="lr-eyebrow lr-sgroup-head">Not in your library</p><ul class="lr-list" role="listbox" aria-label="Not in your library">
          {res('<span class="lr-cover art-khru"></span>', "Turiya Sings", "Alice Coltrane · 1982", "Album", get("Turiya Sings"))}
          {res('<span class="lr-cover art-grouper2"></span>', "Transfiguration", "Alice Coltrane · 1978", "Album", get("Transfiguration"))}
          {res('<span class="lr-person-photo photo-b" aria-hidden="true"></span>', mark("Alice Damon"), "MusicBrainz artist", "Artist")}
        </ul></div>
      </div>'''
    recent = "".join(
        f'<li><div class="lr-sres" style="grid-template-columns: 40px minmax(0,1fr) auto;"><span class="lr-logo" style="width: 40px; height: 40px;">{icon("clock")}</span>'
        f'<a href="#" class="lr-card-title" style="color: var(--lr-text); text-decoration: none;">{e(q)}</a>'
        f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="Remove {e(q)} from recent searches">{icon("close")}</button></div></li>'
        for q in ["pharoah sanders", "desert blues", "Tender Buttons"])
    body = (panel + "\n"
            + section("recent", "Before you type", "Focusing the empty field shows recent searches. “/” focuses the field from anywhere.",
                      f'''        <div class="lr-searchpanel" role="region" aria-label="Recent searches">
          <p class="lr-eyebrow lr-sgroup-head">Recent searches</p>
          <ul class="lr-list">{recent}</ul>
        </div>'''))
    page("search", "Search", "home", body, query="alice")


def saved_page():
    items = [("art-mdou", "Afrique Victime", "Mdou Moctar · saved 16 Nov 2026"), ("art-cleo", "Mother", "Cleo Sol · saved 14 Nov 2026"),
             ("art-stereo", "Dots and Loops", "Stereolab · saved 11 Nov 2026"), ("art-talk", "Spirit of Eden", "Talk Talk · saved 9 Nov 2026"),
             ("art-fela", "Zombie", "Fela Kuti · saved 2 Nov 2026"), ("art-tina", "Amassakoul", "Tinariwen · saved 30 Oct 2026")]
    cards = "".join(
        f'<article class="lr-card"><div class="lr-cover {a}"></div><p class="lr-card-title"><a href="#">{e(t)}</a></p><p class="lr-meta">{e(m)}</p>'
        f'<div class="lr-card-tools"><button type="button" class="lr-btn lr-btn-icon lr-btn-quiet lr-card-get" aria-label="Get {e(t)}">{icon("get")}</button>'
        f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="Remove {e(t)} from Saved">{icon("trash")}</button>'
        f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="More actions for {e(t)}">{icon("more")}</button></div></article>'
        for a, t, m in items)
    body = (pagehead("Saved", "Albums you bookmarked with Save, newest first. Saving never starts a download.", right=refresh_button())
            + '      <p class="lr-status-line" role="status">6 saved albums</p>\n'
            + f'      <div class="lr-grid">{cards}</div>\n'
            + f'''      <div class="lr-note">{icon("info")}<div><p class="lr-note-title">Nothing saved yet</p><p class="lr-note-text">The empty state: “Save” on any album puts it here. It never starts a download.</p></div></div>
''')
    page("saved", "Saved", "saved", body)


def blocklist_page():
    def row(face, name, meta, button):
        return (f'<li class="lr-blockrow">{face}<span><span class="lr-card-title">{e(name)}</span><span class="lr-meta" style="display: block;">{e(meta)}</span></span>'
                f'<button type="button" class="lr-btn">{e(button)}</button></li>')
    tagface = f'<span class="lr-logo">{icon("tag")}</span>'
    body = (pagehead("Blocklist", "What you told discair to leave out of picks. Unblocking restores them on the next refresh.")
            + section("bgenres", "Blocked genres", "Albums with these genres never appear in picks.",
                      f'        <ul class="lr-liblist">{row(tagface, "christian rock", "Blocked from a Daily picks album", "Unblock")}{row(tagface, "nu metal", "Blocked from a genre page", "Unblock")}</ul>')
            + section("bartists", "Artists hidden with Not this artist", None,
                      f'        <ul class="lr-liblist">{row('<span class="lr-person-photo photo-b" aria-hidden="true"></span>', "Coldplay", "Hidden 4 Nov 2026", "Unblock")}</ul>')
            + section("bleans", "More and Less like this", "Artists you nudged. Removing one returns its picks to normal.",
                      f'''        <ul class="lr-liblist">
          <li class="lr-blockrow"><span class="lr-person-photo photo-a" aria-hidden="true"></span><span><span class="lr-card-title">Alice Coltrane</span><span class="lr-pill" style="margin-top: 4px;">{icon("lean-more", True)}More like this</span></span><button type="button" class="lr-btn">Remove</button></li>
          <li class="lr-blockrow"><span class="lr-person-photo photo-c" aria-hidden="true"></span><span><span class="lr-card-title">Khruangbin</span><span class="lr-pill" style="margin-top: 4px;">{icon("lean-less", True)}Less like this</span></span><button type="button" class="lr-btn">Remove</button></li>
        </ul>'''))
    page("blocklist", "Blocklist", "block", body)


# --- Pages: Acquisitions, Radio ------------------------------------------------------------------

def acquisitions_page():
    def state(tone, ico, label):
        return f'<p class="lr-state lr-state-{tone}">{icon(ico)}{e(label)}</p>'

    def acq(art, title, artist, profile, st, extra_state="", actions="", details=None, big=False, song_of=None):
        det = (f'<details class="lr-details" style="margin-top: var(--lr-space-8);"><summary>{icon("chev-down")}Details</summary><div class="lr-details-body">'
               + "".join(f'<p class="lr-mono">{e(d)}</p>' for d in details) + '</div></details>') if details else ""
        song = f'<p class="lr-meta">Song on <a href="#">{e(song_of)}</a></p>' if song_of else ""
        return (f'<li class="lr-acq{" lr-acq-big" if big else ""}"><div class="lr-cover {art}"></div><div class="lr-acq-main"><p class="lr-card-title" style="font-size: {16 if big else 14}px;"><a href="#">{e(title)}</a></p>'
                f'<p class="lr-meta"><a href="#" style="color: inherit;">{e(artist)}</a></p>{song}<p class="lr-meta">Quality profile: {e(profile)}</p>{det}</div>'
                f'<div class="lr-acq-state">{st}{extra_state}</div><div class="lr-rank-tools">{actions}</div></li>')
    ib = lambda ico, label: f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="{e(label)}" title="{e(label)}">{icon(ico)}</button>'  # noqa: E731
    rows = [
        acq("art-khru", "Con Todo El Mundo", "Khruangbin", "FLAC / CD quality · MP3 320 kbps", state("active", "acquisitions", "Downloading"),
            '<div class="lr-progress" role="progressbar" aria-label="Download progress" aria-valuenow="62" aria-valuemin="0" aria-valuemax="100"><span style="width: 62%;"></span></div>'
            '<p class="lr-meta" style="color: var(--lr-text);">62% complete</p><p class="lr-meta">2.4 MB/s · Total 412 MB · 156 MB remaining</p><p class="lr-meta">4 of 9 tracks remaining</p>',
            f'<button type="button" class="lr-btn">{icon("skip")}Use next source (12s)</button>',
            ["Peer: soulseek_user_42", "Source: Khruangbin - Con Todo El Mundo (2018) [FLAC]", "Expected files: 10", "Transfer states: InProgress, Queued"], big=True),
        acq("art-grouper2", "Shine a Light", "Grouper", "FLAC / CD quality", state("active", "acquisitions", "Importing"), '<p class="lr-meta">Checking tags and moving files into your library</p>'),
        acq("art-nala2", "Endlessness", "Nala Sinephro", "MP3 320 kbps", state("active", "clock", "Queued"), '<p class="lr-meta">Waiting for the peer to start</p>', ib("close", "Dismiss")),
        acq("art-broadcast", "Tender Buttons", "Broadcast", "FLAC / CD quality", state("caution", "alert", "Needs review"),
            '<p class="lr-meta">Two candidate folders match. Pick one in slskd, then refresh.</p>', ib("refresh", "Refresh status") + ib("close", "Dismiss")),
        acq("art-mdou2", "Funeral for Justice", "Mdou Moctar", "FLAC / CD quality", state("error", "alert", "No matches found"),
            '<p class="lr-meta">No source offered the album at a quality on your list.</p>', f'<button type="button" class="lr-btn">{icon("refresh")}Try again</button>' + ib("close", "Dismiss")),
        acq("art-cleo", "Know That You Are Loved", "Cleo Sol", "MP3 320 kbps", state("ok", "check", "Imported"), '<p class="lr-meta">Updated 17 Nov 2026, 14:02</p>',
            ib("close", "Dismiss"), song_of="Mother"),
    ]
    body = (pagehead("Acquisitions", "Download and import status, in the order you asked for them.",
                     right=f'<div class="lr-row"><button type="button" class="lr-btn">{icon("check")}Dismiss all successful imports</button><button type="button" class="lr-btn lr-btn-icon" aria-label="Refresh status" title="Refresh status">{icon("refresh")}</button></div>')
            + '      <p class="lr-status-line" role="status">6 acquisition records · 3 active</p>\n'
            + '      <ul class="lr-list" style="gap: var(--lr-space-16);">' + "\n".join(rows) + "</ul>\n")
    page("acquisitions", "Acquisitions", "acquisitions", body, getting=False)


def radio_page():
    def station(name, meta, on):
        return (f'<li class="lr-station-row"><span class="lr-logo">{icon("signal")}</span><span><span class="lr-card-title">{e(name)}</span><span class="lr-meta" style="display: block;">{e(meta)}</span></span>'
                f'<button type="button" class="lr-switch" role="switch" aria-checked="{"true" if on else "false"}" aria-label="Grab {e(name)}"><span class="lr-switch-track"></span>{"Grabbing" if on else "Grab"}</button></li>')

    def heard(time, art, title, artist, album, st, getstate="idle"):
        if getstate == "done":
            g = f'<span class="lr-btn lr-btn-done">{icon("check")}Requested</span>'
        else:
            g = f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="Get {e(title)}">{icon("get")}</button>'
        return (f'<li class="lr-heard"><span class="lr-time">{e(time)}</span><div class="lr-cover {art}"></div><div style="min-width: 0;"><p class="lr-card-title"><a href="#">{e(title)}</a></p>'
                f'<p class="lr-meta">{e(artist)} · {e(album)} · {e(st)}</p></div><div class="lr-rank-tools">{g}'
                f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="Save {e(album)}">{icon("saved")}</button>'
                f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="Remove {e(title)} from the log">{icon("close")}</button></div></li>')
    body = (pagehead("Grab the radio", "Turn on a Navidrome radio station and this app relays its stream, so the songs you actually listen to are logged here. Songs you skip past are not. Get downloads a logged song.")
            + section("addr", "App address", None, f'''        <form class="lr-row" style="align-items: end; gap: var(--lr-space-16);">
          <label class="lr-field" style="flex: 1 1 360px;"><span class="lr-field-label">Address your Navidrome apps use to reach this app</span><input class="lr-input" type="url" inputmode="url" placeholder="http://my-server.tailnet.ts.net:8000" value="http://media.tailnet.ts.net:8000"><span class="lr-field-help">For example its Tailscale address. Leave blank to use the address of this browser tab.</span></label>
          <button type="submit" class="lr-btn" style="margin-bottom: 22px;">{icon("check")}Save</button>
        </form>''')
            + section("stations", "Stations", "Grab relays a station so its songs are logged.",
                      f'        <ul class="lr-list">{station("FIP Jazz", "Navidrome station · relayed through this app", True)}{station("NTS 1", "Navidrome station", False)}{station("WFMU", "Navidrome station", False)}</ul>')
            + section("heard", "Heard", "Songs the grabbed stations played while you listened, newest first.",
                      f'''        <ul class="lr-liblist">
          {heard("14:32", "art-alice", "Blue Nile", "Alice Coltrane", "Ptah, the El Daoud", "FIP Jazz")}
          {heard("14:24", "art-yussef", "Rust", "Yussef Dayes", "Black Classical Music", "FIP Jazz", "done")}
          {heard("14:17", "art-nala", "Space 3", "Nala Sinephro", "Space 1.8", "FIP Jazz")}
        </ul>''', right=f'<div class="lr-row">{refresh_button()}<button type="button" class="lr-btn">{icon("trash")}Clear all</button></div>'))
    page("radio", "Radio", "radio", body)


# --- Pages: Settings, Login -----------------------------------------------------------------------

SETTINGS_TABS = [("library", "Navidrome"), ("acquisitions", "slskd"), ("listeners", "Last.fm"), ("signal", "ListenBrainz"), ("disc", "Discogs"), ("palette", "Appearance")]


def settings_page(name, selected, panel):
    tabs = "".join(f'<button type="button" class="lr-nav" role="tab" aria-selected="{"true" if lbl == selected else "false"}">{icon(ico)}{e(lbl)}</button>'
                   for ico, lbl in SETTINGS_TABS)
    body = (pagehead("Settings", "Configure the services discair uses. Secrets are never shown after saving.")
            + f'''      <div class="lr-settings">
        <div class="lr-vtabs" role="tablist" aria-label="Service settings" aria-orientation="vertical">{tabs}</div>
        <div class="lr-form" role="tabpanel" aria-label="{e(selected)}">
{panel}
        </div>
      </div>
''')
    page(name, "Settings · " + selected, "settings", body)


def field(label, value="", placeholder="", kind="text", help_text=None, secret=False):
    val = f' value="{e(value)}"' if value else ""
    ph = f' placeholder="{e(placeholder)}"' if placeholder else ""
    hint = (f'<span class="lr-secret">{icon("lock", True)}{e(help_text)}</span>' if secret and help_text
            else (f'<span class="lr-field-help">{e(help_text)}</span>' if help_text else ""))
    return f'<label class="lr-field"><span class="lr-field-label">{e(label)}</span><input class="lr-input" type="{kind}"{val}{ph}>{hint}</label>'


def form_actions(test=True, extra=""):
    t = f'<button type="button" class="lr-btn">{icon("plug")}Test connection</button>' if test else ""
    return f'<div class="lr-row"><button type="button" class="lr-btn lr-btn-primary">{icon("check")}Save settings</button>{t}{extra}</div>'


def settings_pages():
    settings_page("settings", "Navidrome", f'''          <div class="lr-form-group"><h2 class="lr-section-title">Navidrome connection</h2>
          {field("Navidrome URL", "http://navidrome:4533", kind="url")}
          {field("Username", "owner")}
          {field("Password", placeholder="Leave blank to keep the saved password", kind="password", help_text="A password is saved. It is never shown.", secret=True)}
          {field("Music library directory visible to the Librarian backend", "/media/library/music", help_text="Use the path as seen by the Librarian process or container, not a path inside the Navidrome service.")}</div>
          <p class="lr-ok-text" role="status">{icon("check", True)} Connected to Navidrome 0.53 as owner.</p>
          {form_actions()}''')
    prio = [("FLAC 16-bit / 44.1 kHz", True), ("FLAC / CD quality", False), ("MP3 320 kbps", False), ("MP3 193–319 kbps", False), ("MP3 192 kbps", False)]
    rows = "".join(
        f'<li{" class=" + chr(34) + "is-dragging" + chr(34) if i == 1 else ""}><button type="button" class="lr-grip" aria-label="Drag {e(q)}">{icon("grip")}</button>'
        f'<span class="lr-rank-n" style="font-size: 16px;">{i + 1}</span><span class="lr-card-title">{e(q)}</span><span class="lr-row" style="flex-wrap: nowrap;">'
        f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="Move {e(q)} up"{" disabled" if i == 0 else ""}>{icon("chev-up")}</button>'
        f'<button type="button" class="lr-btn lr-btn-icon lr-btn-quiet" aria-label="Move {e(q)} down"{" disabled" if i == len(prio) - 1 else ""}>{icon("chev-down")}</button></span></li>'
        for i, (q, _) in enumerate(prio))
    settings_page("settings-slskd", "slskd", f'''          <div class="lr-form-group"><h2 class="lr-section-title">slskd connection</h2>
          {field("slskd URL", "http://slskd:5030", kind="url")}
          {field("API key", placeholder="Enter key to set or replace it", kind="password", help_text="A key is saved. It is never shown; leave blank to keep it.", secret=True)}
          {field("slskd completed-download directory visible to the Librarian backend", "/media/downloads/slskd/complete", help_text="An absolute path on the machine or container running the Librarian backend. With Docker, the directory must be mounted.")}</div>
          <div class="lr-form-group"><h2 class="lr-section-title">Audio quality priority</h2>
          <p class="lr-field-help">Drag a row by its handle to set your preferred order, or use Move up and Move down.</p>
          <ol class="lr-priority" aria-label="Audio quality priority order">{rows}</ol></div>
          <p class="lr-error-text" role="status">{icon("alert", True)} Could not reach slskd at http://slskd:5030: connection refused.</p>
          {form_actions()}''')
    themes = [("Listening Room", ["#101114", "#16181D", "#F5B544", "#F2F1EE"], True), ("Default", ["#F7F5F0", "#FFFFFF", "#2F5D50", "#1B1B1B"], False),
              ("Tape Deck", ["#1E1B16", "#2A251E", "#E86A33", "#F3E9D2"], False), ("Ledger Room", ["#F4F1E8", "#FFFFFF", "#7A2E1F", "#202020"], False)]
    choices = "".join(
        f'<button type="button" class="lr-choice" role="radio" aria-checked="{"true" if on else "false"}"><span class="lr-swatch" aria-hidden="true">'
        + "".join(f'<span style="background: {c};"></span>' for c in cs) + f'</span>{e(n)}{" · default" if n == "Listening Room" else ""}</button>'
        for n, cs, on in themes)
    settings_page("settings-appearance", "Appearance", f'''          <div class="lr-form-group"><h2 class="lr-section-title">Theme</h2>
          <p class="lr-field-help">Listening Room is the default. The older themes stay until the owner retires them (decision D2).</p>
          <div class="lr-choices" role="radiogroup" aria-label="Theme">{choices}</div></div>
          <div class="lr-form-group"><h2 class="lr-section-title">Font</h2>
          <div class="lr-note">{icon("info")}<div><p class="lr-note-title">Listening Room uses its own fonts</p><p class="lr-note-text">Instrument Sans for titles and reasons, Inter for text. The font choice applies to the older themes only.</p></div></div></div>''')
    # The other three tabs use the same parts; drawn here so nothing is left to guess.
    settings_page("settings-services", "Last.fm", f'''          <div class="lr-form-group"><h2 class="lr-section-title">Last.fm API</h2>
          <p class="lr-field-help">Optional. Used to enrich recommendations with album popularity and artist tags.</p>
          {field("Username", "owner_fm", help_text="Your Last.fm username is used to read your listening history for Daily picks.")}
          {field("API key", placeholder="Leave blank to keep the saved key", kind="password", help_text="A key is saved. It is never shown.", secret=True)}</div>
          {form_actions()}
          <div class="lr-form-group" style="margin-top: var(--lr-space-16);"><h2 class="lr-section-title">ListenBrainz profile (same parts)</h2>
          {field("Username", "owner_lb")}
          {field("User token (optional)", placeholder="Leave blank to keep the saved token", kind="password")}</div>
          <div class="lr-form-group"><h2 class="lr-section-title">Discogs (same parts)</h2>
          {field("Personal access token", placeholder="Enter a token to set or replace it", kind="password", help_text="Optional. Adds Discogs styles to similar artists and genre pages. Data provided by Discogs.")}</div>
          {form_actions(extra=f'<button type="button" class="lr-btn">{icon("trash")}Remove saved token</button>')}''')


def login_page():
    doc = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Listening Room · Sign in</title>
<link rel="stylesheet" href="../tokens.css">
<link rel="stylesheet" href="../components.css">
<style> .wrap {{ min-height: 100vh; display: grid; place-items: center; padding: var(--lr-space-16); }} </style>
</head>
<body>
<!--sprite-->
<!--/sprite-->
<main class="wrap">
  <form class="lr-login" aria-labelledby="login-title">
    <a class="lr-brand" href="#" style="padding: 0;"><svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true"><circle cx="14" cy="14" r="13" fill="#F5B544"/><circle cx="14" cy="14" r="4" fill="#0C0D10"/></svg>discair</a>
    <div><h1 class="lr-page-title" id="login-title" style="font-size: 30px; line-height: 34px;">Sign in</h1><p class="lr-page-sub">Use the account you set up for this server.</p></div>
    {field("Username", "owner")}
    {field("Password", kind="password")}
    <p class="lr-error-text" role="alert">{icon("alert", True)} Wrong username or password.</p>
    <button type="submit" class="lr-btn lr-btn-primary" style="justify-content: center;">Sign in</button>
  </form>
</main>
</body>
</html>
'''
    write("login", doc)


ALL = [discover_music, discover_daily, discover_dives, discover_others, library_artists, library_albums, artist_page,
       lambda: album_page("album", False), lambda: album_page("album-owned", True), album_modal, genre_page, search_page,
       saved_page, blocklist_page, acquisitions_page, radio_page, settings_pages, login_page]

# Every generated page name, for build.py's renders.
NAMES = ["discover", "discover-daily", "discover-dives", "discover-personal", "discover-collection", "discover-new", "library", "library-albums",
         "artist", "album", "album-owned", "album-modal", "genre", "search", "saved", "blocklist", "acquisitions", "radio",
         "settings", "settings-slskd", "settings-appearance", "settings-services", "login"]


def write_all():
    """Write every generated page."""
    for build in ALL:
        build()


if __name__ == "__main__":
    write_all()
