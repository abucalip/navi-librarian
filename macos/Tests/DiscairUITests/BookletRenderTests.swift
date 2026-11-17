import AppKit
import DiscairCore
@testable import DiscairLibrarian
import DiscairNavidrome
import SwiftUI
import Testing
@testable import DiscairUI

/// A page as a plain colour, so the stand-in pages of the render tests are decoded by the real `ArtworkStore` path.
private struct PageTransport: HTTPTransport {
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let id = Int(request.url?.path.split(separator: "/").last ?? "") ?? 0
        let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 280, pixelsHigh: 280, bitsPerSample: 8, samplesPerPixel: 4,
                                   hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        let paper = id >= 100 ? NSColor(red: 0.7, green: 0.15, blue: 0.2, alpha: 1) : NSColor(red: 0.93, green: 0.9, blue: 0.84, alpha: 1)
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
        paper.setFill(); NSRect(x: 0, y: 0, width: 280, height: 280).fill()
        NSGraphicsContext.restoreGraphicsState()
        return (rep.representation(using: .png, properties: [:])!, HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil,
                                                                                      headerFields: ["Content-Type": "image/png"])!)
    }
}

/// A server that never answers, so a page stays in its loading state.
private struct HangTransport: HTTPTransport {
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        try await Task.sleep(for: .seconds(600))
        throw URLError(.timedOut)
    }
}

/// Renders the Booklet sheet in the states of `docs/design/macos-paths-booklet/pages/mockups.html` (`booklet-spread`, `booklet-page`,
/// `booklet-extra`, `booklet-single`, `booklet-min`, `booklet-loading`) to PNG, to be put beside the mockups' PNGs. Output goes to
/// `DISCAIR_SCREENSHOT_DIR` (or a temp folder) as `cupertino-booklet-<state>.png`. The PDF state is not rendered: `ImageRenderer` and
/// offscreen hosting cannot draw `PDFView`, so its look is checked by hand in a real window. Each state first checks the inputs that
/// make it that state. Pages are plain stand-ins served by a fake transport; no server is asked.
@MainActor
@Suite("Booklet render", .serialized)
struct BookletRenderTests {
    private func pic(_ id: Int, _ type: String = "Booklet", edition: String = "2001 US CD", comment: String = "") -> ArtworkPicture {
        ArtworkPicture(imageID: id, release: "r", releases: ["r"], edition: edition, types: [type], comment: comment, width: 1400, height: 1400)
    }

    private func booklet(pages: Int = 16, extras: [String] = ["Obi", "Sticker", "Poster"], edition: String = "2001 US CD") -> BookletView {
        BookletView(edition: edition,
                    pages: (1...pages).map { pic($0, edition: edition, comment: $0 == 4 ? "Inner spread with personnel and session photo" : "") },
                    extras: extras.enumerated().map { pic(100 + $0, $1, edition: edition) })
    }

    private enum Scenario { case spread, page, extra, single, narrow, loading }

    private func render(_ scenario: Scenario, name: String, size: CGSize = CGSize(width: 1120, height: 740)) async throws {
        RenderMode.offscreenScreenshot = true
        let editions = [booklet(), booklet(pages: 2, edition: "1957 US LP"), booklet(pages: 24, edition: "2005 JP CD")]
        let books = scenario == .single ? [booklet(extras: [])] : editions
        let store = ArtworkStore(transport: PageTransport())
        let transport: any HTTPTransport = scenario == .loading ? HangTransport() : PageTransport()
        store.configure(librarian: try LibrarianClient(baseURL: URL(string: "https://lib.example.ts.net")!,
                                                       credential: Credential(username: "o", password: "p"), transport: transport))
        // The inputs that make each scenario its mockup state.
        let first = books[0]
        #expect(BookletLayout.showsSidebar(books) == (scenario != .single))
        switch scenario {
        case .spread, .loading: #expect(BookletLayout.items(first, mode: .spread).count == 12 && BookletLayout.position(BookletLayout.items(first, mode: .spread)[2], pageCount: 16) == "Pages 4–5 of 16")
        case .page: #expect(BookletLayout.items(first, mode: .page).count == 19)
        case .extra: #expect(BookletLayout.items(first, mode: .spread)[9].isExtra)
        case .single: #expect(books.count == 1 && first.extras.isEmpty && BookletLayout.filmstrip(BookletLayout.items(first, mode: .spread)).extras.isEmpty)
        case .narrow: #expect(BookletLayout.isNarrow(width: size.width) && BookletLayout.showsEditionMenu(books, narrow: true))
        }
        let start: Int
        switch scenario {
        case .spread, .loading, .narrow: start = 2
        case .page: start = 3
        case .extra: start = 9
        case .single: start = 2
        }
        let view = BookletSheet(title: "’Round About Midnight", booklets: books, startIndex: start, startMode: scenario == .page ? .page : .spread) {}
            .environment(\.artwork, store)
            .frame(width: size.width, height: size.height)
        let host = NSHostingView(rootView: view)
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        try await Task.sleep(for: .seconds(1.5))
        host.layoutSubtreeIfNeeded()
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        var colours = Set<Int>()
        for ix in 0..<48 { for iy in 0..<48 {
            guard let c = rep.colorAt(x: (rep.pixelsWide - 1) * ix / 47, y: (rep.pixelsHigh - 1) * iy / 47)?.usingColorSpace(.sRGB) else { continue }
            colours.insert(Int(c.redComponent * 15) << 8 | Int(c.greenComponent * 15) << 4 | Int(c.blueComponent * 15))
        } }
        #expect(colours.count >= 4, "render looks blank (\(colours.count) distinct colours)")
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try png.write(to: dir.appendingPathComponent("cupertino-booklet-\(name).png"))
    }

    @Test func rendersSpread() async throws { try await render(.spread, name: "spread") }
    @Test func rendersPage() async throws { try await render(.page, name: "page") }
    @Test func rendersExtra() async throws { try await render(.extra, name: "extra") }
    @Test func rendersSingle() async throws { try await render(.single, name: "single") }
    @Test func rendersNarrow() async throws { try await render(.narrow, name: "min", size: CGSize(width: 760, height: 600)) }
    @Test func rendersLoading() async throws { try await render(.loading, name: "loading") }
}
