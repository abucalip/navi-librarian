from mac_shell import *
from mac_home import header, ERAS, SHELF, SHELF_L, skel

# =============================================================== Settings > Services
def tabs(on):
    return '<div class="seg" style="margin-bottom:24px">' + "".join(f'<span class="{"on" if t == on else ""}" style="height:28px;padding:0 16px">{t}</span>' for t in ["Services", "Playback", "Music folder", "Profiles"]) + '</div>'

def wiring(lb="ok", lib="ok"):
    """Who talks to whom. A line is drawn only where one service really calls another."""
    W, H = 948, 216
    col = {"ok": "#AEAEB2", "da": "var(--danger)", "off": "#D1D1D6", "wa": "var(--warning)"}
    def node(x, y, w, icon, name, sub, state="ok"):
        glyph = {"ok": ("checkc", "var(--success)"), "da": ("xc", "var(--danger)"), "off": ("minus", "var(--text-3)"), "wa": ("warn", "var(--warning)"), "unk": ("minus", "var(--text-3)")}[state]
        return (f'<div style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:48px;border-radius:8px;background:#fff;box-shadow:inset 0 0 0 1px {"var(--danger)" if state == "da" else "var(--sep-strong)"};'
                f'display:flex;align-items:center;gap:8px;padding:0 8px"><span class="c2">{ico(icon,16)}</span><div class="f1" style="min-width:0"><div class="t-head trunc" style="line-height:16px">{name}</div>'
                f'<div class="t-cap c2 trunc">{sub}</div></div><span style="color:{glyph[1]}">{ico(glyph[0],14,2.2)}</span></div>')
    down = "unk" if lib == "da" else None
    s = f'<svg width="{W}" height="{H}" style="position:absolute;left:0;top:0">'
    def line(x1, y1, x2, y2, st="ok"):
        dash = ' stroke-dasharray="4 4"' if st in ("da", "off", "unk") else ""
        c = col["off" if st == "unk" else st]
        return f'<path d="M{x1},{y1} C{(x1+x2)/2},{y1} {(x1+x2)/2},{y2} {x2},{y2}" fill="none" stroke="{c}" stroke-width="1.5"{dash}/>'
    s += line(160, 84, 268, 44, lib) + line(160, 108, 268, 172, "ok") + line(428, 60, 428, 148, down or "ok").replace("C428.0,60 428.0,148", "L")
    for i, stt in enumerate([down or "ok", down or "ok", down or lb, down or "off", down or "ok"]):
        s += line(588, 44, 700 if i < 3 else 700, 24 + i * 42, stt)
    s += "</svg>"
    n = node(0, 72, 160, "mac", "This Mac", "Discair app")
    n += node(268, 20, 320, "server", "Librarian", "Picks, downloads, insights · 100.92.14.7", lib)
    n += node(268, 148, 320, "note", "Navidrome", "Your library and playback · 192.168.1.87")
    names = [("cloud", "slskd", "Downloads"), ("wave", "Last.fm", "Listening history"), ("wave", "ListenBrainz", "Taste, popularity"), ("disc", "Discogs", "Optional · not set up"), ("graph", "MusicBrainz data", "Stored on the server")]
    sts = [down or "ok", down or "ok", down or lb, down or "off", down or "ok"]
    for i, (ic, nm, sb) in enumerate(names):
        n += node(700, i * 42, 248, ic, nm, sb, sts[i]).replace("height:48px", "height:36px").replace('<div class="t-cap c2 trunc">', '<div class="t-cap c2 trunc" style="display:none">')
    return f'<div style="position:relative;width:{W}px;height:{H}px">{s}{n}</div>'

def srow(icon, name, role, powers, state, open_=None, last=False):
    chips = "".join(pill("", p) for p in powers)
    head = (f'<div class="row g16 center" style="min-height:56px;padding:8px 0"><div style="width:32px;height:32px;border-radius:8px;background:#fff;display:flex;align-items:center;justify-content:center" class="c2">{ico(icon,16)}</div>'
            f'<div style="width:232px"><div class="t-head">{name}</div><div class="t-call c2 trunc">{role}</div></div><div class="f1 row g4" style="flex-wrap:wrap">{chips}</div>'
            f'<div style="width:168px;text-align:right">{state}</div><span class="c2">{ico("chevu" if open_ else "chevd",14,2.2)}</span></div>')
    return f'<div style="{"" if last else "box-shadow:0 1px 0 var(--sep)"}">{head}{open_ or ""}</div>'

def detail(status_rows, setup_rows, actions, note=""):
    kv = lambda rows: "".join(f'<div class="row between g16" style="padding:4px 0"><span class="t-call c2">{k}</span><span class="t-call num" style="text-align:right">{v}</span></div>' for k, v in rows)
    return (f'<div style="background:#fff;border-radius:8px;padding:16px;margin:0 0 16px 48px">{note}<div class="row g32">'
            f'<div class="f1"><div class="t-eye" style="margin-bottom:4px">Status now</div>{kv(status_rows)}</div><div class="vr"></div>'
            f'<div class="f1"><div class="t-eye" style="margin-bottom:4px">Setup</div>{kv(setup_rows)}</div></div><div class="row g8 mt16">{actions}</div></div>')

def group(title, rows):
    return f'<div class="t-eye" style="margin:24px 0 8px 16px">{title}</div><div class="panel" style="padding:0 16px">{rows}</div>'

