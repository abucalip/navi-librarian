# Index design package

The design system for the Android **Index** theme. The spec is [`docs/INDEX_THEME.md`](../../INDEX_THEME.md); this folder holds everything it refers to.

| Path | What it is |
|---|---|
| [`tokens.json`](tokens.json) | The single source for:<ul><li>colours: four palettes in `Palette` field names, plus `tones`;</li><li>the type scale, spacing and shapes;</li><li>icon sizes and motion values.</li></ul> |
| [`palettes.css`](palettes.css) | Generated from `tokens.json`: one block of CSS variables per palette (`data-p="<id>"`) |
| [`index.css`](index.css) | Every component's measurements in dp (1 CSS px = 1dp). It loads the app's own font files from `android/app/src/main/res/font/` |
| [`pages/`](pages/) | The mockups: `.html` to open and measure, `.png` to look at. Drawn in Signal Blue, except `palettes`. `motion.html` is live (no PNG) |
| [`icons/`](icons/) | 49 SVG icons (24 grid, 2 stroke, square caps, mitred) and `IndexIcons.kt.txt`, a ready Kotlin object |
| [`_src/build.py`](_src/build.py) | Writes `palettes.css`, the icons and every page, and renders the PNGs with Google Chrome |
| [`_src/check_contrast.py`](_src/check_contrast.py) | Checks all four palettes against the `PaletteTest` rules plus Index's tones |
| [`../_kit/`](../_kit/) | Shared with Bento: sample data, the icon paths, contrast maths, the page wrapper, and the stand-in artwork (`art.css`, not for the app) |

```sh
python3 docs/design/index/_src/check_contrast.py   # all palettes pass, exit 0
python3 docs/design/index/_src/build.py            # every page; or: build.py home paths
```

## The other palettes

Mockups are drawn only in Signal Blue. Newsprint Red, Graphite Orange and Field Green are values in `tokens.json`, and any page shows them when the frame (or `<html>`) carries `data-p="index_newsprint"`, `"index_graphite"` or `"index_field"`. `pages/palettes` does this for Home.

## Fonts

None to add. Inter Tight 800, Inter (variable) and IBM Plex Mono 400/500/600 are already in `android/app/src/main/res/font/`, and the mockups load those files.
