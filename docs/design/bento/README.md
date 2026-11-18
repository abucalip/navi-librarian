# Bento design package

The design system for the Android **Bento** theme. The spec is [`docs/plans/BENTO_THEME.md`](../../plans/BENTO_THEME.md); this folder holds everything it refers to.

| Path | What it is |
|---|---|
| [`tokens.json`](tokens.json) | The single source for:<ul><li>colours: three palettes in `Palette` field names, plus `tones`;</li><li>the type scale, spacing and shapes;</li><li>shadows, icon sizes and motion values.</li></ul> |
| [`palettes.css`](palettes.css) | Generated from `tokens.json`: one block of CSS variables per palette (`data-p="<id>"`) |
| [`bento.css`](bento.css) | Every component's measurements in dp (1 CSS px = 1dp) |
| [`pages/`](pages/) | The mockups: `.html` to open and measure, `.png` to look at. Drawn in Sorbet, except `palettes`. `motion.html` is live (no PNG) |
| [`icons/`](icons/) | 48 SVG icons (24 grid, 1.8 stroke, round) and `BentoIcons.kt.txt`, a ready Kotlin object |
| [`fonts/`](fonts/) | `gabarito_bento.ttf` and `figtree_bento.ttf` (Latin subsets), with their OFL licences |
| [`_src/build.py`](_src/build.py) | Writes `palettes.css`, the icons and every page, and renders the PNGs with Google Chrome |
| [`_src/check_contrast.py`](_src/check_contrast.py) | Checks all three palettes against the `PaletteTest` rules plus Bento's tones |
| [`../_kit/`](../_kit/) | Shared with Index:<ul><li>`kit.py`: sample data, the icon paths, contrast maths, the page wrapper and the PNG render;</li><li>`art.css`: generated stand-in covers and photos, not for the app.</li></ul> |

```sh
python3 docs/design/bento/_src/check_contrast.py   # all palettes pass, exit 0
python3 docs/design/bento/_src/build.py            # every page; or: build.py home paths
```

The PNGs need Google Chrome at `/Applications/Google Chrome.app`; without it, the HTML is still written.

## The other palettes

Mockups are drawn only in Sorbet. Licorice and Riviera are values in `tokens.json`, and any page shows them when the frame (or `<html>`) carries `data-p="bento_licorice"` or `data-p="bento_riviera"`. `pages/palettes` does this for Home. To check one page in another palette, add the attribute in a browser's inspector.

## Fonts

Both files are under the SIL Open Font License 1.1 (licence texts in `fonts/`). They were made from the Google Fonts variable sources with fontTools 4:

```python
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset
f = instancer.instantiateVariableFont(TTFont("Gabarito[wght].ttf"), {"wght": (500, 900)})
f.save("tmp.ttf"); f = TTFont("tmp.ttf")          # save and reopen before subsetting
o = subset.Options(); o.layout_features = ["kern", "liga", "calt", "tnum", "pnum", "lnum", "case", "frac"]; o.name_IDs = ["*"]; o.drop_tables += ["meta"]
s = subset.Subsetter(o)
s.populate(unicodes=list(range(0x20, 0x7F)) + list(range(0xA0, 0x180)) + [0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026, 0x2190, 0x2192, 0x2212])
s.subset(f); f.save("gabarito_bento.ttf")
# Figtree[wght].ttf the same way with {"wght": (400, 800)} -> figtree_bento.ttf
```
