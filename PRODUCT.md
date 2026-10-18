# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
A single owner who self-hosts Navidrome (their music library) and slskd (Soulseek downloads) at home. Desktop-first, with occasional use from a phone on the same network. The job: understand what is already in the library, find music worth adding (new releases, missing albums by artists they already own, classics, taste-based picks), request an acquisition with confidence, and check on its progress. Household or multi-user use is not a requirement.

## Product Purpose
Navidrome Librarian is a web UI for discovering music and managing acquisitions on top of an existing Navidrome library and slskd. Success is a collector who can go from "what should I add next?" to a confirmed, tracked request in a few deliberate steps, without second-guessing whether the request landed or whether a destructive action touched the right files.

## Positioning
Librarian is an acquisition-aware discovery tool, not a player. It knows the user's library and listening history, so it recommends what is missing rather than what is popular, and it closes the loop through slskd. Streaming apps cannot truthfully copy "request this album into my own library and watch it arrive".

## Operating Context
- FastAPI app serving a single-page shell: `app/templates/index.html`, `static/app.css`, `static/app.js`. No framework, no build system.
- Pages today: Dashboard ("Ten from the collection"), Discover music (recommendations), New releases, Personal Discoveries, Add to your collection (classics), Artist Deep Dives (grouped by genre, one album per artist), Acquisition status, Settings (Navidrome, slskd, Last.fm, ListenBrainz, quality tiers). An album detail modal shows tracklist and platform links.
- External services: Navidrome, slskd, Last.fm, ListenBrainz, MusicBrainz. Artwork is the dominant content.
- The Get/request flow, Dismiss, and import are enforced server-side; the browser never duplicates that logic or reports success before the server confirms.
- Testing uses an isolated local helper with sandbox music paths and slskd disabled (`docs/LOCAL_UI_TESTING.md`).

## Capabilities and Constraints
- The existing API is authoritative. No endpoint or field may be invented; needs are written up as contract proposals.
- No playback exists. Reference mockups show a player bar; the owner's decision is to borrow the visual language only. A now-playing or streaming bar is out of scope unless separately approved with an API contract.
- Fonts currently load from Google Fonts via `@import`; self-hosting is an open decision.
- Acquisition information (quality, progress, status, actions) must stay coherent and scannable.
- The repository's UI restrictions in `AGENTS.md` and `docs/FRONTEND_DESIGN_GUIDE.md` are to be rewritten by the owner to permit the redesign. Until then the roadmap treats them as superseded for planning only.

## Brand Commitments
Name: Navidrome Librarian. Existing cassette mark at `assets/cassette.png`. The current yellow/red accents and the Barlow Condensed / IBM Plex trio are starting points, not commitments: the owner has opened color, type, icons and motion to exploration.

## Evidence on Hand
- Four owner-supplied reference mockups (dark music apps: red-orange hero with green accents; blue-accent artwork rows; yellow-on-charcoal with a hero banner; orange-accent mobile screens with a lyrics/playlist view).
- A shipped, audited front end with measured contrast and accessibility history in `docs/UI_BACKLOG_EXECUTION.md`.
- No user research, analytics, or testimonials exist. None may be fabricated.

## Product Principles
1. Artwork leads; metadata supports.
2. Every state is honest: pending, confirmed, failed, and recoverable are visibly different, and never by color alone.
3. Each task gets its own composition (exploring, acquiring, monitoring, configuring) inside one shared design language.
4. Earn every flourish: motion, icons and color must carry meaning.
5. Accessibility is a floor, not a pass at the end.

## Accessibility & Inclusion
WCAG 2.1 AA minimum, 44x44 touch targets, visible focus, keyboard-operable everything, `prefers-reduced-motion` respected, status never by color alone. Chromium-only manual testing so far; no screen-reader testing recorded.