def services(mode):
    lb = "da" if mode == "degraded" else "ok"; lib = "da" if mode == "down" else "ok"
    unk = '<span class="st off">' + ico("minus", 14, 2) + 'Unknown</span>'
    S = lambda ok: unk if mode == "down" else ok
    if mode == "ok":
        summ = (f'<div class="row g16 center"><span class="ok">{ico("checkc",32,1.800)}</span><div><div class="t-title2">Everything is working</div>'
                f'<div class="t-call c2 mt4">8 of 8 services you use answered · checked 2 minutes ago, at 21:14</div></div><div style="flex:1"></div><span class="btn">{ico("refresh",14,2)}Check again</span></div>')
    elif mode == "degraded":
        summ = (f'<div class="row g16 center"><span class="wa">{ico("warn",32,1.800)}</span><div><div class="t-title2">One service needs attention</div>'
                f'<div class="t-call c2 mt4">ListenBrainz rejected the saved token. Playback, picks and Get are not affected · checked at 21:14</div></div><div style="flex:1"></div><span class="btn">{ico("refresh",14,2)}Check again</span></div>')
    else:
        summ = (f'<div class="row g16 center"><span class="da">{ico("xc",32,1.800)}</span><div><div class="t-title2">Can’t reach Librarian</div>'
                f'<div class="t-call c2 mt4 measure">No answer from 100.92.14.7:8080 since 20:58. Check that Tailscale is connected on this Mac. Your library still plays from Navidrome.</div></div>'
                f'<div style="flex:1"></div><span class="btn pri">{ico("refresh",14,2)}Try again</span><span class="btn">Edit address</span></div>')
    lbopen = None
    if mode == "degraded":
        lbopen = detail([("Answer", '<span class="st da">' + ico("xc", 12, 2.2) + 'Token rejected (401)</span>'), ("Since", "9 November, 14:02"), ("Last good read", "9 November, 13:02 · 48,912 listens"), ("Checked", "Today, 21:14")],
                        [("Username", "the-owner"), ("Token", "Saved on the server, never shown"), ("Used by", "Taste, popularity, lenses")],
                        '<span class="btn pri">Replace token</span><span class="btn">Test again</span><span class="btn out">Disconnect</span>',
                        note=f'<div class="notice da" style="margin-bottom:16px">{ico("xc",16,2,"da")}<div><b>ListenBrainz did not accept the token.</b> Create a new one at listenbrainz.org, under Settings, then paste it here. '
                             f'Until then Taste and popularity keep showing the data read on 9 November and say so.</div></div>')
    libopen = None
    if mode == "ok":
        libopen = detail([("Answer", '<span class="st ok">' + ico("checkc", 12, 2.2) + 'Signed in</span>'), ("Route", "Tailscale"), ("Checked", "Today, 21:14"), ("Server contract", "Version 1 · data generation 14")],
                         [("Address", "http://100.92.14.7:8080"), ("User", "owner"), ("Password", "In the Keychain on this Mac")],
                         '<span class="btn">Edit…</span><span class="btn">Sign in again</span>')
    core = srow("server", "Librarian", "Picks, downloads, insights", ["Home", "Discover", "Insights", "Downloads"], st("da", "No answer") if mode == "down" else st("ok", "Connected"), libopen)
    core += srow("note", "Navidrome", "Your library and playback", ["Library", "Playback", "Playlists"], st("ok", "Connected"), last=True)
    acq = srow("cloud", "slskd", "Finds and downloads what you Get", ["Get", "Downloads"], S(st("ok", "Connected")), last=True)
    hist = srow("wave", "Last.fm", "Listening history for picks", ["Picks", "Listener counts"], S(st("ok", "Connected")))
    hist += srow("wave", "ListenBrainz", "Listening history for taste", ["Taste", "Popularity", "Lenses"], S(st("da", "Token rejected") if mode == "degraded" else st("ok", "Connected")), lbopen, last=True)
    know = srow("graph", "MusicBrainz data", "Credits stored on the server", ["Connections", "Paths", "Atlas", "Timeline"], S(st("ok", "Loaded · broad")))
    know += srow("wave", "Sonic analysis", "Navidrome’s analysis of each song", ["Sonic paths", "Neighbours by ear"], st("ok", "Available"))
    know += srow("disc", "Discogs", "Edition details, optional", ["Editions"], S('<span class="btn sm">Set up</span>'), last=True)
    mac = srow("folder", "Music folder over SMB", "Optional, read only", ["Quick tag reads"], '<span class="st off">Off</span>', last=True)
    diagram = f'<div class="panel mt24"><div class="t-eye" style="margin-bottom:16px">How Discair is connected</div>{wiring(lb, lib)}</div>'
    return (header("Settings") + tabs("Services") + summ + diagram + group("Core", core) + group("Getting music", acq) + group("Listening history", hist)
            + group("Knowledge", know) + group("On this Mac", mac))

window("settings-services--healthy", "Settings, Services, all working", "settings", services("ok"), h=1700, playing=False)
window("settings-services--degraded", "Settings, Services, one service failing", "settings", services("degraded"), h=1960, playing=False, status=("wa", "1 needs attention"))
window("settings-services--librarian-unreachable", "Settings, Services, Librarian unreachable", "settings", services("down"), h=1280, playing=False, status=("da", "Librarian unreachable"))

def fld(label, value, help_="", cls="", w=""):
    return f'<div class="field" style="{w}"><label>{label}</label><div class="inp {cls}">{value}</div>' + (f'<div class="help">{help_}</div>' if help_ else "") + '</div>'
