# Mockup generator

These scripts wrote every HTML mockup under `docs/design/redesign/` and rendered the PNG beside it. They are design tooling, not application code: nothing imports them and no test collects them.

- `common.py`: icons, generated album covers, sample data.
- `mac_shell.py`: the Cupertino window shell and the SVG chart functions (`chart_line`, `chart_cols`, `chart_pairs`, `chart_dumbbell`, `chart_heat`, `stage_track`). The chart functions hold the exact geometry the chart rules describe.
- `mac_home.py`, `mac_conn.py`, `mac_more.py`: the macOS pages.
- `android.py`: the Android pages (Day · Sand).
- `build.py`: `python3 build.py mac [name ...]` or `python3 build.py android [name ...]`. Needs Google Chrome at its default macOS path for the PNGs; the HTML is written either way.

The design tokens live in the two stylesheets, not here: `../macos/cupertino/cupertino.css` and `../android/android.css`.
