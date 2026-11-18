# Listening Room design package

The design system for the web client's **Listening Room** redesign. The spec and build plan are in [`docs/plans/LISTENING_ROOM_WEB.md`](../../plans/LISTENING_ROOM_WEB.md); this folder is what that document refers to.

| Path | What it is |
|---|---|
| [`tokens.json`](tokens.json) | Single source: colours, hero tint rule, fonts, type, spacing, radii, sizes, breakpoints, shadows, motion, contrast pairs |
| [`tokens.css`](tokens.css) | Generated from `tokens.json`: `@font-face`, `--lr-*` variables, `.lr-type-*` classes |
| [`components.css`](components.css) | Every component's measurements, with the tablet and phone layouts |
| [`art.css`](art.css) | Stand-in covers and artist photos for the mockups only; not for the app |
| [`pages/`](pages/) | `home`, `reasons`, `states`, and every other web page (plan section 8): `.html` to open and measure, `.png` (1440) and `-phone.png` (390) to look at. The page list is plan section 12 |
| [`icons/`](icons/) | 52 SVG icons (24 grid, 1.75 stroke) and the sprite `icons.svg` (`#lr-<name>`) |
| [`fonts/`](fonts/) | Instrument Sans 600 and 700, Latin woff2 from Google Fonts, and the OFL licence. Inter 400/600 are already in `static/fonts/` |
| [`_src/pages.py`](_src/pages.py) | Writes the page mockups beyond Home, reasons and states from shared parts, so the shell, the reason panel and the rows are identical on every page |
| [`_src/build.py`](_src/build.py) | Writes `tokens.css` and the icons, runs `pages.py`, puts the sprite into each page, and renders PNGs with Google Chrome |
| [`_src/check_contrast.py`](_src/check_contrast.py) | Checks every contrast pair, and the hero tint over 1,301 cover colours |

```sh
python3 docs/design/listening-room/_src/check_contrast.py   # all pass, exit 0
python3 docs/design/listening-room/_src/build.py            # everything; or: build.py album
```

Phone PNGs are drawn in a 390px iframe inside a 600px window, because headless Chrome will not open a narrower window, and then cropped with `sips` (macOS).

Each page's PNG height is measured from the page itself (an iframe read with `--allow-file-access-from-files`), so no height is hard-coded. There is no Paths page: Paths is exclusive to the Android and macOS clients.
