import AppKit
import DiscairAudio
import DiscairNavidrome
import SwiftUI
import Testing
@testable import DiscairUI

/// Slice D6 (`docs/plans/MACOS_DESIGN_DETAILS.md`):
/// - D6.1: traffic lights keep the same window position on library pages and Now Playing; collapse chevron and top-right chips sit on their centre line.
/// - D6.2: artist and album sit on stacked lines (album up to 2 lines, tail-truncated) instead of wrapping as a hanging block.
/// - D6.3: the lyrics column clears the slid-out vinyl disc by at least 32 pt.
/// - D6.4: the untimed-lyrics note sits directly above the first lyric line, the bottom status chips align with the volume slider row, and the quality tag uses `CUQualityBadge` beside the song title.
@MainActor
@Suite(.serialized)
struct D6NowPlayingTests {
    @Test func trafficLightsAndTopChromeShareLibraryCentreLine() {
        #expect(CU.Shell.trafficLightsLeading == 28)
        #expect(CU.Shell.trafficLightsTop == 28)
        #expect(CU.Shell.trafficLightsCentreY == CupertinoToolbar.centreY)
        #expect(NowPlayingCloseControls.barTop + NowPlayingCloseControls.barHeight / 2 == CU.Shell.trafficLightsCentreY)
        #expect(NowPlayingCloseControls.barHeight == CupertinoNowPlaying.chipHeight)
    }

    @Test func lyricsColumnClearsSlidOutVinylDiscByAtLeast32Points() {
        let coverWidth = CupertinoNowPlaying.coverWidth
        let overhang = DiscSleeve.overhang(for: coverWidth)
        let discRightEdge = CupertinoNowPlaying.coverLeading + coverWidth + overhang
        let gap = CupertinoNowPlaying.lyricsLeading - discRightEdge
        #expect(abs(overhang - 130.2) < 0.01)
        #expect(gap >= CupertinoNowPlaying.discClearance)
        #expect(CupertinoNowPlaying.discClearance == CU.Space.xl)
    }

    @Test func plainLyricsNoteAndAlbumLineLimitsMatchSpec() {
        #expect(CupertinoNowPlaying.albumLineLimit == 2)
        #expect(CupertinoNowPlaying.plainLyricsTopPadding == 0)
        #expect(CupertinoNowPlaying.plainLyricsNoteSpacing == CU.Space.m)
        #expect(CupertinoNowPlaying.timedLyricsVerticalPadding == 120)
    }

