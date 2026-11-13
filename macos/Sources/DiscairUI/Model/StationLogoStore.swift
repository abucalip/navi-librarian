import AppKit
import DiscairAudio
import DiscairLibrarian
import SwiftUI

/// What the logo store asks of the Librarian. `LibrarianClient` is the real one; tests pass a fake.
public protocol StationLogoSource: Sendable {
    func radioLogo(station: String, size: RadioLogoSize) async throws -> ArtworkImageData
}
extension LibrarianClient: StationLogoSource {}

/// Station logos (S2.5): fetched once per station and size, kept in memory and, when the media cache is on, on disk.
/// The server always answers with an image (a generated tile when it found none), so the Mac never draws its own logo.
/// A failed read is remembered for five minutes only, so a logo that failed while the server was down is asked for again.
@MainActor
@Observable
public final class StationLogoStore {
    /// Counts resets and connections; views include it in their task id so they ask again after a change.
    public private(set) var generation = 0

    @ObservationIgnored private var source: (any StationLogoSource)?
    @ObservationIgnored private let media: MediaCache?
    @ObservationIgnored private let cache = NSCache<NSString, NSImage>()
    @ObservationIgnored private var failed: [String: Date] = [:]
    @ObservationIgnored private var loads: [String: Task<NSImage?, Never>] = [:]
    @ObservationIgnored var now: () -> Date = { .now }
    static let retryAfter: TimeInterval = 300

    public init(media: MediaCache? = nil) { self.media = media }

    public func configure(source: (any StationLogoSource)?) {
        self.source = source
        forgetAll()
    }

    /// Settings "Reset saved data", and a logo that was changed or reset: asks again for everything.
    public func resetAll() { forgetAll() }

    /// A logo that was just changed or reset: only that station is asked for again.
    public func forget(station: String) {
        for size in [RadioLogoSize.small, .large] {
            let key = Self.key(station, size)
            cache.removeObject(forKey: key as NSString)
            failed[key] = nil
            loads[key]?.cancel(); loads[key] = nil
        }
        generation += 1
    }

    private func forgetAll() {
        cache.removeAllObjects(); failed.removeAll()
        loads.values.forEach { $0.cancel() }; loads.removeAll()
        generation += 1
    }

    static func key(_ station: String, _ size: RadioLogoSize) -> String { "radio-logo|\(station)|\(size.rawValue)" }

    /// The logo, or nil while it cannot be had. One request per station and size; a second ask joins the first.
    public func logo(station: String, size: RadioLogoSize) async -> NSImage? {
        let key = Self.key(station, size)
        if let hit = cache.object(forKey: key as NSString) { return hit }
        if let data = media?.data(for: key, ext: "img"), let image = NSImage(data: data) {
            cache.setObject(image, forKey: key as NSString, cost: data.count); return image
        }
        if let at = failed[key] {
            if now().timeIntervalSince(at) < Self.retryAfter { return nil }
            failed[key] = nil
        }
        guard let source else { return nil }
        let task: Task<NSImage?, Never>
        if let running = loads[key] { task = running } else {
            task = Task { [weak self] in
                guard let got = try? await source.radioLogo(station: station, size: size),
                      let image = NSImage(data: got.data) else { await self?.markFailed(key); return nil }
                await self?.keep(image, data: got.data, key: key)
                return image
            }
            loads[key] = task
        }
        let image = await task.value
        if loads[key] == task { loads[key] = nil }
        return image
    }

    private func markFailed(_ key: String) { failed[key] = now() }

    private func keep(_ image: NSImage, data: Data, key: String) {
        cache.setObject(image, forKey: key as NSString, cost: data.count)
        media?.store(data: data, key: key, ext: "img")
    }
}

private struct StationLogoKey: EnvironmentKey { static let defaultValue: StationLogoStore? = nil }
extension EnvironmentValues {
    var stationLogos: StationLogoStore? {
        get { self[StationLogoKey.self] }
        set { self[StationLogoKey.self] = newValue }
    }
}

/// A station's logo at a fixed size. Until it arrives the square is a plain neutral fill: the server's generated tile is
/// the only placeholder logo there is.
struct StationLogo: View {
    let station: RadioStation
    var size: CGFloat = 34
    var radiusFraction: CGFloat = 0.22
    @Environment(\.stationLogos) private var store
    @State private var image: NSImage?

    var body: some View {
        RoundedRectangle(cornerRadius: size * radiusFraction, style: .continuous)
            .fill(CU.bgFill)
            .overlay { if let image { Image(nsImage: image).resizable().scaledToFill() } }
            .clipShape(RoundedRectangle(cornerRadius: size * radiusFraction, style: .continuous))
            .frame(width: size, height: size)
            .task(id: "\(station.id)@\(size > 64 ? 512 : 128)|\(store?.generation ?? 0)") {
                guard let store else { image = nil; return }
                image = await store.logo(station: station.id, size: size > 64 ? .large : .small)
            }
            .accessibilityHidden(true)       // the station's name is read by the row
    }
}
