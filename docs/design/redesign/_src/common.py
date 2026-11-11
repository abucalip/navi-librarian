"""Shared helpers for the redesign mockups: icons, generated covers, SVG charts."""
import hashlib, math

# ---------------------------------------------------------------- icons (24 grid, stroke)
I = {
 "home": '<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1z"/>',
 "library": '<path d="M5 4v16M9 4v16"/><path d="M13 5l5 15" /><path d="M13 5l0 0"/><rect x="12.2" y="4.2" width="3.4" height="15.6" rx=".6" transform="rotate(-14 14 12)"/>',
 "sparkles": '<path d="M10 4l1.6 4.4L16 10l-4.4 1.6L10 16l-1.6-4.4L4 10l4.4-1.6z"/><path d="M18 14l.8 2.2L21 17l-2.2.8L18 20l-.8-2.2L15 17l2.2-.8z"/>',
 "radar": '<circle cx="12" cy="12" r="2"/><path d="M7.8 7.8a6 6 0 0 0 0 8.4M16.2 7.8a6 6 0 0 1 0 8.4M5 5a10 10 0 0 0 0 14M19 5a10 10 0 0 1 0 14"/>',
 "graph": '<circle cx="12" cy="5" r="2.2"/><circle cx="5" cy="18" r="2.2"/><circle cx="19" cy="18" r="2.2"/><path d="M11 7l-5 9M13 7l5 9M7.2 18h9.6"/>',
 "timeline": '<path d="M4 6h10M4 12h16M4 18h7"/><circle cx="17" cy="6" r="1.6"/><circle cx="14" cy="18" r="1.6"/>',
 "map": '<path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/>',
 "bulb": '<path d="M9 17h6M10 20h4"/><path d="M12 3a6 6 0 0 0-3.6 10.8c.6.5 1 1.2 1 2V17h5.2v-1.2c0-.8.4-1.500 1-2A6 6 0 0 0 12 3z"/>',
 "wand": '<path d="M5 19L16 8M14 6l4 4"/><path d="M18 3v3M16.500 4.500h3M6 5v2M5 6h2M19 14v2M18 15h2"/>',
 "download": '<circle cx="12" cy="12" r="9"/><path d="M12 7v9M8.500 12.500L12 16l3.500-3.500"/>',
 "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 2.500v3M12 18.500v3M2.500 12h3M18.500 12h3M5.300 5.300l2.100 2.100M16.600 16.600l2.100 2.100M5.300 18.700l2.100-2.100M16.600 7.400l2.100-2.100"/>',
 "search": '<circle cx="11" cy="11" r="6.500"/><path d="M16 16l4.500 4.500"/>',
 "list": '<path d="M8 6h12M8 12h12M8 18h12"/><circle cx="4" cy="6" r=".8"/><circle cx="4" cy="12" r=".8"/><circle cx="4" cy="18" r=".8"/>',
 "grid": '<rect x="4" y="4" width="6.500" height="6.500" rx="1.200"/><rect x="13.500" y="4" width="6.500" height="6.500" rx="1.200"/><rect x="4" y="13.500" width="6.500" height="6.500" rx="1.200"/><rect x="13.500" y="13.500" width="6.500" height="6.500" rx="1.200"/>',
 "play": '<path d="M7 4.500v15l12-7.500z" fill="currentColor"/>',
 "pause": '<rect x="6" y="5" width="4" height="14" rx="1" fill="currentColor"/><rect x="14" y="5" width="4" height="14" rx="1" fill="currentColor"/>',
 "next": '<path d="M5 5v14l9-7z" fill="currentColor"/><path d="M17.500 5v14"/>',
 "prev": '<path d="M19 5v14l-9-7z" fill="currentColor"/><path d="M6.500 5v14"/>',
 "heart": '<path d="M12 20s-7.500-4.600-7.500-10A4.300 4.300 0 0 1 12 7.600 4.300 4.300 0 0 1 19.500 10c0 5.400-7.500 10-7.500 10z"/>',
 "more": '<circle cx="5" cy="12" r="1.400" fill="currentColor"/><circle cx="12" cy="12" r="1.400" fill="currentColor"/><circle cx="19" cy="12" r="1.400" fill="currentColor"/>',
 "morev": '<circle cx="12" cy="5" r="1.400" fill="currentColor"/><circle cx="12" cy="12" r="1.400" fill="currentColor"/><circle cx="12" cy="19" r="1.400" fill="currentColor"/>',
 "chevr": '<path d="M9 5l7 7-7 7"/>',
 "chevl": '<path d="M15 5l-7 7 7 7"/>',
 "chevd": '<path d="M5 9l7 7 7-7"/>',
 "chevu": '<path d="M5 15l7-7 7 7"/>',
 "check": '<path d="M5 12.500l4.500 4.500L19 7.500"/>',
 "checkc": '<circle cx="12" cy="12" r="9"/><path d="M8 12.300l2.800 2.800L16 9.700"/>',
 "x": '<path d="M6 6l12 12M18 6L6 18"/>',
 "xc": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
 "warn": '<path d="M12 4l9 16H3z"/><path d="M12 10v4.500M12 17.200v.300"/>',
 "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.500v.300"/>',
 "cloud": '<path d="M7 18a4 4 0 0 1-.500-8A5.500 5.500 0 0 1 17.200 9 4.500 4.500 0 0 1 17 18z"/><path d="M12 11v5M9.800 14l2.200 2.200 2.200-2.200"/>',
 "radio": '<rect x="3" y="8" width="18" height="12" rx="2"/><path d="M7 8l9-4"/><circle cx="8.500" cy="14" r="2.500"/><path d="M14.500 12h3.500M14.500 16h3.500"/>',
 "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.500 2"/>',
 "calendar": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M8 3v4M16 3v4"/>',
 "person": '<circle cx="12" cy="8" r="4"/><path d="M4 20c1-4 4.500-6 8-6s7 2 8 6"/>',
 "disc": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.500"/>',
 "pin": '<path d="M12 21s7-6.300 7-11.500a7 7 0 0 0-14 0C5 14.700 12 21 12 21z"/><circle cx="12" cy="9.500" r="2.500"/>',
 "tag": '<path d="M4 4h8l8 8-8 8-8-8z"/><circle cx="8.500" cy="8.500" r="1.300"/>',
 "note": '<path d="M9 18V6l10-2v12"/><circle cx="6.500" cy="18" r="2.500"/><circle cx="16.500" cy="16" r="2.500"/>',
 "refresh": '<path d="M19 12a7 7 0 1 1-2.200-5.100"/><path d="M19 4v4.500h-4.500"/>',
 "server": '<rect x="4" y="4" width="16" height="6.500" rx="1.500"/><rect x="4" y="13.500" width="16" height="6.500" rx="1.500"/><path d="M7.500 7.300h.300M7.500 16.800h.300"/>',
 "bolt": '<path d="M13 3L5 14h6l-1 7 8-11h-6z"/>',
 "arrowu": '<path d="M12 19V5M6 11l6-6 6 6"/>',
 "arrowd": '<path d="M12 5v14M6 13l6 6 6-6"/>',
 "arrowr": '<path d="M5 12h14M13 6l6 6-6 6"/>',
 "phone": '<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/>',
 "plus": '<path d="M12 5v14M5 12h14"/>',
 "minus": '<path d="M5 12h14"/>',
 "back": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
 "tune": '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
 "wave": '<path d="M4 10v4M8 6v12M12 9v6M16 4v16M20 10v4"/>',
 "link": '<path d="M10 14a4 4 0 0 0 5.700 0l3-3a4 4 0 0 0-5.700-5.700l-1 1"/><path d="M14 10a4 4 0 0 0-5.700 0l-3 3a4 4 0 0 0 5.700 5.700l1-1"/>',
 "eye": '<path d="M2.500 12S6 5.500 12 5.500 21.500 12 21.500 12 18 18.500 12 18.500 2.500 12 2.500 12z"/><circle cx="12" cy="12" r="2.800"/>',
 "lock": '<rect x="5" y="10.500" width="14" height="9.500" rx="2"/><path d="M8 10.500V8a4 4 0 0 1 8 0v2.500"/>',
 "mac": '<rect x="3" y="4" width="18" height="12" rx="1.500"/><path d="M8 20h8M12 16v4"/>',
 "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
 "moon": '<path d="M19 14.500A8 8 0 0 1 9.500 5 8 8 0 1 0 19 14.500z"/>',
 "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2.500v2.500M12 19v2.500M2.500 12H5M19 12h2.500M5.300 5.300l1.800 1.800M16.900 16.900l1.800 1.800M5.300 18.700l1.800-1.800M16.900 7.100l1.800-1.800"/>',
 "queue": '<path d="M4 6h16M4 11h16M4 16h9"/><path d="M17 14.500v5l4-2.500z" fill="currentColor"/>',
 "shuffle": '<path d="M4 7h3c5 0 5 10 10 10h3M4 17h3c1.500 0 2.500-.800 3.400-2M17 7h3M13.600 9c.9-1.200 1.900-2 3.400-2"/><path d="M18 4.500L20.500 7 18 9.500M18 14.500l2.500 2.500-2.500 2.500"/>',
 "star": '<path d="M12 3.500l2.600 5.400 5.900.8-4.300 4.100 1 5.900L12 16.900l-5.200 2.800 1-5.900-4.300-4.100 5.900-.8z"/>',
 "album": '<rect x="4" y="4" width="16" height="16" rx="2.500"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r=".8" fill="currentColor"/>',
 "filter": '<path d="M4 6h16M7 12h10M10 18h4"/>',
 "sort": '<path d="M7 5v14M4 16l3 3 3-3M17 19V5M14 8l3-3 3 3"/>',
 "bell": '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.500 2h-15z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
 "trash": '<path d="M5 7h14M10 7V4.500h4V7M7 7l1 13h8l1-13"/>',
 "key": '<circle cx="8" cy="14" r="4"/><path d="M11 11l8-8M16 6l2.500 2.500M14 8l2 2"/>',
}