sheet = (f'<div class="sheetwrap"><div class="sheet"><div class="t-title2">slskd</div><div class="t-call c2 mt4">Finds and downloads the albums and songs you Get.</div>'
         f'<div class="col g16 mt24">{fld("Address", "http://192.168.1.87:5030", cls="focus")}{fld("API key", "<span class=c3>••••••••••••••••</span>", "Saved on the server. Leave empty to keep the saved key.")}'
         f'{fld("Folder slskd downloads into", "/downloads")}{fld("Music library folder", "/music", "As the server sees it, not as this Mac does.")}</div>'
         f'<div class="notice ok mt16">{ico("checkc",16,2,"ok")}<div><b>Test passed.</b> slskd answered and the key was accepted.</div></div>'
         f'<div class="row g8 mt24" style="justify-content:flex-end"><span class="btn" style="margin-right:auto">Test</span><span class="btn">Cancel</span><span class="btn pri">Save</span></div></div></div>')
window("settings-services--edit-sheet", "Settings, Services, edit sheet with a passed test", "settings", services("ok"), h=832, playing=False, overlay=sheet)

# =============================================================== Settings > Playback (native switches instead of On/Off capsule pairs)
def setrow(title, help_, control, last=False):
    return (f'<div class="row g24 center" style="padding:16px 0;{"" if last else "box-shadow:0 1px 0 var(--sep)"}"><div class="f1"><div class="t-head">{title}</div><div class="t-call c2 measure">{help_}</div></div>{control}</div>')
seg = lambda items, on: '<div class="seg">' + "".join(f'<span class="{"on" if i == on else ""}">{i}</span>' for i in items) + '</div>'
pb = (header("Settings") + tabs("Playback") + '<div class="panel" style="padding:0 16px">'
      + setrow("Crossfade between songs", "Tracks that follow each other on one album always play gapless, so the fade happens between unrelated songs.", seg(["Off", "2 s", "4 s", "6 s", "8 s"], "4 s"))
      + setrow("Streaming quality", "Original plays the file as it is. A number is the most the server may send, in kbps. Applies to songs started afterwards.", seg(["Original", "320", "256", "192"], "Original"))
      + setrow("Match the output sample rate", "Switches your Mac’s output device to each song’s rate when the device offers it. Put back when you switch this off or quit.", '<div class="sw on"></div>')
      + setrow("Scrobble plays", "Reports what you play to Navidrome, which feeds your history and recommendations.", '<div class="sw on"></div>')
      + setrow("Tell me when a Get finishes", "A macOS notification when an album is in your library, or could not be found.", '<div class="sw"></div>')
      + setrow("Keep played songs and covers", "Up to 2 GB on this Mac, oldest-used removed first. Now: 412 MB.", '<div class="row g16 center"><span class="btn sm dng">Clear…</span><div class="sw on"></div></div>')
      + setrow("Equalizer", "10 bands. Now: Off.", f'<span class="btn sm">Open{ico("chevr",12,2.2)}</span>', last=True) + '</div>')
window("settings--playback", "Settings, Playback", "settings", pb, h=832, playing=False)

# =============================================================== Insights
def bars_h(w, rows, hi=0, ghost=False, labelw=120):
    h = 28 * len(rows); bw = w - labelw - 48; top = max(v for _, v in rows)
    o = f'<svg width="{w}" height="{h}">'
    for i, (lab, v) in enumerate(rows):
        y = i * 28
        o += f'<text class="{"axb" if i == hi and not ghost else "ax"}" style="font-size:12px" x="0" y="{y+18}">{lab}</text>'
        o += f'<rect x="{labelw}" y="{y+9}" width="{bw}" height="10" rx="5" fill="var(--chart-ghost)"/>'
        o += f'<rect x="{labelw}" y="{y+9}" width="{bw*v/top:.0f}" height="10" rx="5" fill="{"var(--chart-3)" if ghost or i != hi else "var(--chart-1)"}" {"stroke-dasharray=\'3 3\'" if ghost else ""}/>'
        o += f'<text class="{"axb" if i == hi and not ghost else "axn"}" x="{w}" y="{y+18}" text-anchor="end">{v}%</text>'
    return o + "</svg>"
GEN = [("Dream pop", 19), ("Ambient", 17), ("Post-rock", 14), ("Spiritual jazz", 11), ("Krautrock", 9), ("Post-punk", 8)]
RHY = [("Night", 9), ("Morning", 31), ("Afternoon", 22), ("Evening", 38)]
def icard(lead, title, meta, body, actions):
    return (f'<div class="row g16" style="padding:16px 0;align-items:flex-start">{lead}<div class="f1"><div class="t-title3">{title}</div><div class="t-call c2">{meta}</div>'
            f'<div class="t-body mt8 measure">{body}</div><div class="row g8 mt16">{actions}</div></div></div>')
