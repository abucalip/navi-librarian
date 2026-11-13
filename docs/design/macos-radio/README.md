# macOS radio mockups (stage 2)

The spec for internet radio in the Mac client. The build steps are in
[`../../RADIO_PLAYBACK_PROPOSAL.md`](../../RADIO_PLAYBACK_PROPOSAL.md), "Stage 2 detailed plan".

Owner's choices (2026-11-13): **A2 · B2 · C1 · D2 · E1 E5 E7**. The page opens on them and marks them "chosen". The
other options are kept for the record and are not built.

| File | What it is |
|---|---|
| `mockups.html` | Open in a browser. No network needed. Day and Night switch at the top. |
| `cupertino-radio.css` | The app as drawn: Cupertino Day and Night colour roles (copied from `CUPalette`) and every radio component (station row, On Air panel, Download button states, LIVE badge, player bar, level meter, session tape, Now Playing, menu bar popover, mini player, Home card, tag sheet, menus). |
| `mockups.css` | The page around the mockups (notes, option pills, the picks bar). Not app design. |
| `mockups.js` | Sample stations and songs, and the code that draws each option and state. |

Station names, songs and times are invented samples. The coloured logo tiles and the purple washes stand in for the
server's logos and for blurred artwork; do not copy them.
