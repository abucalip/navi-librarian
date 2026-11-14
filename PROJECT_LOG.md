## 2026-11-14 — macOS Home marquee H2 items 1 and 2: panels moved, Insights "Your collection" (PR pending)

- Plan: `docs/MACOS_HOME_MARQUEE_PLAN.md` slice H2, items 1 and 2 only (item 3, Server activity in Settings, and the rest of H2 were not asked for in this task; see below).
- New `macos/Sources/DiscairUI/Themes/Cupertino/CupertinoCollectionPanels.swift`: `CollectionOverTimePanel`, `OwnAndPlayByDecadePanel`, `TastePanel`, `ShelfLifePanel` and `ServerActivityPanel`, moved out of `CupertinoHome.swift` with their helpers and `@State`. Draws the same as before, except Shelf life no longer shows its four small "Longest since a play" covers (they become "Waiting longest" in H3); `longestCovers` deleted.
- `CupertinoInsights`: new "Your collection" section above "Lenses" (collection 2:1 decades, taste 1:1 shelf life; one column under 860 wide); `.task` calls `state.refreshHomeDashboard()`.
- Home still shows the panels through the new views.
- **Beyond items 1 and 2:** `ServerActivityPanel` also appears as the last section of Settings, Services, with a `.task` that refreshes the dashboard and insights, because item 1 moves that panel and its rows need those figures. This is plan item 3; the owner asked for items 1 and 2 only, so tell me if this should come out of this PR.
- Tests: added `rendersInsightsYourCollection` (wide and stacked) and `rendersServicesWithServerActivity`. Filtered run on a Mac: `swift test --filter "HomeRenderTests|CupertinoPagesRenderTests|ConnectionsServicesRenderTests"`, 32 tests in 3 suites, passing. Full suite not run (owner rule). Not published or deployed.
- **Next action:** H2 items 4 and 5 review, then H3 (the new Home).