from mac_home import countbadge, chart_dumbbell
ins = (header("Insights", "Every card says why it is here. Lenses refreshed 2 hours ago.")
       + f'<div class="row g8" style="margin-bottom:24px">{pill("ok","Anniversaries · 2","check")}{pill("ok","Series · 3","check")}{pill("ok","Forgotten Gems · 4","check")}{pill("","Blind Spots · off")}{pill("","Hidden Canon · off")}</div>'
       + '<div class="t-title2" style="margin-bottom:16px">Your taste</div>'
       + f'<div class="row"><div class="panel f1"><div class="t-eye">Lately against always</div><div class="t-title1 mt4">More ambient, less post-punk lately.</div>'
         f'<div class="t-call c2 mt4">1,240 listens in the last 90 days against 48,912 overall.</div><div class="mt16">{chart_dumbbell(450, [("Ambient", 9, 17), ("Post-punk", 14, 8)])}</div>'
         f'<div class="row g8 mt16"><span class="btn sm">Make an Ambient playlist</span><span class="btn sm">Show Ambient in Library</span></div></div>'
       + f'<div class="panel f1"><div class="row between center"><div class="t-eye">Top genres</div><div class="row g8">{seg(["90 days", "Year", "All time"], "90 days")}{seg(["Genre", "Decade", "Area", "Label"], "Genre")}</div></div>'
         f'<div class="mt16">{bars_h(450, GEN)}</div><div class="t-cap c2 mt8">Share of 1,240 listens · 1,102 carried a genre</div></div></div>'
       + f'<div class="row mt16"><div class="panel f1"><div class="t-eye">When you listen</div><div class="t-title3 mt4">Evenings carry the most listens.</div>'
         f'<div class="mt16">{chart_cols(450, 160, [9, 31, 22, 38], ["Night<tspan class=\'ax\'> 0–5</tspan>", "Morning 6–11", "Afternoon 12–17", "Evening 18–23"], hi_idx=3, valuelabels=True, pad=(24, 0, 24, 0), barw=.5)}</div>'
         f'<div class="t-cap c2 mt8">Share of listens by hour, UTC · all time</div></div>'
       + f'<div class="panel f1"><div class="t-eye">Morning against night</div><div class="t-title3 mt4">Not enough night listening to compare.</div>'
         f'<div class="t-body c2 mt8 measure">A contrast is stated only when both sides hold 100 listens. Night has 61.</div>'
         f'<div class="mt16" style="height:8px;border-radius:4px;background:#E6E6EB"><i style="display:block;width:61%;height:100%;border-radius:4px;background:var(--chart-2)"></i></div><div class="t-call c2 mt8 num">61 of 100 listens</div></div></div>'
       + '<div class="t-title2 mt32" style="margin-bottom:16px">Lenses</div>'
       + f'<div class="row" style="align-items:flex-start"><div class="panel f1" style="padding:8px 16px"><div class="t-eye" style="padding-top:8px">Anniversaries</div>'
         + icard(cover("loveless", 72, 8), "Loveless turned 35 on 4 November", "My Bloody Valentine · 1991", "Released 4 November 1991. In your library, last played 14 months ago.", f'<span class="btn sm">{ico("play",10)}Play</span><span class="btn sm">Why?</span><span class="btn sm out">Dismiss</span>')
         + '<div class="hr"></div>' + icard(cover("satchi", 72, 8), "Journey in Satchidananda was recorded 56 years ago this week", "Alice Coltrane · 1971", "Recorded 8 November 1970. In your library, played 88 times.", f'<span class="btn sm">{ico("play",10)}Play</span><span class="btn sm">Why?</span><span class="btn sm out">Dismiss</span>')
       + '</div><div class="panel f1" style="padding:8px 16px"><div class="t-eye" style="padding-top:8px">Series</div>'
         + icard(countbadge("4/5", "owned").replace("48px", "72px"), "Talk Talk studio albums", "5 albums, 1982 to 1991", "You own four. Missing: The Party’s Over (1982)."
                 '<div class="row" style="gap:2px;margin-top:8px">' + "".join(f'<div style="flex:1;height:8px;border-radius:2px;background:{"#DCDCE2" if i == 0 else "var(--text)"}"></div>' for i in range(5)) + '</div>',
                 '<span class="btn sm">Get</span><span class="btn sm">Save</span><span class="btn sm">Why?</span><span class="btn sm out">Dismiss</span>')
         + '<div class="hr"></div><div class="t-eye" style="padding-top:16px">Blind Spots</div><div class="t-body c2" style="padding:8px 0 16px">Off. The server turns a lens on only after it passes its check.</div></div></div>')
window("insights--default", "Insights", "insights", ins, h=1500, playing=False)

# =============================================================== History
hist = (header("History", "When you last played each song. Navidrome keeps one latest play per song, so earlier plays of the same song are not shown.")
        + f'<div class="panel"><div class="panel-h"><div><div class="t-title2">Last 26 weeks</div><div class="t-call c2 mt4">Songs whose latest play fell on each day · 18 May to 11 November 2026</div></div>'
          f'<div class="row g4 center t-cap c2">Fewer' + "".join(f'<i style="width:12px;height:12px;border-radius:3px;background:{c}"></i>' for c in ("#ECECF0", "#F6C5D0", "#EE8FA5", "#E2537A", "#D61F4A")) + 'More</div></div>'
          f'<div style="position:relative">{chart_heat(26)}<div class="tip" style="left:372px;top:28px"><b>37 songs</b><span class="c2">Saturday 17 October 2026</span></div>'
          f'<div style="position:absolute;left:347px;top:79px;width:14px;height:14px;border-radius:4px;box-shadow:0 0 0 2px var(--text)"></div></div>'
          f'<div class="t-cap c2 mt8">Click a day or move with the arrow keys to read its count. 131 of 182 days have plays.</div></div>'
        + "".join(f'<div class="panel mt16"><div class="row between center"><div class="row g8 base"><div class="t-title3">{d}</div><span class="t-call c2 num">{n} songs</span></div><span class="btn sm">{ico("play",10)}Play day</span></div><div class="mt8">'
                  + "".join(f'<div class="row g16 center" style="height:32px;{"box-shadow:0 -1px 0 var(--sep)" if i else ""}"><span class="t-call c2 num" style="width:48px">{t}</span><span class="t-head" style="width:280px" >{s}</span><span class="t-body c2 f1 trunc">{a}</span><span class="t-call c2 num">{p} plays</span></div>'
                            for i, (t, s, a, p) in enumerate(rows)) + '</div></div>'
                  for d, n, rows in [("Today", 14, [("20:52", "After the Flood", "Talk Talk", 212), ("20:43", "Myrrhman", "Talk Talk", 187), ("19:10", "Alison", "Slowdive", 96), ("18:58", "Machine Gun", "Slowdive", 71)]),
                                     ("Yesterday", 22, [("23:14", "Pieces of the Night", "Bark Psychosis", 3), ("22:40", "Heaven or Las Vegas", "Cocteau Twins", 140), ("21:02", "Roygbiv", "Boards of Canada", 118)])]))
