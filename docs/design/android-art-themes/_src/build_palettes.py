"""
Builds the palette files of docs/palettes.md from the existing Soft Brut and Flow mockups:

  palettes/palettes.css      the colour tokens of every new palette (one class each), loaded after soft-brut.css / flow.css
  palettes/soft-brut.html    Home, Album and Now Playing in each new Soft Brut palette
  palettes/flow.html         the same three screens in each new Flow palette
  palettes/roles.md          the role tables and the Kotlin entries that docs/palettes.md quotes

Only colours change: the screens are cut from the existing mockup pages and the theme CSS files are not edited.
Run from docs/design/android-art-themes:  python3 _src/build_palettes.py
The script stops if a palette misses a contrast floor the unit tests hold the two themes to.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rd = lambda p: open(os.path.join(HERE, p), encoding="utf-8").read()

DAY_STATUS_SB = dict(ok="1B6B33", okDim="D9EEDD", caution="7F4A00", cautionDim="FBE9C4", danger="B3261E", dangerDim="F8D9D5", info="1D4FB8", infoDim="DCE5FB")
DAY_STATUS_FL = dict(ok="1B7339", okDim="DCEEDF", caution="8A5300", cautionDim="F8E8CC", danger="C0271A", dangerDim="F9DCD8", info="1F5FBF", infoDim="DCE7F8")
NIGHT_STATUS_SB = dict(ok="86D39B", okDim="1F3326", caution="F0A640", cautionDim="3D2E14", danger="FF8A80", dangerDim="40211A", info="8FB8E8", infoDim="1D2C3D")
NIGHT_STATUS_FL = dict(NIGHT_STATUS_SB, danger="FF7B62")

# Soft Brut: page surface raised outline edge-soft text muted accent accent-dim on-accent accent2 accent3 accent4 chart2
SB = [
    ("softbrut_mint", "SoftBrutMint", "Soft Brut · Mint", "day", "SD1", "F5F8F0 FFFFFF E6EDDD 17211C CFD8C6 17211C 55625A 9BE3C0 DDF5EA 17211C FFD9A8 C9BBFF FFD84D 7F8C84"),
    ("softbrut_peach", "SoftBrutPeach", "Soft Brut · Peach", "day", "SD2", "FFF6EE FFFFFF F7E6D6 261A15 E2CFBF 261A15 6B564C FFB59A FFE6DB 261A15 BFE3FF B9E8C2 FFD84D 94827A"),
    ("softbrut_sky", "SoftBrutSky", "Soft Brut · Sky", "day", "SD3", "F3F7FB FFFFFF E1EAF3 141C2B C9D4E0 141C2B 556073 A9CCFF E0ECFF 141C2B FFC9DE A6E9CB FFE066 808B9C"),
    ("softbrut_lemon", "SoftBrutLemon", "Soft Brut · Lemon", "day", "SD4", "FBF8E9 FFFFFF F0EBCF 1F1D12 D9D3B3 1F1D12 615C45 FFDF5C FFF4BF 1F1D12 C9BBFF A6E9CB FFB59A 8C876E"),
    ("softbrut_midnight_mint", "SoftBrutMidnightMint", "Soft Brut · Midnight Mint", "night", "SN2", "101714 18221D 223029 DDEFE3 31443A EFF8F1 A9C0B2 9BE3C0 1F4636 101714 FFD9A8 C9BBFF FFD84D 7E9487"),
    ("softbrut_plum_peach", "SoftBrutPlumPeach", "Soft Brut · Plum Peach", "night", "SN3", "1B1416 261C1F 35272B F6E4DC 4A383C FFF3EE CDB3AD FFB59A 55302A 1B1416 BFE3FF B9E8C2 FFD84D 9A827D"),
    ("softbrut_navy_sky", "SoftBrutNavySky", "Soft Brut · Navy Sky", "night", "SN4", "0F1520 17202F 212D42 DCE7F7 2F3D57 F0F5FF A7B5CC A9CCFF 24406B 0F1520 FFC9DE A6E9CB FFE066 7D8BA3"),
]
# Flow: page surface raised edge edge-strong text muted accent accent-dim on-accent chart2 chart3 chevron
FL = [
    ("flow_forest", "FlowForest", "Flow · Forest", "day", "FD2", "F8F9F4 FFFFFF E9EDE2 DBE0D2 7D8672 12150F 596051 1B7340 D9EEDF FFFFFF 87907C D0D6C6 AEB5A3"),
    ("flow_raspberry", "FlowRaspberry", "Flow · Raspberry", "day", "FD3", "FCF8F8 FFFFFF F1E8E9 E5DADB 8E7F82 171113 6A5C5F BE2260 FADCE6 FFFFFF 96878A DCCFD1 BBADB0"),
    ("flow_violet", "FlowViolet", "Flow · Violet", "day", "FD4", "F9F8FC FFFFFF ECEAF3 DEDBE8 827D93 13111A 5F5A6E 6A3BD2 E7DEFA FFFFFF 8A859B D3CFE0 B2AEC2"),
    ("flow_ember", "FlowEmber", "Flow · Ember", "night", "FN1", "12110F 1C1A17 2A2723 35312C 8A8377 F5F1EA A9A296 FF8A4C 4A2A17 1A0F08 8A8377 4A453E 6B655B"),
    ("flow_moss", "FlowMoss", "Flow · Moss", "night", "FN3", "0E1311 171E1A 232C27 2D3832 7A887F EEF5F0 9FAFA5 5FD28C 173D27 06170D 7A887F 3D4A43 5E6B63"),
    ("flow_plum", "FlowPlum", "Flow · Plum", "night", "FN4", "151015 1F181F 2D232D 3A2E3A 8C7C8C F7EEF5 B3A2B0 FF7FAE 4D1F33 2A0A17 8C7C8C 4C3D4C 6E5F6E"),
]
FLOW_WASH = {"day": "DFE6EA", "night": "27313A"}  # the mockup cover's wash; the app derives it from the artwork


def lum(h):
    v = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def cr(a, b):
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def rgba(h, a):
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


bad = []


def need(pid, what, a, b, floor):
    if cr(a, b) < floor:
        bad.append(f"{pid}: {what} #{a} on #{b} is {cr(a, b):.2f}, under {floor}")


def status_checks(pid, st, grounds):
    for bg in grounds:
        need(pid, "error text", st["danger"], bg, 4.5)
    for k, d in (("ok", "okDim"), ("caution", "cautionDim"), ("danger", "dangerDim"), ("info", "infoDim")):
        need(pid, k + " on its tint", st[k], st[d], 4.5)


css, md_sb, md_fl, kt = [], [], [], []
rows = {"sb": [], "fl": []}

for pid, kname, label, mode, pick, vals in SB:
    page, surf, raised, edge, esoft, text, muted, acc, dim, on, a2, a3, a4, c2 = vals.split()
    st = DAY_STATUS_SB if mode == "day" else NIGHT_STATUS_SB
    for bg in (page, surf, raised):
        need(pid, "text", text, bg, 4.5)
        need(pid, "muted", muted, bg, 4.5)
    need(pid, "text on the accent tint", text, dim, 4.5)
    for f in (acc, a2, a3, a4):
        need(pid, "on-accent", on, f, 4.5)
    need(pid, "chart2 on the surface", c2, surf, 3.0)
    status_checks(pid, st, (page, surf, raised))
    floor = int(min(cr(acc, page), cr(acc, surf)) * 10) / 10
    mac = min(floor, 3.0)
    css.append(
        f"/* {pick} {label} */\n.sb.p-{pid}{{--page:#{page};--rail:#{page};--surface:#{surf};--raised:#{raised};--edge:#{edge};--edge-soft:#{esoft};"
        f"--text:#{text};--muted:#{muted};--accent:#{acc};--accent-dim:#{dim};--on-accent:#{on};--accent2:#{a2};--accent3:#{a3};--accent4:#{a4};--shadow:#{edge};"
        f"--ok:#{st['ok']};--ok-dim:#{st['okDim']};--caution:#{st['caution']};--caution-dim:#{st['cautionDim']};--danger:#{st['danger']};--danger-dim:#{st['dangerDim']};"
        f"--info:#{st['info']};--info-dim:#{st['infoDim']};--chart1:#{acc};--chart2:#{c2};--chart3:#{surf};--chart-ghost:#{raised};--chart-grid:#{esoft};--chart-base:#{edge}}}")
    md_sb.append((pid, label, mode, pick, [page, surf, raised, edge, text, muted, acc, dim, on, a2, a3, a4, esoft, c2], mac))
    kt.append(
        f'    val {kname} = Palette(\n        "{pid}", "{label}", {"true" if mode == "day" else "false"},\n'
        f"        rail = c(0x{page}), ink = c(0x{page}), surface = c(0x{surf}), raised = c(0x{raised}), edge = c(0x{edge}), edgeStrong = c(0x{edge}),\n"
        f"        text = c(0x{text}), textMuted = c(0x{muted}), accent = c(0x{acc}), accentDim = c(0x{dim}), onAccent = c(0x{on}),\n"
        f"        chartRed = c(0x{st['danger']}), chartRedText = c(0x{st['danger']}), ok = c(0x{st['ok']}), caution = c(0x{st['caution']}),\n"
        f"        family = Family.Brutal, shape = BrutalShape(10f, 1.5f, 3f), shadowColor = c(0x{edge}),\n"
        f"        info = c(0x{st['info']}), okDim = c(0x{st['okDim']}), cautionDim = c(0x{st['cautionDim']}), dangerDim = c(0x{st['dangerDim']}), infoDim = c(0x{st['infoDim']}),\n"
        f"        chart1 = c(0x{acc}), chart2 = c(0x{c2}), chart3 = c(0x{surf}), chartGhost = c(0x{raised}), chartGrid = c(0x{esoft}),\n"
        f"        chartBase = c(0x{edge}),\n"
        f"        accent2 = c(0x{a2}), accent3 = c(0x{a3}), accent4 = c(0x{a4}), minAccentContrast = {mac},\n"
        f'        layout = Layout.CoverStack, suggestedFontId = "brut_modern",\n    )')
    rows["sb"].append((pid, label, pick, mode))

fl_extra = []
for pid, kname, label, mode, pick, vals in FL:
    page, surf, raised, edge, strong, text, muted, acc, dim, on, c2, c3, chev = vals.split()
    st = DAY_STATUS_FL if mode == "day" else NIGHT_STATUS_FL
    wash = FLOW_WASH[mode]
    for bg in (page, surf, raised, wash):
        need(pid, "text", text, bg, 4.5)
        need(pid, "muted", muted, bg, 4.5)
    for bg in (page, surf):
        need(pid, "accent as text", acc, bg, 4.5)
    need(pid, "label on the accent", on, acc, 4.5)
    need(pid, "text on the accent tint", text, dim, 4.5)
    need(pid, "strong edge on the page", strong, page, 3.0)
    need(pid, "chart2 on the surface", c2, surf, 3.0)
    status_checks(pid, st, (page, surf, raised))
    if mode == "day":
        hair, track, bar = "rgba(0,0,0,.08)", rgba(text, ".14"), "rgba(255,255,255,.86)"
        depth = f"--e1:0 4px 14px -10px {rgba(text, '.30')};--e2:0 6px 22px -8px {rgba(text, '.30')};--e3:0 22px 34px -18px {rgba(text, '.60')};"
    else:
        hair, track, bar = "rgba(255,255,255,.10)", rgba(text, ".18"), rgba(surf, ".86")
        depth = "--e1:0 4px 14px -10px rgba(0,0,0,.70);--e2:0 6px 22px -8px rgba(0,0,0,.80);--e3:0 22px 34px -18px rgba(0,0,0,.90);"
    css.append(
        f"/* {pick} {label} */\n.fl.p-{pid}{{--page:#{page};--rail:#{page};--surface:#{surf};--raised:#{raised};--edge:#{edge};--edge-strong:#{strong};"
        f"--text:#{text};--muted:#{muted};--accent:#{acc};--accent-dim:#{dim};--on-accent:#{on};"
        f"--ok:#{st['ok']};--ok-dim:#{st['okDim']};--caution:#{st['caution']};--caution-dim:#{st['cautionDim']};--danger:#{st['danger']};--danger-dim:#{st['dangerDim']};"
        f"--info:#{st['info']};--info-dim:#{st['infoDim']};--chart1:#{acc};--chart2:#{c2};--chart3:#{c3};--chart-ghost:#{raised};--chart-grid:#{edge};--chart-base:#{strong};"
        f"--bar:{bar};--hair:{hair};{depth}--track:{track};--chev:#{chev};--sw-off:#{c3};" + (f"--wash:#{wash}" if mode == "night" else "") + "}")
    md_fl.append((pid, label, mode, pick, [page, surf, raised, edge, strong, text, muted, acc, dim, on, c2, c3]))
    fl_extra.append((label, chev, c3, hair, track))
    kt.append(
        f'    val {kname} = Palette(\n        "{pid}", "{label}", {"true" if mode == "day" else "false"},\n'
        f"        rail = c(0x{page}), ink = c(0x{page}), surface = c(0x{surf}), raised = c(0x{raised}), edge = c(0x{edge}), edgeStrong = c(0x{strong}),\n"
        f"        text = c(0x{text}), textMuted = c(0x{muted}), accent = c(0x{acc}), accentDim = c(0x{dim}), onAccent = c(0x{on}),\n"
        f"        chartRed = c(0x{st['danger']}), chartRedText = c(0x{st['danger']}), ok = c(0x{st['ok']}), caution = c(0x{st['caution']}),\n"
        f"        info = c(0x{st['info']}), okDim = c(0x{st['okDim']}), cautionDim = c(0x{st['cautionDim']}), dangerDim = c(0x{st['dangerDim']}), infoDim = c(0x{st['infoDim']}),\n"
        f"        chart1 = c(0x{acc}), chart2 = c(0x{c2}), chart3 = c(0x{c3}), chartGhost = c(0x{raised}), chartGrid = c(0x{edge}),\n"
        f"        chartBase = c(0x{strong}),\n"
        f'        layout = Layout.Flow, suggestedFontId = "flow",\n    )')
    rows["fl"].append((pid, label, pick, mode))

if bad:
    print("\n".join(bad))
    sys.exit(1)

os.makedirs(os.path.join(HERE, "palettes"), exist_ok=True)
head = """/*
 * Colour palettes for Soft Brut and Flow (docs/palettes.md). Load after soft-brut.css and flow.css; add the palette's class to the
 * .phone element, for example class="phone sb p-softbrut_mint". Only colour tokens are set here. Built by _src/build_palettes.py.
 */