def ico(name, size=16, sw=1.800, cls="", style=""):
    return (f'<svg class="ico {cls}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" style="{style}" aria-hidden="true">{I[name]}</svg>')

# ---------------------------------------------------------------- generated covers
ALBUMS = {
 # key: (title, artist, year, hue1, hue2, style)
 "eden": ("Spirit of Eden", "Talk Talk", 1988, 150, 40, "rings"),
 "laughing": ("Laughing Stock", "Talk Talk", 1991, 28, 200, "tree"),
 "hex": ("Hex", "Bark Psychosis", 1994, 215, 280, "city"),
 "loveless": ("Loveless", "My Bloody Valentine", 1991, 335, 300, "blur"),
 "souvlaki": ("Souvlaki", "Slowdive", 1993, 20, 350, "sun"),
 "heaven": ("Heaven or Las Vegas", "Cocteau Twins", 1990, 300, 20, "blur"),
 "hats": ("Hats", "The Blue Nile", 1989, 222, 40, "city"),
 "dots": ("Dots and Loops", "Stereolab", 1997, 48, 12, "dots"),
 "mhtrtc": ("Music Has the Right to Children", "Boards of Canada", 1998, 172, 190, "split"),
 "tender": ("Tender Buttons", "Broadcast", 2005, 0, 0, "mono"),
 "satchi": ("Journey in Satchidananda", "Alice Coltrane", 1971, 32, 350, "sun"),
 "karma": ("Karma", "Pharoah Sanders", 1969, 16, 50, "rings"),
 "future": ("Future Days", "Can", 1973, 200, 48, "split"),
 "neu75": ("Neu! 75", "Neu!", 1975, 0, 0, "neu"),
 "hope": ("I Could Live in Hope", "Low", 1994, 30, 30, "mono2"),
 "deer": ("Dragging a Dead Deer Up a Hill", "Grouper", 2008, 95, 60, "blur"),
 "third": ("Third", "Portishead", 2008, 190, 170, "three"),
 "tnt": ("TNT", "Tortoise", 1998, 8, 44, "dots"),
 "hollis": ("Mark Hollis", "Mark Hollis", 1998, 40, 40, "mono2"),
 "beehive": ("Secrets of the Beehive", "David Sylvian", 1987, 36, 20, "tree"),
 "tindrum": ("Tin Drum", "Japan", 1981, 8, 40, "split"),
 "echo": ("World of Echo", "Arthur Russell", 1986, 205, 260, "rings"),
 "colour": ("The Colour of Spring", "Talk Talk", 1986, 110, 55, "dots"),
 "pygmalion": ("Pygmalion", "Slowdive", 1995, 250, 200, "blur"),
 "rustin": ("Out of Season", "Beth Gibbons & Rustin Man", 2002, 28, 100, "tree"),
 "orang": ("Herd of Instinct", ".O.rang", 1994, 130, 30, "split"),
 "rocknroll": ("Rock Bottom", "Robert Wyatt", 1974, 190, 40, "sun"),
 "treasure": ("Treasure", "Cocteau Twins", 1984, 280, 320, "rings"),
}