window("history--default", "History", "history", hist, h=832, playing=False)

# =============================================================== Downloads
def drow(key, title, artist, tracker, words, actions):
    return (f'<div class="lrow" style="padding:16px 0">{cover(key, 56, 8, "flat")}<div style="width:240px"><div class="ttl trunc">{title}</div><div class="sub trunc">{artist}</div></div>'
            f'<div class="f1">{tracker}<div class="t-call mt8">{words}</div></div><div class="row g8">{actions}</div></div>')
steps = '<div class="row t-cap c2" style="width:320px;margin-top:4px"><span class="f1">Found</span><span class="f1">Downloading</span><span class="f1">Importing</span><span class="f1">In library</span></div>'
dl = (header("Downloads", "2 on their way · 1 needs you · 3 arrived this week", right=seg(["All", "Active", "Needs you", "Arrived"], "All"))
      + '<div class="panel" style="padding:0 16px">'
      + drow("pygmalion", "Pygmalion", "Slowdive · FLAC 16/44", stage_track(1, 64, w=320) + steps, '<b class="num">64%</b> <span class="c2">· 7 of 9 files · started 21:02</span>', '<span class="btn sm">Use next source</span>')
      + drow("tender", "Tender Buttons", "Broadcast · any lossless", stage_track(0, w=320) + steps, '<span class="c2">Looking for a source · asked 3 minutes ago</span>', "")
      + drow("orang", "Herd of Instinct", ".O.rang · FLAC", stage_track(1, failed=True, w=320) + steps, f'{st("da", "Stopped: the source went offline at 41%.")}', '<span class="btn sm pri">Try again</span><span class="btn sm">Use next source</span><span class="btn sm out dng">Dismiss…</span>')
      + drow("hats", "Hats", "The Blue Nile · FLAC 16/44", stage_track(4, w=320) + steps, f'{st("ok", "In your library")} <span class="c2">· arrived today at 17:26 · not played yet</span>', f'<span class="btn sm">{ico("play",10)}Play</span>')
      + '</div>')
window("downloads--default", "Downloads", "downloads", dl, h=832, playing=False)

# =============================================================== Gap Radar (tokens only; Get is neutral, one primary per card)
def gtile(key, title, year, owned=True):
    c = cover(key, 96, 8, "flat", "" if owned else "opacity:.35;outline:2px dashed #636368;outline-offset:2px;")
    return (f'<div class="col" style="width:96px">{c}<div class="t-call trunc mt8" style="font-weight:600">{title}</div><div class="t-cap c2">{year}{"" if owned else " · Missing"}</div>'
            + ("" if owned else '<span class="btn sm mt8" style="align-self:flex-start">Get</span>') + '</div>')
gap = (header("Gap Radar", "Artists you own, with the albums the Librarian says are missing. Biggest gap first.")
       + f'<div class="row" style="align-items:flex-start"><div class="panel"><div class="row between center g24"><div><div class="t-title2">Talk Talk</div><div class="t-call c2 mt4">4 of 5 albums · 1 missing</div></div>'
         f'<div style="width:96px;height:8px;border-radius:4px;background:#E6E6EB"><i style="display:block;width:80%;height:100%;border-radius:4px;background:var(--text)"></i></div></div>'
         f'<div class="row g16 mt16">{gtile("hope", "The Party’s Over", 1982, False)}{gtile("tindrum", "It’s My Life", 1984)}{gtile("colour", "The Colour of Spring", 1986)}{gtile("eden", "Spirit of Eden", 1988)}{gtile("laughing", "Laughing Stock", 1991)}</div></div>'
       + f'<div class="panel"><div class="row between center g24"><div><div class="t-title2">Slowdive</div><div class="t-call c2 mt4">2 of 4 albums · 2 missing</div></div><span class="btn sm pri">Get 2 missing</span></div>'
         f'<div class="row g16 mt16">{gtile("heaven", "Just for a Day", 1991, False)}{gtile("souvlaki", "Souvlaki", 1993)}{gtile("pygmalion", "Pygmalion", 1995)}{gtile("deer", "Slowdive", 2017, False)}</div></div></div>')
window("gap-radar--default", "Gap Radar", "gap", gap, h=832, playing=False)