/* Flow draws three colours as literals in flow.css. They become tokens so a palette can set them; the fallbacks are the literals. */
.fl .chev{color:var(--chev,#B5B0A5)}
.fl .seek{background:var(--track,rgba(21,19,15,.14))}
.fl .sw{background:var(--sw-off,#D9D5CB)}

/* Soft Brut: whatever sits on a pastel fill takes the on-accent ink. By day that is the text colour, so nothing changes there. */
.sb .nav .on,.sb .cb.main,.sb .chip.on,.sb .tabs .on,.sb .tag,.sb .tile.radio,.sb .bdg,.sb .lyr p.on{color:var(--on-accent)}

"""
open(os.path.join(HERE, "palettes/palettes.css"), "w", encoding="utf-8").write(head + "\n".join(css) + "\n")


def phone(path, cls):
    g = re.findall(r'<div class="phone.*?</div></figure>', rd(path), flags=re.S)[0][: -len("</figure>")]
    return g.replace('<div class="phone ', f'<div class="phone {cls} ', 1)


symbols = re.search(r'<svg width="0".*?</svg>', rd("flow/home.html"), flags=re.S).group(0)
FONTS = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&family=Space+Grotesk:wght@700&display=swap"

for key, folder, theme_css, title, note in (
    ("sb", "soft-brut", "soft-brut.css", "Soft Brut · palettes",
     "At night the outline and the hard shadow are light, and whatever sits on a pastel fill keeps the dark on-accent ink."),
    ("fl", "flow", "flow.css", "Flow · palettes",
     "The accent is also text (links, the playing track). At night the wash behind the album and the player is a dark tone of the cover."),
):
    out = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>'
           f'<link rel="stylesheet" href="{FONTS}"><link rel="stylesheet" href="../shared.css"><link rel="stylesheet" href="../{theme_css}">'
           '<link rel="stylesheet" href="palettes.css"><style>.doc h2{font:700 18px/1.2 \'Space Grotesk\',system-ui,sans-serif;margin:34px 0 12px}</style></head><body>'
           f'{symbols}<div class="doc"><h1>{title}</h1><p>Android, 360 × 780 dp, 1 px = 1 dp. The three screens are the existing {folder} mockups; only the colour '
           f'tokens differ (palettes.css). {note} Covers and photos are drawn stand-ins. Spec: docs/palettes.md.</p></div>']
    for pid, label, pick, mode in rows[key]:
        out.append(f'<div class="doc"><h2>{pick} · {label} ({mode}) · <code>{pid}</code></h2></div><div class="frames">')
        for cap, page_ in (("Home", "home"), ("Album", "album-artist-genre"), ("Now Playing", "player")):
            out.append(f'<figure><figcaption>{label} · {cap}</figcaption>{phone(f"{folder}/{page_}.html", "p-" + pid)}</figure>')
        out.append("</div>")
    out.append("</body></html>\n")
    open(os.path.join(HERE, f"palettes/{folder}.html"), "w", encoding="utf-8").write("".join(out))

# ---- the tables docs/palettes.md quotes ----
m = ["### Soft Brut roles\n",
     "| Palette | id | Mode | page (`rail`, `ink`) | `surface` | `raised` | outline (`edge`, `edgeStrong`, `shadowColor`, `chartBase`) | `text` | `textMuted` | `accent` (`chart1`) | `accentDim` | `onAccent` | `accent2` | `accent3` | `accent4` | soft edge (`chartGrid`) | `chart2` | `minAccentContrast` |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for pid, label, mode, pick, v, mac in md_sb:
    m.append(f"| {pick} {label} | `{pid}` | {mode} | " + " | ".join(f"`#{x}`" for x in v) + f" | {mac} |")
m += ["", "### Flow roles\n",
      "| Palette | id | Mode | page (`rail`, `ink`) | `surface` | `raised` (`chartGhost`) | `edge` (`chartGrid`) | `edgeStrong` (`chartBase`) | `text` | `textMuted` | `accent` (`chart1`) | `accentDim` | `onAccent` | `chart2` | `chart3` |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for pid, label, mode, pick, v in md_fl:
    m.append(f"| {pick} {label} | `{pid}` | {mode} | " + " | ".join(f"`#{x}`" for x in v) + " |")
m += ["", "### Flow colours that are not Palette roles today\n",
      "| Palette | chevron | switch, off | hairline on bars | seek track |", "|---|---|---|---|---|"]
for label, chev, off, hair, track in fl_extra:
    m.append(f"| {label} | `#{chev}` | `#{off}` | `{hair}` | `{track}` |")
m += ["", "### Kotlin entries\n", "```kotlin", "\n\n".join(kt), "```", ""]
open(os.path.join(HERE, "palettes/roles.md"), "w", encoding="utf-8").write("\n".join(m))
print("built", len(SB) + len(FL), "palettes")
