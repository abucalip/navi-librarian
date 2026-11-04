import DiscairAudio
import Foundation
import Observation

/// The Settings side of the optional media cache: the switch (remembered, off by default), the size readout and Clear.
@MainActor
@Observable
public final class CacheModel {
    public var isEnabled: Bool {
        didSet { defaults.set(isEnabled, forKey: Self.key); media.isEnabled = isEnabled }
    }
    /// Bytes on disk, as of the last `refresh`.
    public private(set) var usedBytes: Int64 = 0
    public let limit: Int64
    public let media: MediaCache
    @ObservationIgnored private let defaults: UserDefaults
    private static let key = "discair.mediaCacheEnabled"

    public init(media: MediaCache, defaults: UserDefaults = .standard) {
        self.media = media
        self.defaults = defaults
        limit = MediaCache.defaultLimit
        isEnabled = defaults.bool(forKey: Self.key)
        media.isEnabled = isEnabled
    }

    /// Reads the folder size off the main thread.
    public func refresh() async {
        let media = self.media
        usedBytes = await Task.detached { media.usedBytes() }.value
    }

    public func clear() async {
        let media = self.media
        await Task.detached { media.clear() }.value
        usedBytes = 0
    }

    /// "412 MB of 2 GB".
    public var readout: String {
        let f = ByteCountFormatter(); f.countStyle = .file
        return "\(f.string(fromByteCount: usedBytes)) of \(f.string(fromByteCount: limit))"
    }
}
