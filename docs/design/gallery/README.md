# Gallery design package

The design system for the Android **Gallery** theme. The spec is [`docs/GALLERY_THEME.md`](../../GALLERY_THEME.md); this folder is what it refers to.

| Path | What it is |
|---|---|
| [`tokens.json`](tokens.json) | Single source for colours (eight palettes, `Palette` field names), type scale, spacing, print mats and shadows, icon sizes and motion |
| [`palettes.css`](palettes.css) | Generated from `tokens.json`: one block of CSS variables per palette (`data-p="<id>"`) |
| [`gallery.css`](gallery.css) | Every component's measurements, in dp (1 CSS px = 1dp). The last block draws stand-in artwork and is not for the app |
| [`pages/`](pages/) | The mockups: `.html` to open and measure, `.png` to look at. Drawn in Day 1 except `palettes` |
| [`icons/`](icons/) | 46 SVG icons (24 grid, 1.4 stroke) and `GalleryIcons.kt.txt`, a ready Kotlin object |
| [`fonts/`](fonts/) | `fraunces_gallery.ttf`, `fraunces_gallery_italic.ttf`, `manrope_gallery.ttf` (Latin subsets) and their OFL licences |
| [`_src/build.py`](_src/build.py) | Writes `palettes.css`, the icons and every page; renders PNGs with Google Chrome |
| [`_src/check_contrast.py`](_src/check_contrast.py) | Checks all eight palettes against the `PaletteTest` rules plus the Gallery roles |

```sh
python3 docs/design/gallery/_src/check_contrast.py   # all palettes pass, exit 0
python3 docs/design/gallery/_src/build.py            # every page; or: build.py home player
```

## Fonts

All three files are under the SIL Open Font License 1.1 (licence texts in `fonts/`). They were made from the Google Fonts variable sources with fontTools:

```python
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset
f = instancer.instantiateVariableFont(TTFont("Fraunces[SOFT,WONK,opsz,wght].ttf"), {"SOFT": 0, "WONK": 0, "opsz": (9, 144), "wght": (300, 600)})
# save, reopen, then subset to U+0020-007E, U+00A0-017F and common punctuation, keeping kern, liga, onum, lnum, tnum, pnum, frac, case
```

The italic uses the same limits. Manrope keeps `wght` 400 to 800. DM Mono 400 and 500 are already in `android/app/src/main/res/font/`.
