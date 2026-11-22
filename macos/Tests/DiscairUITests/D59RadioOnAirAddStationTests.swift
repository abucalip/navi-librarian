import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// D5.9 (`docs/plans/MACOS_DESIGN_DETAILS.md`): the empty On Air panel shrinks to its content instead of keeping a 120 pt
/// minimum height, and "Add station" sits in the Radio header toolbar row beside Stations | Heard.
@MainActor
struct D59RadioOnAirAddStationTests {
    @Test func emptyOnAirPanelShrinksToContent() {
        let state = AppState(themeID: .cupertino, screen: .stations)
        let view = OnAirPanel(state: state)
            .frame(width: CupertinoStations.panelWidth)
            .fixedSize(horizontal: false, vertical: true)
        let host = NSHostingView(rootView: view)
        host.layoutSubtreeIfNeeded()
        let height = host.fittingSize.height
        #expect(height > 40 && height < 90, "Empty On Air panel should hug its content (< 90 pt), got \(height) pt")
    }

    @Test(arguments: AppearanceMode.allCases)
    func addStationSitsInHeaderToolbarRowAndEmptyOnAirIsCompact(_ mode: AppearanceMode) throws {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }

        let state = AppState(themeID: .cupertino, screen: .stations)
        state.stations.showForPreview(stations: [
            RadioStation(id: "1", name: "FIP", proxied: true, playableURL: "https://example.invalid/1", tags: ["Eclectic"]),
            RadioStation(id: "2", name: "KEXP", proxied: true, playableURL: "https://example.invalid/2", tags: ["Indie"]),
        ])

        let size = NSSize(width: 1100, height: 640)
        let host = NSHostingView(
            rootView: CupertinoStations(state: state, selected: "1")
                .frame(width: size.width, height: size.height)
                .background(CU.content)
                .environment(\.colorScheme, mode == .night ? .dark : .light)
        )
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.3))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let scale = CGFloat(rep.pixelsWide) / size.width

        func rgb(_ x: Int, _ y: Int) -> (CGFloat, CGFloat, CGFloat) {
            let c = rep.colorAt(x: x, y: y)?.usingColorSpace(.sRGB) ?? .black
            return (c.redComponent, c.greenComponent, c.blueComponent)
        }
        func dist(_ a: (CGFloat, CGFloat, CGFloat), _ b: (CGFloat, CGFloat, CGFloat)) -> CGFloat {
            abs(a.0 - b.0) + abs(a.1 - b.1) + abs(a.2 - b.2)
        }

        let bg = rgb(2, 2)

        // 1. "Add station" button sits in the top header toolbar row (y = 0..<60 pt) directly left of Stations | Heard,
        //    aligned on the same vertical centre line, and NOT below the On Air panel.
        let headerYRange = Int(4 * scale)..<Int(64 * scale)
        let segmentedXRange = Int(920 * scale)..<Int(1068 * scale)
        let addButtonXRange = Int(780 * scale)..<Int(905 * scale)
        let segYs = headerYRange.filter { y in segmentedXRange.contains { x in dist(rgb(x, y), bg) > 0.03 } }
        let addYs = headerYRange.filter { y in addButtonXRange.contains { x in dist(rgb(x, y), bg) > 0.03 } }
        let segTopPt = CGFloat(try #require(segYs.first, "Expected Stations | Heard in header")) / scale
        let segBottomPt = CGFloat(try #require(segYs.last)) / scale
        let addTopPt = CGFloat(try #require(addYs.first, "Expected Add station capsule in header row")) / scale
        let addBottomPt = CGFloat(try #require(addYs.last)) / scale
        let segMidPt = (segTopPt + segBottomPt) / 2
        let addMidPt = (addTopPt + addBottomPt) / 2

        #expect(addTopPt < 50, "Add station should be in the top header row, got top=\(addTopPt)")
        #expect(abs(addMidPt - segMidPt) <= 6,
                "Add station midY=\(addMidPt) should align with Stations|Heard midY=\(segMidPt) (\(mode))")

        // 2. Empty On Air panel in the right column is compact (< 90 pt tall) with no Add station button below it.
        // Right panel column is inside x = 738..1068 pt; sample its horizontal midpoint (900 pt) below the header/chips (y >= 100 pt).
        let panelMidX = Int(900 * scale)
        let startY = Int(100 * scale)
        let panelYs = (startY..<rep.pixelsHigh).filter { dist(rgb(panelMidX, $0), bg) > 0.02 }
        let panelTop = try #require(panelYs.first)
        let panelBottom = try #require(panelYs.last)
        let panelHeightPt = CGFloat(panelBottom - panelTop + 1) / scale
        #expect(panelHeightPt > 40 && panelHeightPt < 90,
                "Rendered empty On Air panel should be compact (< 90 pt), got \(panelHeightPt) pt (\(mode))")
    }

    @Test func addStationHiddenOnHeardTabAndVisibleWhenStationsEmpty() throws {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = .day
        defer { CUPalette.current = saved }

        let state = AppState(themeID: .cupertino, screen: .stations)
        state.stations.showForPreview(stations: [])

        let size = NSSize(width: 1100, height: 640)
        func hasAddStationInHeader() throws -> Bool {
            let host = NSHostingView(
                rootView: CupertinoStations(state: state)
                    .frame(width: size.width, height: size.height)
                    .background(CU.content)
                    .environment(\.colorScheme, .light)
            )
            host.frame = NSRect(origin: .zero, size: size)
            let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
            window.contentView = host
            window.orderBack(nil)
            host.layoutSubtreeIfNeeded()
            RunLoop.current.run(until: Date().addingTimeInterval(0.2))

            let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
            host.cacheDisplay(in: host.bounds, to: rep)
            let scale = CGFloat(rep.pixelsWide) / size.width
            func rgb(_ x: Int, _ y: Int) -> (CGFloat, CGFloat, CGFloat) {
                let c = rep.colorAt(x: x, y: y)?.usingColorSpace(.sRGB) ?? .black
                return (c.redComponent, c.greenComponent, c.blueComponent)
            }
            let bg = rgb(2, 2)
            let headerYRange = Int(8 * scale)..<Int(56 * scale)
            let addButtonXRange = Int(780 * scale)..<Int(905 * scale)
            return headerYRange.contains { y in
                addButtonXRange.contains { x in
                    let c = rgb(x, y)
                    return abs(c.0 - bg.0) + abs(c.1 - bg.1) + abs(c.2 - bg.2) > 0.03
                }
            }
        }

        #expect(try hasAddStationInHeader(),
                "Add station should still be available in header when stations list is empty")

        state.stations.pane = .heard
        #expect(try !hasAddStationInHeader(),
                "Add station should not appear on the Heard tab")
    }
}