def cover_bg(key):
    t, a, y, h1, h2, st = ALBUMS[key]
    c = lambda h, s, l: f"hsl({h} {s}% {l}%)"
    if st == "rings":
        return f"radial-gradient(circle at 50% 55%, {c(h2,70,62)} 0 12%, {c(h1,45,30)} 12% 26%, {c(h2,60,52)} 26% 34%, {c(h1,50,22)} 34% 52%, {c(h1,40,34)} 52% 60%, {c(h1,55,16)} 60%)"
    if st == "tree":
        return f"radial-gradient(ellipse at 50% 30%, {c(h1,65,58)} 0 30%, transparent 31%), linear-gradient(90deg, transparent 47%, {c(h1,40,18)} 47% 53%, transparent 53%), linear-gradient(180deg, {c(h2,30,88)} 0 78%, {c(h1,35,30)} 78%)"
    if st == "city":
        return f"linear-gradient(0deg, {c(h1,60,10)} 0 22%, transparent 22%), repeating-linear-gradient(90deg, {c(h1,55,16)} 0 9%, {c(h1,50,24)} 9% 14%, {c(h1,60,12)} 14% 26%), linear-gradient(180deg, {c(h2,60,40)}, {c(h1,70,22)})"
    if st == "blur":
        return f"radial-gradient(circle at 30% 30%, {c(h1,85,62)} 0, transparent 55%), radial-gradient(circle at 75% 70%, {c(h2,80,45)} 0, transparent 60%), linear-gradient(135deg, {c(h1,70,38)}, {c(h2,60,24)})"
    if st == "sun":
        return f"radial-gradient(circle at 50% 62%, {c(h1,90,60)} 0 24%, transparent 25%), linear-gradient(180deg, {c(h2,60,30)} 0, {c(h1,80,45)} 62%, {c(h2,50,16)} 62%)"
    if st == "dots":
        return f"radial-gradient(circle at 25% 25%, {c(h2,85,55)} 0 14%, transparent 15%), radial-gradient(circle at 75% 25%, {c(h1,30,96)} 0 14%, transparent 15%), radial-gradient(circle at 25% 75%, {c(h1,30,96)} 0 14%, transparent 15%), radial-gradient(circle at 75% 75%, {c(h2,85,55)} 0 14%, transparent 15%), {c(h1,85,52)}"
    if st == "split":
        return f"linear-gradient(135deg, {c(h1,60,42)} 0 50%, {c(h2,75,58)} 50%)"
    if st == "mono":
        return "repeating-linear-gradient(45deg, #1b1b1b 0 6%, #f1efe9 6% 12%)"
    if st == "mono2":
        return f"radial-gradient(circle at 50% 42%, {c(h1,18,70)} 0 20%, transparent 21%), linear-gradient(180deg, {c(h1,12,22)}, {c(h1,10,10)})"
    if st == "neu":
        return "linear-gradient(0deg, transparent 38%, #f04a23 38% 62%, transparent 62%), #f4f1e8"
    if st == "three":
        return f"radial-gradient(circle at 50% 50%, transparent 0 22%, {c(h1,50,60)} 22% 30%, transparent 30%), {c(h1,45,14)}"
    return c(h1, 50, 40)