# =============================================================== Chart specimen sheet
line1, _ = chart_line(440, 200, GROWTH, ["Dec", "Mar", "Jun", "Sep", "Nov"], [1000, 1100, 1200, 1300], sel=19)
line2, _ = chart_line(440, 200, [181, 164, 190, 172, 201, 188, 214], ["23 Sep", "7 Oct", "21 Oct", "4 Nov"], [0, 100, 200, 300], prev=[150, 171, 160, 182, 175, 169, 181], area=False)
ghost, _ = chart_line(440, 200, [1, 1, 2, 2, 3, 3, 4], ["", "", ""], [0, 2, 4], ghost=True)
ADDED = [9, 14, 22, 31, 18, 12, 25, 16, 21, 28, 17, 12]; LAST = [6, 10, 12, 18, 20, 9, 14, 15, 11, 19, 13, 7]
MON = ["D", "J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N"]
def cell(title, rule, chart, note=""):
    return f'<div class="panel"><div class="t-title3">{title}</div><div class="t-call c2 mt4" style="min-height:36px">{rule}</div><div class="mt16" style="position:relative">{chart}</div>{f"<div class=\'t-cap c2 mt8\'>{note}</div>" if note else ""}</div>'
anat = ('<div style="position:relative;width:640px;height:300px">' + chart_line(520, 232, GROWTH, ["Dec", "Feb", "Apr", "Jun", "Aug", "Oct", "Nov"], [1000, 1100, 1200, 1300], sel=19, annot=(12, "Biggest month: March, 31 added"))[0]
        + '<div class="tip" style="left:330px;top:70px"><b>1,171 albums</b><span class="c2">12 July 2026</span></div></div>')
calls = [("Title", "17/24 Semibold, sentence case. Says what is measured."), ("Subtitle", "12/18 Regular, secondary. Unit, source and the exact period."),
         ("Value labels", "11 pt tabular, secondary, on the trailing side. No axis line, no tick marks."), ("Gridlines", "Horizontal only, 1 pt #E5E5EA, at most 4. The baseline is #C7C7CC."),
         ("Series", "2 pt accent line, round joins, 8% accent area under a single series. The last point carries a 4 pt dot."),
         ("Annotation", "11 pt secondary with a 1 pt leader and a hollow 3 pt marker. At most 2 per chart."),
         ("Selection", "1 pt rule plus a 5 pt accent dot with a 2 pt white ring. Click, drag or ← → moves it."),
         ("Tooltip", "White, radius 8, popover shadow. Value 13 Semibold tabular first, then the date in 11 pt secondary."),
         ("Time labels", "11 pt secondary, 5 to 7 labels, first left-aligned and last right-aligned so nothing hangs outside the plot.")]
sw = lambda hexv, name, use: f'<div class="sw-chip"><i style="background:{hexv}"></i><div><b>{name} · {hexv}</b>{use}</div></div>'
spec = ('<h2>Chart anatomy · Cupertino</h2><div class="row g32"><div class="panel white" style="width:672px">'
        '<div class="row between"><div><div class="t-title3">Collection over time</div><div class="t-call c2 mt4">Albums in your library · 1 December 2025 to today</div></div>'
        + seg(["3M", "1Y", "5Y", "All"], "1Y") + f'</div><div class="mt16">{anat}</div></div><div class="f1 col g8">'
        + "".join(f'<div class="row g16"><b class="t-head" style="width:96px;flex:none">{k}</b><span class="t-call c2">{v}</span></div>' for k, v in calls) + '</div></div>'
        '<h2>Chart types and when to use each</h2><div class="grid" style="grid-template-columns:repeat(3,1fr)">'
        + cell("Line: a total over time", "One accent line. The value axis may start above zero and the subtitle says so.", line1)
        + cell("Line with the period before", "The comparison is 1.5 pt dashed #8E8E93, never a second colour.", line2 + '<div class="legend mt8"><span><i></i>Last 7 weeks</span><span><i class="n"></i>The 7 weeks before</span></div>')
        + cell("Columns: counts per period", "Always from zero. The selected period is accent, the rest #C7C7CC. A 2 pt ink tick marks last year.", chart_cols(440, 200, ADDED, MON, hi_idx=3, yticks=[0, 10, 20, 30], marks=LAST), "Albums added per month · tick: same month a year earlier")
        + cell("Paired bars: two shares", "Context bar neutral above, highlighted bar accent below, values right-aligned in tabular figures.", chart_pairs(440, ERAS, hi="1990s", rowh=28))
        + cell("Dumbbell: before and after", "Hollow dot is the baseline, filled dot is now. Accent when the share rose, ink when it fell; never red or green.", chart_dumbbell(440, [("Ambient", 9, 17), ("Post-punk", 14, 8), ("Dream pop", 18, 19)]))
        + cell("Ranked bars: parts of a whole", "More than 3 parts are sorted bars, never a pie. One accent bar, 10 pt tall on a ghost track.", bars_h(440, GEN))
        + cell("Histogram: a distribution", "Ordered bins from zero with value labels. The actionable bin is accent.", chart_cols(440, 184, SHELF, SHELF_L, hi_idx=5, valuelabels=True, pad=(24, 0, 24, 0)))
        + cell("Heatmap: days", "Five steps from #ECECF0 to accent, 12 pt cells, 4 pt gaps, a Fewer to More key. Never hover-only.", chart_heat(18), "")
        + cell("Stage tracker: a pipeline", "Four 4 pt segments. Done is ink, current is accent with its percentage in words, failed is danger with words.",
               f'<div class="col g16">{stage_track(1, 64, w=320)}{stage_track(3, w=320)}{stage_track(1, failed=True, w=320)}{stage_track(4, w=320)}</div>', "Found · Downloading · Importing · In library")
        + '</div><h2>States every chart must have</h2><div class="grid" style="grid-template-columns:repeat(4,1fr)">'
        + cell("Loading", "Skeleton in the plot’s own footprint. No spinner, no layout shift.", skel("100%", 160, 8))
        + cell("Insufficient data", "Ghost dotted line plus one sentence that names the threshold.", f'<div style="position:relative;height:160px;overflow:hidden">{ghost.replace("440", "260", 1)}<div style="position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center"><div class="t-head">Not enough history yet</div><div class="t-call c2">Needs albums added in 3 different months.</div></div></div>')
        + cell("Not available", "The source is missing or off. Say which, and offer the fix.", f'<div style="height:160px;display:flex;flex-direction:column;justify-content:center;gap:8px"><div class="t-head">Needs ListenBrainz</div><div class="t-call c2">Listening charts read your history from ListenBrainz.</div><span class="btn sm" style="align-self:flex-start">Open Services</span></div>')
        + cell("Stale or failed", "Keep the last good chart, label its date, add a warning with words.", f'<div style="height:160px"><div class="notice wa" style="padding:8px">{ico("warn",16,2,"wa")}<div class="t-call"><b>As of 9 November.</b> The refresh failed; this is the last good data.</div></div><div style="opacity:.5;margin-top:8px">{skel("100%", 88, 8)}</div></div>')
        + '</div><h2>Chart colours</h2><div class="grid" style="grid-template-columns:repeat(4,1fr)">'
        + sw("#D61F4A", "chart.1", "The one highlighted series or bar") + sw("#8E8E93", "chart.2", "Comparison line, baseline dot") + sw("#C7C7CC", "chart.3", "Context bars") + sw("#ECECF0", "chart.ghost", "Tracks, empty cells, ghost marks")
        + sw("#E5E5EA", "chart.grid", "Gridlines") + sw("#C7C7CC", "chart.base", "Zero baseline") + sw("#1D1D1F", "text", "Done segments, “fell” dot, last-year tick") + sw("#B3261E", "danger", "Failed stage only, with words")
        + '</div>')
