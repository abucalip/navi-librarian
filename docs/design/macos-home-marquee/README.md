# macOS Home mockups, "Marquee" layout

The spec for the artwork-led Home of the Mac client. The owner chose it on 2026-11-13. The build steps are in
[`../../MACOS_HOME_MARQUEE_PLAN.md`](../../MACOS_HOME_MARQUEE_PLAN.md).

| File | What it is |
|---|---|
| `mockups.html` | Open in a browser. No network needed. Day and Night switch at the top. Shows every state: default, shelf tile kinds, notice, no pick, first run, Librarian unreachable, loading, narrow. |
| `home-marquee.css` | The app as drawn: Cupertino Day and Night colour roles (copied from `CUPalette`) and every Home component (marquee, next picks, shelf tile and its overlays, summary line, notice, empty marquee, skeleton, narrow layout). Take sizes and spacing from here. |
| `mockups.js` | The code that draws each state from sample data. Shows which tiles and sentences each state holds. |
| `covers.js` | Sample albums, the drawn stand-in covers, and the window frame (sidebar, title, player bar). Not app design. |
| `mockups.css` | The page around the mockups (titles, captions, the mode switch). Not app design. |
| `not-chosen.html`, `not-chosen.css`, `not-chosen.js` | The two layouts offered at the same time and not chosen (Cover Wall, Covers as Charts). Kept for the record; not built. |

Album names, artists, years and figures are invented samples. The drawn covers stand in for real artwork; do not copy
them. In Swift use the `CU` roles and `CU.Space`, never the hex values or pixel values of the CSS.
