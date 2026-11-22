import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// D5.2 (`docs/plans/MACOS_DESIGN_DETAILS.md`):
/// - `CUStageTracker` draws 2 pt connectors between the four dots, filled up to the current step.
/// - `CupertinoDownloads` hides the stepper on completed (`.imported`) rows while keeping "✓ In your library".
@MainActor
@Suite(.serialized)
struct D52DownloadsStepperConnectorsTests {
    @Test func stageConnectorsMatchStepProgress() {
        #expect(CUStageTracker.connectorThickness == 2)
        #expect(CUChartMath.stageConnectors(step: -1) == [false, false, false])
        #expect(CUChartMath.stageConnectors(step: 0) == [false, false, false])
        #expect(CUChartMath.stageConnectors(step: 1) == [true, false, false])
        #expect(CUChartMath.stageConnectors(step: 2) == [true, true, false])
        #expect(CUChartMath.stageConnectors(step: 3) == [true, true, true])
        #expect(CUChartMath.stageConnectors(step: 4) == [true, true, true])
        #expect(CUChartMath.stageConnectors(step: 9) == [true, true, true])
    }

    @Test(arguments: AppearanceMode.allCases)
    func stageTrackerRendersTwoPointConnectorsFilledUpToStep(_ mode: AppearanceMode) throws {
        let width: CGFloat = 320
        let height: CGFloat = 48
        let rep = try render(
            width: width,
            height: height,
            mode: mode,
            CUStageTracker(step: 2, progress: 0.5, showsNames: true, width: width)
        )
        let scale = CGFloat(rep.pixelsWide) / width
        let bg = rgb(rep, x: Int(2 * scale), y: Int(2 * scale))
        let colW = width / 4.0

        // Sample the midpoint between each pair of dots: (0->1) at colW, (1->2) at 2*colW, (2->3) at 3*colW.
        // The dots are 20 pt tall at the top of the tracker, so the connector centerline is at y = 10 pt.
        let dotCenterY = Int(10 * scale)
        let scanYRange = Int(6 * scale)...Int(14 * scale)
        let savedPalette = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        let filledTarget = rgb(CURGB: CU.textRGB)
        let trackTarget = rgb(CURGB: CU.trackerTrackRGB)
        CUPalette.current = savedPalette

        var measuredColours: [(r: Double, g: Double, b: Double)] = []
        for connectorIndex in 0..<3 {
            let x = Int(CGFloat(connectorIndex + 1) * colW * scale)
            let activeYs = scanYRange.filter { y in dist(rgb(rep, x: x, y: y), bg) > 0.04 }
            let thicknessPt = CGFloat(activeYs.count) / scale
            #expect(
                thicknessPt >= 1.5 && thicknessPt <= 3.0,
                "connector \(connectorIndex) thickness=\(thicknessPt) pt expected ~2 pt (\(mode))"
            )
            measuredColours.append(rgb(rep, x: x, y: dotCenterY))
        }

