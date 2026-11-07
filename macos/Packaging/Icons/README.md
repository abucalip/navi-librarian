# App and Dock icons

One icon per theme (see `macos/DESIGN.md`). Both are built from the Discair wordmark: black "Di", yellow dot, a mint-to-sky gradient and one large, faint, blurred ring.

| Theme | Files | Look |
|---|---|---|
| Cupertino | `Discair-Cupertino.*` | The base icon, nothing added. |
| Zine Spread | `Discair-Zine.*` | The base icon plus a yellow ticker band with ink rules, like the pipeline ticker. |

`.svg` is the source (1024 x 1024, tile inset to 824 as macOS expects), `.png` is the 1024 render with transparent corners, `.icns` is the full set for the bundle.

Not wired yet: the bundle has no `CFBundleIconFile` and the app does not switch its Dock icon with the theme. That is a follow-up.
