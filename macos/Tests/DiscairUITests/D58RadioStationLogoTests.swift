import AppKit
import DiscairAudio
@testable import DiscairLibrarian
import Foundation
import SwiftUI
import Testing
@testable import DiscairUI

private func solidPNG(_ color: NSColor, width: Int, height: Int) -> Data {
    let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: width,
        pixelsHigh: height,
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0,
        bitsPerPixel: 0
    )!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    color.setFill()
    NSRect(x: 0, y: 0, width: width, height: height).fill()
    NSGraphicsContext.restoreGraphicsState()
    return rep.representation(using: .png, properties: [:])!
}

private final class FakeStationLogoSource: StationLogoSource, @unchecked Sendable {
    let data: Data
    init(data: Data) { self.data = data }
    func radioLogo(station: String, size: RadioLogoSize) async throws -> ArtworkImageData {
        ArtworkImageData(data: data, contentType: "image/png")
    }
}

/// D5.8 (`docs/plans/MACOS_DESIGN_DETAILS.md`): non-square station logos are aspect-fitted with 3 pt padding on a neutral ground
/// so wide logos (e.g. "3j Radio") are not cropped.
@MainActor
@Suite("D5.8 radio station logo rendering")
struct D58RadioStationLogoTests {
    @Test func squareLogoHasZeroPaddingAndNonSquareLogoHasThreePointPadding() {
        #expect(StationLogo.isSquare(NSSize(width: 128, height: 128)))
        #expect(StationLogo.logoPadding(for: NSSize(width: 128, height: 128)) == 0)

        #expect(!StationLogo.isSquare(NSSize(width: 240, height: 80)))
        #expect(StationLogo.logoPadding(for: NSSize(width: 240, height: 80)) == 3)

        #expect(!StationLogo.isSquare(NSSize(width: 80, height: 240)))
        #expect(StationLogo.logoPadding(for: NSSize(width: 80, height: 240)) == 3)
    }

    private func renderLogo(pngData: Data, stationID: String, size: CGFloat = 96) async throws -> NSBitmapImageRep {
        let saved = CUPalette.current
        CUPalette.current = .day
        defer { CUPalette.current = saved }

        let store = StationLogoStore(media: nil)
        store.configure(source: FakeStationLogoSource(data: pngData))
        let station = RadioStation(id: stationID, name: "3j Radio", proxied: true, playableURL: "https://example.invalid/3j", tags: ["Radio"])
        _ = await store.logo(station: station.id, size: size > 64 ? .large : .small)

        let view = StationLogo(station: station, size: size)
            .environment(\.stationLogos, store)
            .environment(\.colorScheme, .light)
            .frame(width: size, height: size)

        let host = NSHostingView(rootView: view)
        host.frame = NSRect(origin: .zero, size: NSSize(width: size, height: size))
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        try await Task.sleep(for: .milliseconds(150))
        host.layoutSubtreeIfNeeded()

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        return rep
    }

    private func color(in rep: NSBitmapImageRep, point: CGPoint, viewSize: CGFloat) -> NSColor? {
        let px = Int((point.x / viewSize) * CGFloat(rep.pixelsWide))
        let py = Int((point.y / viewSize) * CGFloat(rep.pixelsHigh))
        let clampedX = min(max(px, 0), rep.pixelsWide - 1)
        let clampedY = min(max(py, 0), rep.pixelsHigh - 1)
        return rep.colorAt(x: clampedX, y: clampedY)?.usingColorSpace(.sRGB)
    }

    @Test func wideLogoAspectFitsWithThreePointPaddingOnNeutralGround() async throws {
        let size: CGFloat = 96
        let rep = try await renderLogo(pngData: solidPNG(.red, width: 180, height: 45), stationID: "3j-wide", size: size)

        // Center and horizontal span inset by 3 pt padding should show the red wide logo.
        let center = try #require(color(in: rep, point: CGPoint(x: 48, y: 48), viewSize: size))
        let leftInner = try #require(color(in: rep, point: CGPoint(x: 6, y: 48), viewSize: size))
        let rightInner = try #require(color(in: rep, point: CGPoint(x: 90, y: 48), viewSize: size))
        for c in [center, leftInner, rightInner] {
            #expect(c.redComponent > 0.8 && c.redComponent - c.greenComponent > 0.5 && c.redComponent - c.blueComponent > 0.5,
                    "got r=\(c.redComponent) g=\(c.greenComponent) b=\(c.blueComponent)")
        }

        // 3 pt left/right padding and top/bottom letterbox areas should show the neutral ground, not red.
        let leftPad = try #require(color(in: rep, point: CGPoint(x: 1, y: 48), viewSize: size))
        let rightPad = try #require(color(in: rep, point: CGPoint(x: 94, y: 48), viewSize: size))
        let topNeutral = try #require(color(in: rep, point: CGPoint(x: 48, y: 12), viewSize: size))
        let bottomNeutral = try #require(color(in: rep, point: CGPoint(x: 48, y: 84), viewSize: size))
        for c in [leftPad, rightPad, topNeutral, bottomNeutral] {
            #expect(abs(c.redComponent - c.blueComponent) < 0.1)
        }
    }

    @Test func squareLogoFillsWithoutPadding() async throws {
        let size: CGFloat = 96
        let rep = try await renderLogo(pngData: solidPNG(.blue, width: 128, height: 128), stationID: "3j-square", size: size)

        let leftEdge = try #require(color(in: rep, point: CGPoint(x: 1, y: 48), viewSize: size))
        let center = try #require(color(in: rep, point: CGPoint(x: 48, y: 48), viewSize: size))
        let rightEdge = try #require(color(in: rep, point: CGPoint(x: 94, y: 48), viewSize: size))
        for c in [leftEdge, center, rightEdge] {
            #expect(c.blueComponent > 0.8 && c.redComponent < 0.2)
        }
    }
}
