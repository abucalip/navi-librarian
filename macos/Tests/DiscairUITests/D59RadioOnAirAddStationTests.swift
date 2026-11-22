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

        // 1. "Add station" button sits in the top header toolbar row (y near top, beside Stations | Heard),
        //    not below the On Air panel.
        let addButtonFrame = try #require(findAccessibilityFrame(in: host, label: "Add station"),
                                          "Expected Add station button in accessibility tree")
        let segmentedFrame = try #require(findAccessibilityFrame(in: host, label: "Radio view"),
                                          "Expected Stations | Heard segmented control in accessibility tree")
        let hostFrameInScreen = window.convertToScreen(host.convert(host.bounds, to: nil))
        let addTopFromWindowTop = hostFrameInScreen.maxY - addButtonFrame.maxY
        let segTopFromWindowTop = hostFrameInScreen.maxY - segmentedFrame.maxY

        #expect(addTopFromWindowTop < 60, "Add station should be in the top header row, got top=\(addTopFromWindowTop)")
        #expect(abs(addButtonFrame.midY - segmentedFrame.midY) <= 6,
                "Add station midY=\(addButtonFrame.midY) should align with Stations|Heard midY=\(segmentedFrame.midY)")
        #expect(addButtonFrame.maxX < segmentedFrame.minX,
                "Add station (maxX=\(addButtonFrame.maxX)) should sit to the left of Stations|Heard (minX=\(segmentedFrame.minX))")
        #expect(abs(addTopFromWindowTop - segTopFromWindowTop) <= 6)

        // 2. Empty On Air panel in the right column is compact (< 90 pt tall) with no Add station button below it.
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

    @Test func addStationHiddenOnHeardTabAndVisibleWhenStationsEmpty() {
        let state = AppState(themeID: .cupertino, screen: .stations)
        state.stations.showForPreview(stations: [])

        let size = NSSize(width: 1100, height: 640)
        let host = NSHostingView(
            rootView: CupertinoStations(state: state)
                .frame(width: size.width, height: size.height)
                .background(CU.content)
        )
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.2))

        #expect(findAccessibilityFrame(in: host, label: "Add station") != nil,
                "Add station should still be available in header when stations list is empty")

        state.stations.pane = .heard
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.2))

        #expect(findAccessibilityFrame(in: host, label: "Add station") == nil,
                "Add station should not appear on the Heard tab")
    }

    private func findAccessibilityFrame(in root: AnyObject, label: String) -> NSRect? {
        var queue: [AnyObject] = [root]
        var visited = Set<ObjectIdentifier>()
        while !queue.isEmpty {
            let current = queue.removeFirst()
            let id = ObjectIdentifier(current)
            if visited.contains(id) { continue }
            visited.insert(id)

            if let element = current as? NSAccessibilityElementProtocol {
                if element.accessibilityLabel?() == label, let frame = element.accessibilityFrame?(), !frame.isEmpty {
                    return frame
                }
            } else if let view = current as? NSView {
                if view.accessibilityLabel() == label, !view.accessibilityFrame().isEmpty {
                    return view.accessibilityFrame()
                }
            }

            if let children = (current as? NSAccessibilityElementProtocol)?.accessibilityChildren?() {
                for child in children { queue.append(child as AnyObject) }
            }
            if let view = current as? NSView {
                for subview in view.subviews { queue.append(subview) }
            }
        }
        return nil
    }
}
