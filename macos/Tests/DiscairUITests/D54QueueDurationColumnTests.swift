import AppKit
import DiscairAudio
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// D5.4 (`docs/plans/MACOS_DESIGN_DETAILS.md`): Queue rows reserve both the playing-icon slot before the title
/// and the trailing "⋯" action slot on every row so durations share one fixed column, and the header count's
/// trailing edge aligns with that column.
@MainActor
struct D54QueueDurationColumnTests {
    @Test func queueLayoutConstantsReservePlayingAndActionSlots() {
        #expect(CupertinoQueueInspector.playingSlotWidth > 0)
        #expect(CupertinoQueueInspector.actionSlotWidth > 0)
        #expect(
            CupertinoQueueInspector.headerCountTrailingInset ==
            CupertinoQueueInspector.rowHorizontalPadding + CupertinoQueueInspector.rowSpacing + CupertinoQueueInspector.actionSlotWidth
        )
    }

    @Test(arguments: AppearanceMode.allCases)
    func liveQueueRowsAndHeaderShareDurationColumn(_ mode: AppearanceMode) throws {
        let state = AppState(themeID: .cupertino, screen: .home)
        let songs = [
            QueueItem(songID: "p1", title: "Played Song", artist: "Artist One", duration: 225),
            QueueItem(songID: "c1", title: "Current Song", artist: "Artist Two", duration: 225),
            QueueItem(songID: "u1", title: "Upcoming Song", artist: "Artist Three", duration: 225),
        ]
        state.player.play(songs, startAt: 1)

        let measured = try measureLiveQueue(mode, state: state)

        // All three rows (played, current, upcoming) share the same duration trailing edge.
        #expect(abs(measured.playedTimeTrailingX - measured.currentTimeTrailingX) <= 1.5,
                "played=\(measured.playedTimeTrailingX) vs current=\(measured.currentTimeTrailingX) (\(mode))")
        #expect(abs(measured.upcomingTimeTrailingX - measured.currentTimeTrailingX) <= 1.5,
                "upcoming=\(measured.upcomingTimeTrailingX) vs current=\(measured.currentTimeTrailingX) (\(mode))")

        // Header count trailing edge ("1 to come · 3 min") aligns with the duration column.
        #expect(abs(measured.headerTrailingX - measured.upcomingTimeTrailingX) <= 2.5,
                "header=\(measured.headerTrailingX) vs duration=\(measured.upcomingTimeTrailingX) (\(mode))")

        // Trailing "⋯" slot is populated only on the upcoming row, yet reserved on played and current rows.
        #expect(!measured.playedHasActionIcon, "played row should not show action icon (\(mode))")
        #expect(!measured.currentHasActionIcon, "current row should not show action icon (\(mode))")
        #expect(measured.upcomingHasActionIcon, "upcoming row should show action icon (\(mode))")

        // Playing-icon slot before the title is populated only on the current row.
        #expect(!measured.playedHasPlayingIcon, "played row should not show playing icon (\(mode))")
        #expect(measured.currentHasPlayingIcon, "current row should show playing icon (\(mode))")
        #expect(!measured.upcomingHasPlayingIcon, "upcoming row should not show playing icon (\(mode))")
    }

    @Test(arguments: AppearanceMode.allCases)
    func fixtureQueueRowsAndHeaderShareDurationColumn(_ mode: AppearanceMode) throws {
        let state = AppState(themeID: .cupertino, screen: .home)
        let rep = try renderInspector(mode, state: state, size: NSSize(width: CupertinoQueueInspector.width, height: 640))
        let scale = CGFloat(rep.pixelsWide) / CupertinoQueueInspector.width
        let expectedTimeTrailingX = CupertinoQueueInspector.width - 16 - CupertinoQueueInspector.headerCountTrailingInset

        // Header count ("8 songs · 52 min") aligns with the reserved duration column.
        let headerTrailingX = try rightmostInkX(in: rep, scale: scale, xRange: 210..<360, yRange: 66..<102, bgSampleX: 210, bgSampleY: 84)
        #expect(abs(headerTrailingX - expectedTimeTrailingX) <= 2.5,
                "fixture header=\(headerTrailingX) vs expected=\(expectedTimeTrailingX) (\(mode))")

        // First two fixture rows (playing row 0 and non-playing row 1) share the same duration trailing edge.
        let rowCenters = findRowCenters(in: rep, scale: scale, count: 2)
        #expect(rowCenters.count == 2)
        let row0TimeX = try rightmostInkX(in: rep, scale: scale, xRange: 270..<328, yRange: (rowCenters[0] - 12)..<(rowCenters[0] + 12), bgSampleX: 265, bgSampleY: rowCenters[0])
        let row1TimeX = try rightmostInkX(in: rep, scale: scale, xRange: 270..<328, yRange: (rowCenters[1] - 12)..<(rowCenters[1] + 12), bgSampleX: 265, bgSampleY: rowCenters[1])
        #expect(abs(row0TimeX - row1TimeX) <= 1.5, "row0=\(row0TimeX) vs row1=\(row1TimeX) (\(mode))")
        #expect(abs(row0TimeX - expectedTimeTrailingX) <= 2.5, "row0=\(row0TimeX) vs expected=\(expectedTimeTrailingX) (\(mode))")
    }

    private struct LiveMeasured {
        let headerTrailingX: CGFloat
        let playedTimeTrailingX: CGFloat
        let currentTimeTrailingX: CGFloat
        let upcomingTimeTrailingX: CGFloat
        let playedHasActionIcon: Bool
        let currentHasActionIcon: Bool
        let upcomingHasActionIcon: Bool
        let playedHasPlayingIcon: Bool
        let currentHasPlayingIcon: Bool
        let upcomingHasPlayingIcon: Bool
    }

    private func measureLiveQueue(_ mode: AppearanceMode, state: AppState) throws -> LiveMeasured {
        let rep = try renderInspector(mode, state: state, size: NSSize(width: CupertinoQueueInspector.width, height: 640))
        let scale = CGFloat(rep.pixelsWide) / CupertinoQueueInspector.width

        let headerTrailingX = try rightmostInkX(in: rep, scale: scale, xRange: 210..<360, yRange: 66..<102, bgSampleX: 210, bgSampleY: 84)
        let rowCenters = findRowCenters(in: rep, scale: scale, count: 3)
        #expect(rowCenters.count == 3, "expected 3 rendered queue rows, found \(rowCenters.count)")

        let playedY = rowCenters[0]
        let currentY = rowCenters[1]
        let upcomingY = rowCenters[2]

        let playedTimeX = try rightmostInkX(in: rep, scale: scale, xRange: 270..<328, yRange: (playedY - 12)..<(playedY + 12), bgSampleX: 265, bgSampleY: playedY)
        let currentTimeX = try rightmostInkX(in: rep, scale: scale, xRange: 270..<328, yRange: (currentY - 12)..<(currentY + 12), bgSampleX: 265, bgSampleY: currentY)
        let upcomingTimeX = try rightmostInkX(in: rep, scale: scale, xRange: 270..<328, yRange: (upcomingY - 12)..<(upcomingY + 12), bgSampleX: 265, bgSampleY: upcomingY)

        // Trailing action slot sits at x = 332..356 pt (width 24 pt after 8 pt spacing).
        let playedAction = hasInk(in: rep, scale: scale, xRange: 332..<356, yRange: (playedY - 12)..<(playedY + 12), bgSampleX: 265, bgSampleY: playedY)
        let currentAction = hasInk(in: rep, scale: scale, xRange: 332..<356, yRange: (currentY - 12)..<(currentY + 12), bgSampleX: 265, bgSampleY: currentY)
        let upcomingAction = hasInk(in: rep, scale: scale, xRange: 332..<356, yRange: (upcomingY - 12)..<(upcomingY + 12), bgSampleX: 265, bgSampleY: upcomingY)

        // Playing-icon slot sits at x = 72..90 pt (between 40 pt cover at 24..64 and title at 98+).
        let playedIcon = hasInk(in: rep, scale: scale, xRange: 72..<90, yRange: (playedY - 10)..<(playedY + 10), bgSampleX: 265, bgSampleY: playedY)
        let currentIcon = hasInk(in: rep, scale: scale, xRange: 72..<90, yRange: (currentY - 10)..<(currentY + 10), bgSampleX: 265, bgSampleY: currentY)
        let upcomingIcon = hasInk(in: rep, scale: scale, xRange: 72..<90, yRange: (upcomingY - 10)..<(upcomingY + 10), bgSampleX: 265, bgSampleY: upcomingY)

        return LiveMeasured(
            headerTrailingX: headerTrailingX,
            playedTimeTrailingX: playedTimeX,
            currentTimeTrailingX: currentTimeX,
            upcomingTimeTrailingX: upcomingTimeX,
            playedHasActionIcon: playedAction,
            currentHasActionIcon: currentAction,
            upcomingHasActionIcon: upcomingAction,
            playedHasPlayingIcon: playedIcon,
            currentHasPlayingIcon: currentIcon,
            upcomingHasPlayingIcon: upcomingIcon
        )
    }

    private func renderInspector(_ mode: AppearanceMode, state: AppState, size: NSSize) throws -> NSBitmapImageRep {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }

        let host = NSHostingView(
            rootView: CupertinoQueueInspector(state: state)
                .frame(width: size.width, height: size.height)
                .background(CU.content)
                .environment(\.colorScheme, mode == .night ? .dark : .light)
        )
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.2))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        return rep
    }

    /// Locates vertical centers of queue rows by scanning the 40x40 cover column (`x = 30..58 pt`) below the divider (`y >= 200 pt`).
    private func findRowCenters(in rep: NSBitmapImageRep, scale: CGFloat, count: Int) -> [CGFloat] {
        let maxY = Int(CGFloat(rep.pixelsHigh) / scale) - 40
        let bg = rgb(rep, x: Int(265 * scale), y: Int(190 * scale))
        var centers: [CGFloat] = []
        var y = 200
        while y < maxY && centers.count < count {
            let py = Int(CGFloat(y) * scale)
            let hasCover = (Int(30 * scale)..<Int(58 * scale)).contains { px in
                dist(rgb(rep, x: px, y: py), bg) > 0.08
            }
            if hasCover {
                // CoverView is 40 pt tall; its center is ~20 pt below its top edge.
                centers.append(CGFloat(y) + 20)
                y += 54
            } else {
                y += 2
            }
        }
        return centers
    }

    private func rightmostInkX(in rep: NSBitmapImageRep, scale: CGFloat, xRange: Range<CGFloat>, yRange: Range<CGFloat>, bgSampleX: CGFloat, bgSampleY: CGFloat) throws -> CGFloat {
        let bg = rgb(rep, x: Int(bgSampleX * scale), y: Int(bgSampleY * scale))
        let pxRange = Int(xRange.lowerBound * scale)..<Int(xRange.upperBound * scale)
        let pyRange = Int(yRange.lowerBound * scale)..<Int(yRange.upperBound * scale)
        let lastPx = try #require(pxRange.reversed().first { px in
            pyRange.contains { py in dist(rgb(rep, x: px, y: py), bg) > 0.08 }
        })
        return CGFloat(lastPx) / scale
    }

    private func hasInk(in rep: NSBitmapImageRep, scale: CGFloat, xRange: Range<CGFloat>, yRange: Range<CGFloat>, bgSampleX: CGFloat, bgSampleY: CGFloat) -> Bool {
        let bg = rgb(rep, x: Int(bgSampleX * scale), y: Int(bgSampleY * scale))
        let pxRange = Int(xRange.lowerBound * scale)..<Int(xRange.upperBound * scale)
        let pyRange = Int(yRange.lowerBound * scale)..<Int(yRange.upperBound * scale)
        return pxRange.contains { px in
            pyRange.contains { py in dist(rgb(rep, x: px, y: py), bg) > 0.08 }
        }
    }

    private func rgb(_ rep: NSBitmapImageRep, x: Int, y: Int) -> (CGFloat, CGFloat, CGFloat) {
        let c = rep.colorAt(x: x, y: y)?.usingColorSpace(.sRGB) ?? .black
        return (c.redComponent, c.greenComponent, c.blueComponent)
    }

    private func dist(_ a: (CGFloat, CGFloat, CGFloat), _ b: (CGFloat, CGFloat, CGFloat)) -> CGFloat {
        abs(a.0 - b.0) + abs(a.1 - b.1) + abs(a.2 - b.2)
    }
}
