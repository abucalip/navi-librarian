# macOS Paths and Booklet design package

This is the design system for the Mac client's redesigned **Paths sheet** (album and artist) and **Booklet sheet**. It comes from the mockups the owner was shown in an earlier session, and those mockups are redrawn here with every state. The spec and the build plan are in [`docs/MACOS_PATHS_BOOKLET.md`](../../MACOS_PATHS_BOOKLET.md). This folder holds the files that document refers to.

| Path | What it is |
|---|---|
| [`tokens.json`](tokens.json) | The single source of the design. It holds:<ul><li>every Paths colour, mapped to a `CU` role, with the mockup value and whether the role is an exact match, a substitute or a derived value</li><li>the Booklet's fixed dark colours</li><li>the type table, mapped to `CU.Font` roles</li><li>spacing, snapped to `CU.Space`, with the named exceptions</li><li>sizes, radii, shadows and motion</li><li>the SF Symbols table</li><li>the contrast pairs</li></ul> |
| [`tokens.css`](tokens.css) | Generated from `tokens.json`. It holds `--pb-*` (the Paths roles in Day and Night, default accent), `--bk-*` (the Booklet) and the `.t-*` type roles. |
| [`components.css`](components.css) | Every component's measurements, for both sheets and all their states. Read sizes from here when the spec is silent. |
| [`art.css`](art.css) | Stand-in covers, artist photos and booklet pages for the mockups only. It is not app design. |
| [`pages/mockups.html`](pages/mockups.html) | Every state, drawn from sample data by [`pages/mockups.js`](pages/mockups.js). Open it in a browser; it needs no network. A Day/Night switch is at the top. `?only=<state>` draws one state. |
| [`pages/png/`](pages/png/) | One PNG per state (19), for looking at without a browser. |
| [`swift/CUPathsBooklet.swift`](swift/CUPathsBooklet.swift) | Generated. It holds the sizes and roles as `CU.PathsSheet` and `CU.Booklet`. Slices P1 and B1 copy it into `macos/Sources/DiscairUI/Themes/Cupertino/`. It is not compiled from here. |
| [`_src/cupalette.py`](_src/cupalette.py) | A Python port of `CUPalette` (Day, Night, accent hue). The two scripts below use it. |
| [`_src/build.py`](_src/build.py) | Writes `tokens.css` and the Swift file, and renders the PNGs with Google Chrome. |
| [`_src/check_contrast.py`](_src/check_contrast.py) | Checks every contrast pair in Day and Night, for the default accent and for 72 accent hues. |

```sh
python3 docs/design/macos-paths-booklet/_src/check_contrast.py   # all pass, exit 0
python3 docs/design/macos-paths-booklet/_src/build.py            # tokens.css, Swift, all PNGs; or: build.py paths / --no-png
```

## Rules for the implementing agent

- **In Swift, use the `CU` roles and `CU.Space`, never the hex values or pixel values of the CSS.** The CSS shows Day and Night with the default accent only. The owner can change the accent hue, and the roles follow it.
- **Fonts are system only (SF Pro through `.system`). No font files ship.** Georgia appears only inside the drawn stand-in booklet pages. In the app, the pages are the booklet images.
- **Icons are SF Symbols, named in `tokens.json` → `icons`.** No SVGs ship, because the SF Symbols licence does not allow copying the glyphs. The mockups use text glyphs (✕ ↓ ○ ✓ ‹ ›) as stand-ins.
- **The Booklet is always dark.** Its colours are fixed (`CU.Booklet`). Its accent is the **Night** accent of the owner's accent setting (`stageAccent`), because the Day accent falls to 1.9:1 on the dark ground for some hues.
- **The pictures are placeholders.** Names, counts and sentences are sample data. On the album sheet, the wording comes from the existing model code (`PathStory`, `AlbumPathTab.summary`, `PathAnswer` notes). The detail-bar sentences on the artist sheet and on Sonic are samples: the app shows the server's reason text there (spec, section 9, item 12). The only new wording is two role lines on the artist sheet (spec, section 4.2).
- Where the mockups and the spec differ, the spec's section 9 (corrections) wins; otherwise the mockups win.