sheet_page("charts--specimens", "Chart rules and specimens", spec, w=1520, h=2040)

# =============================================================== Components and tokens sheet
typ = [("t-large", "Large title · 34/40 Bold −0.4", "Home"), ("t-hero", "Hero metric · 44/48 Bold −0.8 tabular", "1,284"), ("t-title1", "Title 1 · 24/32 Bold −0.3", "More ambient, less post-punk lately."),
       ("t-title2", "Title 2 · 20/24 Bold −0.2", "Collection over time"), ("t-metric", "Metric · 24/32 Semibold tabular", "214"), ("t-title3", "Title 3 · 17/24 Semibold −0.1", "Tim Friese-Greene"),
       ("t-head", "Headline · 13/20 Semibold", "Spirit of Eden"), ("t-body", "Body · 13/20 Regular", "You have played Laughing Stock 212 times."), ("t-call", "Callout · 12/18 Regular", "Talk Talk · 1988 · in your library"),
       ("t-cap", "Caption · 11/16 Regular", "Source: MusicBrainz · exact match"), ("t-eye", "Eyebrow · 11/16 Bold +0.06em caps", "Today’s pick")]
cols = [("#FFFFFF", "bg.content", "Opaque content"), ("#F5F5F7", "bg.panel", "Grouped panels"), ("#ECECF0", "bg.fill", "Neutral controls"), ("#E6E6EB", "bg.fill.onPanel", "Controls on a panel"),
        ("#1D1D1F", "text", "16.8:1 on white"), ("#636368", "text.secondary", "5.9:1 white · 5.5:1 panel"), ("#8E8E93", "text.tertiary", "Disabled, decorative"), ("#E5E5EA", "separator", "Hairlines"),
        ("#D61F4A", "accent", "5.06:1 with white"), ("#C8163F", "accent.strong", "Pressed, text on tint"), ("#FCE8EC", "accent.tint", "Selection ground"), ("#D1D1D6", "separator.strong", "Field and button outlines"),
        ("#187A48", "success", "tint #E6F4EC"), ("#8A5200", "warning", "tint #FFF4DC"), ("#B3261E", "danger", "tint #FBEAE8"), ("#0B5CAD", "info", "tint #E8F1FB")]
dialog = (f'<div style="width:320px;background:#fff;border-radius:16px;box-shadow:var(--shadow-pop);padding:24px"><div class="t-title3">Dismiss this download?</div>'
          f'<div class="t-body c2 mt8">Herd of Instinct by .O.rang. The files downloaded so far are deleted. The server refuses if that would touch anything else.</div>'
          f'<div class="row g8 mt24" style="justify-content:flex-end"><span class="btn">Keep</span><span class="btn dng">Dismiss and delete files</span></div></div>')