        // Connectors 0 and 1 are before step 2 -> filled (CU.text); connector 2 is after step 2 -> track (CU.trackerTrack).
        #expect(
            dist(measuredColours[0], filledTarget) < dist(measuredColours[0], trackTarget),
            "connector 0 should be filled in \(mode)"
        )
        #expect(
            dist(measuredColours[1], filledTarget) < dist(measuredColours[1], trackTarget),
            "connector 1 should be filled in \(mode)"
        )
        #expect(
            dist(measuredColours[2], trackTarget) < dist(measuredColours[2], filledTarget),
            "connector 2 should remain unfilled track in \(mode)"
        )
    }

    @Test(arguments: AppearanceMode.allCases)
    func downloadsHidesStepperForImportedRowsAndKeepsInLibraryLabel(_ mode: AppearanceMode) throws {
        let activeJob = try decodeJob(
            artist: "Slowdive",
            album: "Pygmalion",
            status: "downloading",
            details: ["album_name": "Pygmalion", "live_progress": ["available": true, "percent": 64.0, "completed_tracks": 7, "total_tracks": 9]]
        )
        let importedJob = try decodeJob(
            artist: "The Blue Nile",
            album: "Hats",
            status: "imported"
        )

        let activeState = AppState(themeID: .cupertino, screen: .downloads)
        activeState.acquisition.showJobs([activeJob])
        let importedState = AppState(themeID: .cupertino, screen: .downloads)
        importedState.acquisition.showJobs([importedJob])

        let size = NSSize(width: 720, height: 280)
        let activeRep = try render(width: size.width, height: size.height, mode: mode, CupertinoDownloads(state: activeState))
        let importedRep = try render(width: size.width, height: size.height, mode: mode, CupertinoDownloads(state: importedState))

        let scale = CGFloat(activeRep.pixelsWide) / size.width
        let bg = rgb(activeRep, x: Int(8 * scale), y: Int(8 * scale))

        // Measure the vertical extent of panel content (from top of panel to bottommost ink pixel).
        let activeInkRows = inkRowCount(in: activeRep, bg: bg, xRange: Int(120 * scale)...Int(440 * scale))
        let importedInkRows = inkRowCount(in: importedRep, bg: bg, xRange: Int(120 * scale)...Int(440 * scale))
        #expect(
            activeInkRows - importedInkRows >= Int(28 * scale),
            "imported row should omit the stepper and be shorter than active row (active=\(activeInkRows)px, imported=\(importedInkRows)px, \(mode))"
        )

        // Verify the imported row still renders the green "In your library" checkmark/label.
        let palette: CUPalette = mode == .night ? .night : .day
        let successTarget = rgb(CURGB: palette.success)
        let hasSuccessTint = hasPixelNear(successTarget, in: importedRep, maxDistance: 0.22)
        #expect(hasSuccessTint, "imported row should keep ✓ In your library in CU.success (\(mode))")
    }

    private func decodeJob(artist: String, album: String, status: String, details: [String: Any]? = nil) throws -> Acquisition {
        let now = Date().timeIntervalSince1970
        var dict: [String: Any] = [
            "id": album,
            "title": album,
            "artist": artist,
            "album": album,
            "status": status,
            "updated_at": now - 120,
            "created_at": now - 600,
        ]
        if let details { dict["details"] = details }
        return try JSONDecoder().decode(Acquisition.self, from: JSONSerialization.data(withJSONObject: dict))
    }

    private func render(width: CGFloat, height: CGFloat, mode: AppearanceMode, _ view: some View) throws -> NSBitmapImageRep {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }

        let size = NSSize(width: width, height: height)
        let host = NSHostingView(
            rootView: view
                .frame(width: size.width, height: size.height, alignment: .topLeading)
                .background(CU.content)
                .environment(\.colorScheme, mode == .night ? .dark : .light)
        )
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.15))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        return rep
    }

    private func inkRowCount(in rep: NSBitmapImageRep, bg: (r: Double, g: Double, b: Double), xRange: ClosedRange<Int>) -> Int {
        var count = 0
        for y in 0..<rep.pixelsHigh {
            if xRange.contains(where: { x in dist(rgb(rep, x: x, y: y), bg) > 0.04 }) {
                count += 1
            }
        }
        return count
    }

    private func hasPixelNear(_ target: (r: Double, g: Double, b: Double), in rep: NSBitmapImageRep, maxDistance: Double) -> Bool {
        for y in stride(from: 0, to: rep.pixelsHigh, by: 2) {
            for x in stride(from: 0, to: rep.pixelsWide, by: 2) {
                if dist(rgb(rep, x: x, y: y), target) < maxDistance {
                    return true
                }
            }
        }
        return false
    }

    private func rgb(_ rep: NSBitmapImageRep, x: Int, y: Int) -> (r: Double, g: Double, b: Double) {
        let c = (rep.colorAt(x: x, y: y) ?? .clear).usingColorSpace(.sRGB) ?? .clear
        return (Double(c.redComponent), Double(c.greenComponent), Double(c.blueComponent))
    }

    private func rgb(CURGB c: CURGB) -> (r: Double, g: Double, b: Double) {
        (Double((c.hex >> 16) & 0xFF) / 255, Double((c.hex >> 8) & 0xFF) / 255, Double(c.hex & 0xFF) / 255)
    }

    private func dist(_ a: (r: Double, g: Double, b: Double), _ b: (r: Double, g: Double, b: Double)) -> Double {
        let dr = a.r - b.r
        let dg = a.g - b.g
        let db = a.b - b.b
        return (dr * dr + dg * dg + db * db).squareRoot()
    }
}
