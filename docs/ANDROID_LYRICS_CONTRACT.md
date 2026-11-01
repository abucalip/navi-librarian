# Android lyrics contract (Discair)

Status: **approved by the owner on 2026-11-01 (answers 1 to 4 in section 11); phases L1 to L3 are merged (PRs #668, #669, #670: data layer, timeline, screen) and are unit-tested only. Phase L4, the device run on the owner's phone (section 10), has started: on 2026-11-01 the owner confirmed the Lyrics tab works and timed lyrics follow the music. The rest of section 10 is unchecked and not claimed.** Answers 5 to 8 were not discussed: their proposed defaults stand until the owner overrides them before the phase they affect. This contract is the "lyrics" item that [`ANDROID_PLAYER_CONTRACT.md`](ANDROID_PLAYER_CONTRACT.md) section 6 left for its own contract (D-018). It goes through a PR, as the Android contracts do.

## 1. Purpose and scope

Show the lyrics of the song that is playing, on the owner's phone, inside the Now Playing sheet. Lyrics that carry timings follow the music; lyrics without timings are plain text.

In scope:
- A Lyrics view in the Now Playing sheet, beside the existing Player and Queue views.
- Timed lyrics: the current line is marked and kept in view as the song plays, and follows a seek.
- Plain lyrics: shown as text, with a line saying they are not timed.
- Honest states: loading, no lyrics, cannot reach Navidrome, login rejected.
- A small on-device cache so lyrics already fetched show again, and show offline.

Out of scope:
- The web UI. No Librarian change (D-016 is untouched).
- Any outside lyrics service or website. The only source is the owner's Navidrome.
- Editing, uploading or correcting lyrics; translation; karaoke effects.
- Lyrics on the mini-player, the notification or the lock screen.
- Radio.

## 2. What was measured on the owner's server

A read-only survey on 2026-11-01 from the owner's Mac over the local network (not from the phone over Tailscale), using one random sample. It reads song ids and lyrics structure only; no lyric text was kept.

| Fact | Result |
|---|---|
| Server | Navidrome 0.64.2 (OpenSubsonic) |
| Lyrics support | `getOpenSubsonicExtensions` lists `songLyrics` (also `transcoding`, `playbackReport`, `indexBasedQueue` and others, not used here) |
| Coverage, 24 random songs | 14 timed, 7 plain, 3 none |
| By format in that sample | mp3: 12 timed, 7 plain, 2 none; flac: 1 timed, 1 none; m4a: 1 timed. The sample is too small to say anything about m4a or flac. |
| Fields seen | per lyrics entry: `displayArtist`, `displayTitle`, `lang`, `synced`, `line`; per line: `start`, `value`. No `offset` appeared. |
| Language | `xxx` (undetermined) throughout the sample |
| Speed | per lookup, 4.1 s on average and 12.5 s at the slowest |
| Unknown song id | status `failed`, error code 70, no lyrics list |

Consequences that shape the design: lookups can be slow, so they are fetched only when asked for, with a loading state, a cache and a negative cache; and a visible share of songs has no lyrics, so "none" is a normal state, not an error.

## 3. Binding rules (inherited)

1. The existing API is authoritative: no endpoint or field is invented. Anything not listed in section 4 is a new proposal.
2. `ANDROID_CLIENT_CONTRACT.md` section 2 applies: 48dp targets, TalkBack labels, honest states not by colour alone, no third-party SDKs or analytics, no tracking.
3. Every screen goes through `/mobile-design` and is recorded in `android/DESIGN.md` (rule 9).
4. Lyrics text is copyrighted. It is never written to a log, never committed (fixtures use placeholder text with the real structure), never sent anywhere except from Navidrome to the screen, and the cache is cleared at sign-out.
5. In all documentation and communications, the person directing the project is "the owner".

## 4. Data source

Navidrome, directly, with the login already saved on the device (the same as streaming, `ANDROID_PLAYER_CONTRACT.md` section 1):

- `getLyricsBySongId` (OpenSubsonic `songLyrics`), with the song id the queue already holds. The id is checked with the same validator as streaming; an invalid id makes no request.
- `getOpenSubsonicExtensions`, once per session, to see whether `songLyrics` is listed. If it is not, the Lyrics view says "Your Navidrome doesn't provide lyrics" and no lyrics requests are made.
- The older `getLyrics` (artist and title) is not used: it matches by name, can pick the wrong song, and returns plain text only.

Requests use the signing style of `SubsonicSongSource` (fresh salt per request, no password in the address, https only, no redirects). The read timeout for a lyrics request is 45 s (measured 2026-11-01: songs with no lyrics can take over 23 s to be answered, so the first 20 s was too short; a timeout is shown as its own state, not as "unreachable"). A failure is classified as in `SongSourceProblem`: unreachable, login rejected, not found (code 70, treated as "no lyrics"), other.

## 5. Choosing and cleaning the lyrics

A response can hold several entries (different languages, or timed and plain versions).

1. Prefer a timed entry (`synced: true`). Among several, prefer the one whose `lang` matches the phone's language, otherwise the first listed.
2. If there is no timed entry, use a plain entry by the same language rule.
3. No other entry is shown in version 1 (open question 2).

Cleaning, for safety and layout:
- Lines are plain text. No HTML, links or markup are interpreted. Control characters are removed.
- A timed entry is sorted by `start` (milliseconds). Entries with a missing or negative `start`, or a line longer than 500 characters, are cut or dropped; more than 2,000 lines is cut.
- If the entry has an `offset` (milliseconds, may be negative), it is added to every `start`. If it has none, nothing is added.
- An empty line is kept as a pause and drawn as space.
- If every timed line has the same `start` or the starts run backwards, the entry is treated as plain.

## 6. Following the music

- The current line is the last line whose start is at or before the playback position. Before the first line, no line is current.
- The position comes from the player. The scrobble tracker's one-second tick is too coarse, so while the Lyrics view is visible and the song is playing a separate check runs about every 250 ms, and it stops when the view is hidden or playback pauses. It never changes the scrobbling cadence.
- A seek, a skip or a restart moves the marker at once. Pause freezes it.
- The current line is kept near the middle of the view. If the owner scrolls the lyrics by hand, following stops and a "Back to the current line" button appears (no gesture is the only way back). Following also resumes when the song changes.
- Reduced motion: the view jumps to the current line instead of scrolling smoothly (Compose already follows the system animation setting).
- Tapping a line does nothing (owner decision, section 11, answer 1). The only ways to move the music remain the seek bar and the player controls, so an accidental touch while reading never moves the song.

## 7. The screen

The Now Playing sheet already toggles between the player and the queue. It gets three labelled views, **Player, Lyrics, Queue**, as a row of text tabs, each at least 48dp, with the selected one marked in words and by shape, not colour alone. The last view used is remembered for the session.

States, each written out:
- **Loading:** "Loading lyrics…" (lookups can take several seconds; a plain progress indicator with the text).
- **Timed lyrics:** the lines; the current line is larger and bold and carries the spoken state "Current line"; the others are normal.
- **Plain lyrics:** the lines, with "These lyrics are not timed." above them.
- **None:** "No lyrics for this song." No retry button, because this is a normal answer.
- **Cannot reach Navidrome / login rejected / other:** a sentence in the same words as the rest of the app, with Try again. Lyrics already in the cache are shown instead, marked "Saved copy", when the phone is offline.
- **Server without `songLyrics`:** "Your Navidrome doesn't provide lyrics."

Accessibility: text follows the system font size and wraps; the view scrolls in portrait, landscape and at 200 % text; each line is plain text for TalkBack; the current line is not announced as it changes (that would interrupt the music and the speech), but it can be found with the "Back to the current line" button and its spoken state.

## 8. Cache and fetching

- Fetch only for the song that is playing, and only when the Lyrics view is opened for it. One request at a time; a request for a song that is no longer playing is cancelled.
- While the Lyrics view is open and the current song's lyrics have loaded, the next song's lyrics are fetched in the background so they are ready at the song change.
- Cache: one small file per song id, keyed by the Navidrome address and user so a different server never reads it; at most 300 songs or 5 MB, oldest removed first; cleared at sign-out. A cached entry is used at once and refreshed in the background no more than once a day.
- "None" answers are cached for 24 hours so a song with no lyrics does not cost another slow request every time it plays.
- Nothing is fetched in the background for songs the owner has not opened the Lyrics view for.

## 9. Phases

Each phase is one focused PR from `main`, with tests, no full-suite run by agents (the owner runs it; CI runs it on the PR head), and the `/mobile-design` review recorded for UI.

**L0: documents.** This contract approved by the owner. Then `D-019` in `DECISIONS.md`, `LYRICS-01..04` rows in `REQUIREMENTS.md`, a Lyrics section in `TEST_PLAN.md`, and the pointer in `ANDROID_PLAYER_CONTRACT.md`. Direct to `main` (documentation only).

**L1: data layer.** `LyricsSource` (`getLyricsBySongId` and the extension check, in the style of `SubsonicSongSource`), the choosing and cleaning rules of section 5, and the cache of section 8. Tests (no real lyrics; fixtures use placeholder text and the structure of the real answer):
- Parsing of a timed, a plain and an empty answer; several entries; language preference; timed before plain.
- Cleaning: unsorted starts, missing or negative `start`, an `offset`, over-long lines, over-many lines, control characters, equal or backward starts treated as plain.
- A bad song id makes no request; the answer for error code 70 is "none"; auth codes are "login rejected"; a network failure is "unreachable".
- No password, token or lyrics text in any error or log.
- Cache: hit, miss, size and count limits, a different server or user does not read it, cleared at sign-out, "none" expiry after 24 hours.

**L2: following the music.** A pure `LyricsTimeline` (current line for a position, an offset, seek, empty and one-line cases) and the visible-only 250 ms check. Tests: exact boundaries, before the first line, after the last, a seek backward and forward, an offset, pause, and that the check stops when hidden.

**L3: screen.** The three-view sheet, the lyrics view and every state of section 7. Tests: the state choice from the data layer's results; the manual device list below.

**L4: hardening and device run** (the owner's phone): see section 10.

## 10. Verification

- Unit tests as above; `./gradlew testDebugUnitTest assembleDebug lintDebug assembleRelease` on JDK 17 per phase.
- On the owner's phone over Tailscale: a timed song (line follows the music, a seek moves it), a plain song, a song with none, the slowest case (is the loading state clear after 10 s?), airplane mode with a cached song and an uncached song, a song change with the view open (does the next song's lyrics arrive in time?), TalkBack through the three views, 200 % text and landscape, scrolling by hand and the return button, a tap on a line doing nothing, battery over a long listen with the view open, sign-out clearing the cache.
- Nothing is claimed as verified on a device until the owner has tested it.

## 11. Open questions, with proposed answers

Decided by the owner on 2026-11-01:

1. **Tap a line to seek: no.** Lines are not tappable.
2. **A language switch: no.** The phone's language is preferred, otherwise the first listed. The sample showed only undetermined language.
3. **Prefetch the next song's lyrics: yes,** only while the Lyrics view is open (section 8), because lookups can take several seconds.
4. **Cache size and life: yes** to 300 songs or 5 MB, refreshed at most daily, "none" for 24 hours.

Not yet discussed (the proposed answer stands until the owner overrides it):

5. **Hide the Lyrics tab when the server lacks `songLyrics`, or show it with a message?** Proposed: show it with the message, so the owner knows why.
6. **Lyrics on the lock screen or notification?** Proposed: no. Android's media notification has no lyrics area.
7. **Font size control inside the view?** Proposed: no; follow the system font size.
8. **Where the phone's measured speed will differ.** The 4.1 s average was measured on the local network; Tailscale may be slower. Proposed: judge the loading state again after the owner's first device run.

## 12. Risks

1. **Slow lookups** (4.1 s average, 12.5 s worst on the local network): mitigated by loading state, cache, negative cache and prefetch.
2. **Wrong or badly timed lyrics** come from the owner's files and plugins; the app shows what Navidrome returns and has no correction. Only an explicit `offset` is applied.
3. **Copyright text in the repository:** fixtures and test data use placeholder text; the real survey kept no lyrics.
4. **Battery:** the 250 ms check runs only while the view is visible and the song is playing.
5. **Coverage:** about one song in eight had no lyrics in the sample, so "none" will be common.
6. **Server variety:** a different Navidrome version could omit `songLyrics` or fields; the extension check and tolerant parsing (ignore unknown fields, tolerate missing optional ones) cover that.
