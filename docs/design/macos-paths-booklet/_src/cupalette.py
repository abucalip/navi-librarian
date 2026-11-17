"""A line-for-line Python port of `CUPalette` (macos/Sources/DiscairUI/Themes/Cupertino/CupertinoPalette.swift).

Used by build.py (to write the Day and Night CSS the mockups draw with) and by check_contrast.py (to sweep accent hues).
If CupertinoPalette.swift changes, change this file with it. Design tooling only: nothing in the app or the tests imports it.
"""


def rgb(hexv):
    return ((hexv >> 16) & 0xFF) / 255, ((hexv >> 8) & 0xFF) / 255, (hexv & 0xFF) / 255


def luminance(hexv):
    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb(hexv)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mixed(a, b, amount):
    """`amount` of b over a, per channel, rounded (CURGB.mixed)."""
    out = 0
    for shift in (16, 8, 0):
        x, y = (a >> shift) & 0xFF, (b >> shift) & 0xFF
        out |= int(round(x + (y - x) * amount)) << shift
    return out


def over(fg, bg, alpha):
    """fg at `alpha` opacity composited over bg (what an `.opacity()` fill shows)."""
    return mixed(bg, fg, alpha)


def from_hsb(hue, s, v):
    h = ((hue % 360) + 360) % 360 / 60
    s, v = min(max(s, 0), 1), min(max(v, 0), 1)
    c = v * s
    x = c * (1 - abs(h % 2 - 1))
    m = v - c
    i = int(h)
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c)][i] if i < 5 else (c, 0, x)

    def byte(d):
        return int(round(min(max(d + m, 0), 1) * 255))
    return byte(r) << 16 | byte(g) << 8 | byte(b)


def hsb(hexv):
    r, g, b = rgb(hexv)
    hi, lo = max(r, g, b), min(r, g, b)
    d = hi - lo
    h = 0.0
    if d > 0:
        if hi == r:
            h = (g - b) / d
        elif hi == g:
            h = 2 + (b - r) / d
        else:
            h = 4 + (r - g) / d
        h = (h * 60 + 360) % 360
    return h, (0 if hi == 0 else d / hi), hi


DAY = dict(
    content=0xFFFFFF, panel=0xF5F5F7, fill=0xECECF0, fillOnPanel=0xE6E6EB,
    text=0x1D1D1F, textSecondary=0x636368, textTertiary=0x8E8E93,
    separator=0xE5E5EA, separatorStrong=0xD1D1D6,
    accent=0xD61F4A, accentStrong=0xC8163F, accentTint=0xFCE8EC, onAccent=0xFFFFFF,
    success=0x187A48, successTint=0xE6F4EC, warning=0x8A5200, warningTint=0xFFF4DC,
    danger=0xB3261E, dangerTint=0xFBEAE8, info=0x0B5CAD, infoTint=0xE8F1FB,
)
DAY_ACCENT = 0xD61F4A
NIGHT_ACCENT = 0xFF7A8F


def day_accent(hue, panel, content):
    if hue is None:
        return DAY_ACCENT, 0xC8163F, 0xFCE8EC
    _, s, b = hsb(DAY_ACCENT)
    accent = from_hsb(hue, s, b)
    while contrast(accent, panel) < 4.7 and b > 0.25:
        b -= 0.02
        accent = from_hsb(hue, s, b)
    tint = mixed(content, accent, 0.10)
    sb = b * 0.94
    strong = from_hsb(hue, s, sb)
    while contrast(strong, tint) < 4.6 and sb > 0.2:
        sb -= 0.02
        strong = from_hsb(hue, s, sb)
    return accent, strong, tint


def night_accent(hue, panel):
    h0, s, _ = hsb(NIGHT_ACCENT)
    h = h0 if hue is None else hue
    accent = NIGHT_ACCENT if hue is None else from_hsb(h, s, 1)
    while contrast(accent, panel) < 4.8 and s > 0.05:
        s -= 0.02
        accent = from_hsb(h, s, 1)
    tint = mixed(panel, accent, 0.20)
    ss = s * 0.9
    strong = from_hsb(h, ss, 1)
    while contrast(strong, tint) < 4.6 and ss > 0.02:
        ss -= 0.02
        strong = from_hsb(h, ss, 1)
    return accent, strong, tint


def night_base():
    content, panel, fill = 0x0B0B0D, 0x151518, 0x202025
    accent, strong, tint = night_accent(None, panel)
    return dict(
        content=content, panel=panel, fill=fill, fillOnPanel=0x26262B,
        text=0xF2F2F4, textSecondary=0x9E9EA7, textTertiary=0x6E6E78,
        separator=0x27272C, separatorStrong=0x3A3A41,
        accent=accent, accentStrong=strong, accentTint=tint, onAccent=content,
        success=0x47C285, successTint=mixed(panel, 0x47C285, 0.16),
        warning=0xF2B04A, warningTint=mixed(panel, 0xF2B04A, 0.16),
        danger=0xFF7B72, dangerTint=mixed(panel, 0xFF7B72, 0.16),
        info=0x6CB4FF, infoTint=mixed(panel, 0x6CB4FF, 0.16),
    )


def make(mode, hue=None):
    """CUPalette.make(mode, accentHue:). mode is "day" or "night"."""
    p = dict(DAY) if mode == "day" else night_base()
    if hue is None:
        return p
    if mode == "night":
        a = night_accent(hue, p["panel"])
    else:
        a = day_accent(hue, p["panel"], p["content"])
    p["accent"], p["accentStrong"], p["accentTint"] = a
    return p


def hexs(v):
    return "#%06X" % v