def cover(key, size, radius=8, cls="", extra=""):
    t, a, *_ = ALBUMS[key]
    return f'<div class="cover {cls}" title="{t} — {a}" style="width:{size}px;height:{size}px;border-radius:{radius}px;background:{cover_bg(key)};{extra}"></div>'

def avatar_bg(name):
    h = int(hashlib.md5(name.encode()).hexdigest()[:4], 16) % 360
    return f"radial-gradient(circle at 50% 38%, hsl({h} 25% 78%) 0 19%, transparent 20%), radial-gradient(ellipse at 50% 100%, hsl({h} 25% 78%) 0 42%, transparent 43%), linear-gradient(160deg, hsl({h} 30% 46%), hsl({(h+40)%360} 35% 28%))"

# ---------------------------------------------------------------- chart helpers
def nice_path(points, smooth=False):
    if not smooth:
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
    d = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
    for i in range(1, len(points)):
        x0, y0 = points[i-1]; x1, y1 = points[i]
        mx = (x0 + x1) / 2
        d += f" C{mx:.1f},{y0:.1f} {mx:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"
    return d

def scale(vals, lo, hi, a, b):
    return [a + (v - lo) / (hi - lo) * (b - a) if hi != lo else a for v in vals]

GROWTH = [1012,1019,1027,1031,1044,1052,1058,1071,1077,1090,1096,1101,1113,1118,1131,1139,1147,1158,1166,1171,1183,1190,1204,1209,1221,1228,1236,1247,1253,1262,1267,1272,1284]
GROWTH_PREV = [880,884,890,899,905,911,918,926,931,940,948,955,960,968,974,981,987,992,996,1001,1004,1008,1012]
