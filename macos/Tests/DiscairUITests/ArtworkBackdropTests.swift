import AppKit
import DiscairCore
import DiscairNavidrome
import SwiftUI
import Testing
@testable import DiscairUI

private func stripedPNG() -> Data {
    let img = NSImage(size: NSSize(width: 300, height: 300))
    img.lockFocus()
    for i in 0..<6 {
        NSColor(hue: CGFloat(i) / 6, saturation: 0.9, brightness: 1, alpha: 1).setFill()
        NSRect(x: i * 50, y: 0, width: 50, height: 300).fill()
    }
    img.unlockFocus()
    return NSBitmapImageRep(data: img.tiffRepresentation!)!.representation(using: .png, properties: [:])!
}

private struct StripedTransport: HTTPTransport {
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        (stripedPNG(), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

/// The backdrop on Now Playing and the artist banner stands alone (no placeholder under the image); the image has to load
/// and draw there. A bare `Group` that was empty until the image arrived never started its load in that position.
@MainActor
@Suite("Artwork backdrop", .serialized)
struct ArtworkBackdropTests {
    @Test func aStandaloneBlurredArtworkLoadsAndDrawsTheCover() async throws {
        RenderMode.offscreenScreenshot = true            // the blur itself does not render in this capture path
        defer { RenderMode.offscreenScreenshot = false }
        let store = ArtworkStore(transport: StripedTransport())
        store.configure(try StreamURLBuilder(baseURL: URL(string: "http://192.168.1.87:4533")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw"))))
        let album = AlbumItem(id: 1, title: "t", artist: "a", year: 0, genre: "", format: "", owned: true, hue: 200, coverArt: "al-1")
        let host = NSHostingView(rootView: ZStack { Color.gray; BlurredArtwork(album: album) }.environment(\.artwork, store).frame(width: 500, height: 400))
        host.frame = NSRect(x: 0, y: 0, width: 500, height: 400)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.makeKeyAndOrderFront(nil)
        var colours = Set<Int>()
        for _ in 0..<30 where colours.count < 4 {
            try await Task.sleep(for: .milliseconds(100))
            let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
            host.cacheDisplay(in: host.bounds, to: rep)
            colours = []
            for ix in 0..<20 {
                guard let c = rep.colorAt(x: (rep.pixelsWide - 1) * ix / 19, y: rep.pixelsHigh / 2)?.usingColorSpace(.sRGB) else { continue }
                colours.insert(Int(c.redComponent * 7) << 6 | Int(c.greenComponent * 7) << 3 | Int(c.blueComponent * 7))
            }
        }
        window.orderOut(nil)
        #expect(colours.count >= 4, "the cover should be drawn across the backdrop, not left as the grey behind it (\(colours.count) colours)")
    }
}