menu = '<div class="menu" style="width:220px"><div>Play next</div><div>Add to queue</div><div class="on">Show in Connections</div><hr><div>Save</div><div>Not for me</div><hr><div class="da">Dismiss…</div></div>'
comp = ('<h2>Type scale · SF Pro (system font), tabular figures for every number</h2><div class="col g8">'
        + "".join(f'<div class="row g24 base"><span class="t-call c2" style="width:280px;flex:none">{lab}</span><span class="{c}">{s}</span></div>' for c, lab, s in typ) + '</div>'
        '<h2>Colour tokens</h2><div class="grid" style="grid-template-columns:repeat(4,1fr)">' + "".join(sw(h, n, u) for h, n, u in cols) + '</div>'
        '<h2>Buttons: one filled primary per view</h2><div class="row g16 center" style="flex-wrap:wrap">'
        f'<span class="btn pri lg">{ico("cloud",16,2)}Get album</span><span class="btn lg onwhite">Save</span><span class="btn lg out">Not for me</span><span class="vr"></span>'
        f'<span class="btn pri">Re-centre here</span><span class="btn onwhite">Open artist</span><span class="btn out">Disconnect</span><span class="btn onwhite dis">Disabled</span><span class="btn onwhite dng">Dismiss…</span><span class="vr"></span>'
        f'<span class="btn pri sm">Try again</span><span class="btn sm onwhite">{ico("play",10)}Play</span><span class="btn sm out">Dismiss</span></div>'
        '<div class="callout mt8">Large 40 pt high · regular 32 · small 24. Capsule. Label 14, 13 and 12 Semibold. Primary: accent fill, white label. Secondary: neutral fill. Tertiary: 1 pt outline. Destructive: danger label, never a red fill, and it names what is deleted.</div>'
        '<h2>Controls</h2><div class="row g32" style="align-items:flex-start">'
        f'<div class="col g16" style="width:280px">{fld("Address", "http://100.92.14.7:8080")}{fld("Address", "http://100.92.14.7:8080", cls="focus")}'
        f'<div class="field"><label>Address</label><div class="inp err">100.92.14.7</div><div class="help err">{ico("warn",12,2.2)}Add http:// or https:// at the start.</div></div>{fld("Username", "you", cls="ph", help_="Placeholder is an example, never the label.")}</div>'
        f'<div class="col g16"><div class="row g16 center">{seg(["3M", "1Y", "5Y", "All"], "1Y")}{seg(["Graph", "List"], "Graph")}</div><div class="row g16 center"><div class="sw on"></div><div class="sw"></div><span class="t-call c2">Switch 36 × 20, accent when on</span></div>'
        f'<div class="row g8 center">{st("ok","Connected")}{st("wa","Not updating")}{st("da","Token rejected")}{st("inf","Paused")}{st("off","Unknown")}</div>'
        f'<div class="row g8 center">{pill("ok","Credit","check")}{pill("","Link")}{pill("acc","Selected")}{pill("wa","As of 9 Nov","warn")}{pill("inf","Not loaded","info")}</div>'
        f'<div class="row g8 center"><span class="key">→</span><span class="key">Space</span><span class="key">⌘K</span><span class="t-call c2">Key caps 24 high, radius 8</span></div></div>'
        f'<div class="col g8 f1"><div class="notice inf">{ico("info",16,2,"inf")}<div><b>Not loaded.</b> The server has no data for this artist yet.</div><span class="btn sm">Request update</span></div>'
        f'<div class="notice wa">{ico("warn",16,2,"wa")}<div><b>Taste could not refresh.</b> Showing data from 9 November.</div><span class="btn sm">Fix</span></div>'
        f'<div class="notice da">{ico("xc",16,2,"da")}<div><b>Can’t reach Librarian.</b> Your library still plays.</div><span class="btn sm">Try again</span></div>'
        f'<div class="notice ok">{ico("checkc",16,2,"ok")}<div><b>Saved.</b> slskd answered and the key was accepted.</div></div></div></div>'
        '<h2>Overlays</h2><div class="row g32" style="align-items:flex-start;background:#ECECF0;border-radius:16px;padding:32px">'
        f'{dialog}{menu}<div class="tip" style="position:static"><b>1,171 albums</b><span class="c2">12 July 2026 · 5 added that week</span></div>'
        '<div class="callout" style="max-width:260px">Alert: 320 wide, radius 16, padding 24. The safe choice is the default button; the destructive one says what happens. Menu: radius 12, rows 24 high, selection is the accent. Chart tooltip: radius 8.</div></div>'
        '<h2>Spacing, radius and elevation</h2><div class="row g32 end">'
        + "".join(f'<div class="col center g8"><div style="width:{v}px;height:{v}px;background:var(--accent-tint);box-shadow:inset 0 0 0 1px var(--accent)"></div><span class="t-cap c2">{v}</span></div>' for v in (4, 8, 16, 24, 32))
        + '<span class="vr"></span>'
        + "".join(f'<div class="col center g8"><div style="width:64px;height:64px;background:var(--bg-panel);border-radius:{r}px;box-shadow:inset 0 0 0 1px var(--sep-strong)"></div><span class="t-cap c2">{n} {r}</span></div>' for n, r in (("control", 8), ("inner", 8), ("popover", 16), ("sidebar", 20), ("panel", 24), ("window", 26)))
        + '<span class="vr"></span><div class="callout" style="max-width:300px">Gaps: 4, 8, 16, 24, 32. One documented exception: 12 for the horizontal padding of small buttons and sidebar row radius. Nested radius = outer − padding: panel 24 − 16 = 8 for covers and tiles inside. Panels are tonal, not shadowed; only covers and overlays cast a shadow.</div></div>')
sheet_page("components--tokens-and-controls", "Tokens and controls", comp, h=1680)
