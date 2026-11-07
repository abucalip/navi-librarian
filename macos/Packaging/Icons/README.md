# App and Dock icons

One icon per theme (see `macos/DESIGN.md`). Both are built from the Discair wordmark: black Discair wordmark, yellow dots, a mint-to-sky gradient and one large, faint, blurred ring.

| Theme | Files | Look |
|---|---|---|
| Cupertino | `Discair-Cupertino.*` | The base icon, nothing added. |
| Zine Spread | `Discair-Zine.*` | The base icon plus a yellow ticker band with ink rules, like the pipeline ticker. |

`.svg` is the source (1024 x 1024, tile inset to 824 as macOS expects), `.png` is the 1024 render with transparent corners, `.icns` is the full set for the bundle.

Wired: `bundle.sh` copies them into the app, `Info.plist` uses the Cupertino icon for Finder, and the app swaps the Dock icon when the theme changes (`AppIcon` in `DiscairApp.swift`). A bare `swift run` has no bundle, so it keeps the default icon.