    @Test(arguments: AppearanceMode.allCases)
    func trafficLightsDoNotJumpBetweenLibraryAndNowPlaying(_ mode: AppearanceMode) throws {
        let size = NSSize(width: 1280, height: 800)

        let homeState = AppState(themeID: .cupertino, screen: .home)
        let homeRep = try render(CupertinoWindow(state: homeState), size: size, mode: mode, name: "d6-home-\(mode)")
        let homeRed = try findRedTrafficLightCentre(in: homeRep, widthPt: size.width)

        let nowState = makeLiveNowPlayingState(plainLyrics: false)
        let nowRep = try render(CupertinoWindow(state: nowState), size: size, mode: mode, name: "d6-now-timed-\(mode)")
        let nowRed = try findRedTrafficLightCentre(in: nowRep, widthPt: size.width)

        #expect(
            abs(homeRed.x - nowRed.x) <= 1.5 && abs(homeRed.y - nowRed.y) <= 1.5,
            "red traffic light jumped from \(homeRed) on Home to \(nowRed) on Now Playing (\(mode))"
        )
        #expect(
            abs(nowRed.y - CU.Shell.trafficLightsCentreY) <= 2.0,
            "Now Playing traffic lights centreY=\(nowRed.y) expected ~\(CU.Shell.trafficLightsCentreY) (\(mode))"
        )

        // Probe the top-right "Up Next" chip to confirm its vertical centre matches the traffic lights' centre line.
        let scale = CGFloat(nowRep.pixelsWide) / size.width
        let chipX = Int((size.width - CU.Space.m - 36) * scale)
        let bg = rgb(nowRep, x: chipX, y: Int(4 * scale))
        let chipYs = (Int(8 * scale)..<Int(64 * scale)).filter { y in
            dist(rgb(nowRep, x: chipX, y: y), bg) > 0.04
        }
        let chipTopPt = CGFloat(try #require(chipYs.first)) / scale
        let chipBottomPt = CGFloat(try #require(chipYs.last)) / scale
        let chipCentrePt = (chipTopPt + chipBottomPt) / 2
        #expect(
            abs(chipCentrePt - nowRed.y) <= 2.5,
            "Up Next chip centreY=\(chipCentrePt) (\(chipTopPt)...\(chipBottomPt)) vs traffic lights centreY=\(nowRed.y) (\(mode))"
        )
    }

    @Test(arguments: AppearanceMode.allCases)
    func plainLyricsStartNearCoverTopAndChipsAlignWithVolumeRow(_ mode: AppearanceMode) throws {
        // Tall window like the owner's 940 pt screenshot, where pinned-to-bottom chips used to drift ~177 pt below the left column.
        let size = NSSize(width: 1280, height: 940)
        let state = makeLiveNowPlayingState(plainLyrics: true)
        let rep = try render(CupertinoWindow(state: state), size: size, mode: mode, name: "d6-now-plain-\(mode)")
        let scale = CGFloat(rep.pixelsWide) / size.width

        // Probe the lyrics column near its top (x = lyricsLeading + 10 ... lyricsLeading + 220) to verify the
        // "These lyrics are not timed." note and first lyric line appear near contentTop (90 pt), not ~155 pt below.
        let lyricsXRange = Int((CupertinoNowPlaying.lyricsLeading + 4) * scale)...Int((CupertinoNowPlaying.lyricsLeading + 220) * scale)
        let noteBand = Int(80 * scale)..<Int(130 * scale)
        let firstLineBand = Int(115 * scale)..<Int(185 * scale)
        let lyricsBg = rgb(rep, x: Int((CupertinoNowPlaying.lyricsLeading + 10) * scale), y: Int(74 * scale))

        let noteHits = noteBand.filter { y in
            lyricsXRange.contains { x in luminance(rgb(rep, x: x, y: y)) - luminance(lyricsBg) > 0.15 }
        }
        let firstLineHits = firstLineBand.filter { y in
            lyricsXRange.contains { x in luminance(rgb(rep, x: x, y: y)) - luminance(lyricsBg) > 0.25 }
        }
        #expect(!noteHits.isEmpty, "expected untimed lyrics note near y=90 (\(mode))")
        #expect(!firstLineHits.isEmpty, "expected first plain lyric line directly below the note, not 155 pt down (\(mode))")

        // Probe the volume slider row on the left column (below transport, y in 620...760) and the bottom status chips
        // on the right column (x = lyricsLeading + 20 ... lyricsLeading + 100) to confirm they share one horizontal band
        // rather than the chips sitting pinned at the bottom of the 940 pt window (y ~ 890).
        let chipProbeX = Int((CupertinoNowPlaying.lyricsLeading + 40) * scale)
        let bottomPinnedBand = Int(860 * scale)..<Int(920 * scale)
        let midColumnBand = Int(640 * scale)..<Int(790 * scale)
        let chipBg = rgb(rep, x: chipProbeX, y: Int(840 * scale))

        let midChipYs = midColumnBand.filter { y in
            dist(rgb(rep, x: chipProbeX, y: y), chipBg) > 0.04
        }
        let bottomPinnedHits = bottomPinnedBand.filter { y in
            dist(rgb(rep, x: chipProbeX, y: y), chipBg) > 0.08
        }
        #expect(!midChipYs.isEmpty, "expected status chips aligned with the left column's volume row (640...790 pt) (\(mode))")
        #expect(bottomPinnedHits.isEmpty, "status chips should not sit pinned near the bottom of a 940 pt window (\(mode))")
    }

    private func makeLiveNowPlayingState(plainLyrics: Bool) -> AppState {
        let state = AppState(themeID: .cupertino, screen: .nowPlaying)
        let song = QueueItem(
            songID: "s1",
            title: "I Say a Little Prayer",
            artist: "Aretha Franklin",
            album: "The Electrifying Aretha Franklin",
            duration: 214,
            suffix: "mp3",
            quality: "MP3 320"
        )
        state.player.play([song])
        if plainLyrics {
            state.lyrics.preview(Lyrics(timed: false, lines: [
                LyricLine(startMs: nil, text: "I didn't want to do it"),
                LyricLine(startMs: nil, text: "The moment I wake up"),
                LyricLine(startMs: nil, text: "Before I put on my makeup"),
            ]))
        } else {
            state.lyrics.preview(Lyrics(timed: true, lines: [
                LyricLine(startMs: 0, text: "A slow tide under the floorboards"),
                LyricLine(startMs: 4000, text: "the lamp keeps counting what we left"),
            ]))
        }
        return state
    }

    private func render<V: View>(_ view: V, size: NSSize, mode: AppearanceMode, name: String? = nil) throws -> NSBitmapImageRep {
        let savedScreenshotMode = RenderMode.offscreenScreenshot
        RenderMode.offscreenScreenshot = true
        let savedPalette = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer {
            RenderMode.offscreenScreenshot = savedScreenshotMode
            CUPalette.current = savedPalette
        }

        let host = NSHostingView(
            rootView: view
                .frame(width: size.width, height: size.height)
                .environment(\.colorScheme, mode == .night ? .dark : .light)
        )
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.25))
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.15))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        if let name, let dirPath = ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"], !dirPath.isEmpty,
           let png = rep.representation(using: .png, properties: [:]) {
            let dir = URL(fileURLWithPath: dirPath)
            try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            try png.write(to: dir.appendingPathComponent("\(name).png"))
        }
        return rep
    }

    private func findRedTrafficLightCentre(in rep: NSBitmapImageRep, widthPt: CGFloat) throws -> CGPoint {
        let scale = CGFloat(rep.pixelsWide) / widthPt
        var xs: [Int] = []
        var ys: [Int] = []
        for y in Int(10 * scale)..<Int(56 * scale) {
            for x in Int(10 * scale)..<Int(56 * scale) {
                let c = rgb(rep, x: x, y: y)
                // Red traffic light dot: Color(red: 1, green: 0.37, blue: 0.34), clearly redder than the backdrop in Day and Night.
                if c.0 > 0.75 && (c.0 - c.1) > 0.25 && (c.0 - c.2) > 0.25 {
                    xs.append(x)
                    ys.append(y)
                }
            }
        }
        let minX = CGFloat(try #require(xs.min())) / scale
        let maxX = CGFloat(try #require(xs.max())) / scale
        let minY = CGFloat(try #require(ys.min())) / scale
        let maxY = CGFloat(try #require(ys.max())) / scale
        return CGPoint(x: (minX + maxX) / 2, y: (minY + maxY) / 2)
    }

    private func rgb(_ rep: NSBitmapImageRep, x: Int, y: Int) -> (CGFloat, CGFloat, CGFloat) {
        let c = rep.colorAt(x: x, y: y)?.usingColorSpace(.sRGB) ?? .black
        return (c.redComponent, c.greenComponent, c.blueComponent)
    }

    private func dist(_ a: (CGFloat, CGFloat, CGFloat), _ b: (CGFloat, CGFloat, CGFloat)) -> CGFloat {
        abs(a.0 - b.0) + abs(a.1 - b.1) + abs(a.2 - b.2)
    }

    private func luminance(_ c: (CGFloat, CGFloat, CGFloat)) -> CGFloat {
        0.2126 * c.0 + 0.7152 * c.1 + 0.0722 * c.2
    }
}
