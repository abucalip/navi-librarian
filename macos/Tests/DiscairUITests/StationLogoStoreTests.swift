import AppKit
import DiscairAudio
@testable import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

private func png(_ color: NSColor) -> Data {
    let image = NSImage(size: NSSize(width: 4, height: 4))
    image.lockFocus(); color.setFill(); NSRect(x: 0, y: 0, width: 4, height: 4).fill(); image.unlockFocus()
    return NSBitmapImageRep(data: image.tiffRepresentation!)!.representation(using: .png, properties: [:])!
}

private final class FakeLogos: StationLogoSource, @unchecked Sendable {
    var data = png(.red)
    func radioLogo(station: String, size: RadioLogoSize) async throws -> ArtworkImageData {
        ArtworkImageData(data: data, contentType: "image/png")
    }
}

@MainActor
struct StationLogoStoreTests {
    /// A changed logo must be asked for again; the copy on disk used to be read back instead.
    @Test func aChangedLogoIsNotReadBackFromTheDiskCache() async throws {
        let media = MediaCache(root: FileManager.default.temporaryDirectory.appending(path: "discair-logo-\(UUID().uuidString)"))
        media.isEnabled = true; media.setScope("u")
        let source = FakeLogos()
        let store = StationLogoStore(media: media)
        store.configure(source: source)
        let old = png(.red), new = png(.blue)
        source.data = old
        _ = await store.logo(station: "1", size: .small)
        source.data = new
        store.forget(station: "1")
        _ = await store.logo(station: "1", size: .small)
        #expect(media.data(for: StationLogoStore.key("1", .small), ext: "img") == new)
    }
}
