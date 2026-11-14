import Foundation

/// What the Notification Center widget shows (contract section 10: now playing only). The app writes it, the widget
/// reads it. They share a folder instead of an app group because the app is ad-hoc signed (no team, so no group
/// container); the widget is allowed to read that one folder, read-only (`Packaging/DiscairWidget.entitlements`).
public struct NowPlayingSnapshot: Codable, Equatable, Sendable {
    public var title: String
    public var artist: String
    public var album: String
    /// Seconds. 0 when unknown.
    public var duration: Double
    /// Where the song was at `updatedAt`.
    public var position: Double
    public var isPlaying: Bool
    public var updatedAt: Date
    /// File name of the cover inside the share folder; nil when the song has none (yet).
    public var coverFile: String?
    /// True while a radio station plays: `title` is the station, the cover is its logo, there is no length and no position.
    /// Optional so a file written before radio still decodes (S2-2 item 7).
    public var isLive: Bool?

    public init(title: String, artist: String, album: String, duration: Double, position: Double,
                isPlaying: Bool, updatedAt: Date = Date(), coverFile: String? = nil, isLive: Bool? = nil) {
        self.title = title; self.artist = artist; self.album = album
        self.duration = duration; self.position = position
        self.isPlaying = isPlaying; self.updatedAt = updatedAt; self.coverFile = coverFile; self.isLive = isLive
    }

    /// A station is playing (an absent `isLive` means a song).
    public var live: Bool { isLive == true }

    /// How long a live snapshot is believed when nobody updates it (the app quit or crashed while a station played).
    public static let liveLifetime: TimeInterval = 6 * 3600

    /// The song position at `now`: moves on while playing, clamped to the song.
    public func position(at now: Date) -> Double {
        let moved = isPlaying ? max(0, now.timeIntervalSince(updatedAt)) : 0
        let p = position + moved
        return duration > 0 ? min(max(p, 0), duration) : max(p, 0)
    }

    /// Start and end dates for a self-updating progress bar (`ProgressView(timerInterval:)`); nil without a duration.
    public func progressInterval(at now: Date) -> ClosedRange<Date>? {
        guard duration > 0 else { return nil }
        let start = now.addingTimeInterval(-position(at: now))
        return start...start.addingTimeInterval(duration)
    }

    /// When a playing song will have ended if nobody updated the file (the app quit or crashed mid-song); nil when paused or
    /// the length is unknown. The widget stops showing the song then instead of a full bar forever.
    public var expectedEnd: Date? {
        if live { return updatedAt.addingTimeInterval(Self.liveLifetime) }
        guard isPlaying, duration > 0 else { return nil }
        return updatedAt.addingTimeInterval(max(0, duration - position) + 5)
    }

    /// True when only the clock moved: same song, same state, and the position is where playing would have put it.
    public func sameState(as other: NowPlayingSnapshot, tolerance: Double = 2) -> Bool {
        guard title == other.title, artist == other.artist, album == other.album, duration == other.duration,
              isPlaying == other.isPlaying, coverFile == other.coverFile, live == other.live else { return false }
        return abs(other.position(at: other.updatedAt) - position(at: other.updatedAt)) <= tolerance
    }
}

/// The shared folder and its two files. All functions take the folder so tests use a temporary one.
public enum NowPlayingShare {
    public static let widgetKind = "app.discair.mac.nowplaying"
    public static let snapshotName = "now-playing.json"
    public static let coverName = "cover.jpg"

    /// `~/Library/Application Support/Discair/Widget`, from the real home folder: inside the sandbox
    /// `NSHomeDirectory()` is the extension's own container, so the passwd entry is used.
    public static var defaultFolder: URL {
        let home = getpwuid(getuid()).flatMap { $0.pointee.pw_dir }.map { String(cString: $0) } ?? NSHomeDirectory()
        return URL(fileURLWithPath: home, isDirectory: true)
            .appending(path: "Library/Application Support/Discair/Widget", directoryHint: .isDirectory)
    }

    /// Writes the cover first, then the snapshot, so a reader never sees a snapshot that names a missing cover.
    public static func write(_ snapshot: NowPlayingSnapshot, cover: Data?, in folder: URL) throws {
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        var snap = snapshot
        if let cover {
            try cover.write(to: folder.appending(path: coverName), options: .atomic)
            snap.coverFile = coverName
        }
        let data = try JSONEncoder().encode(snap)
        try data.write(to: folder.appending(path: snapshotName), options: .atomic)
    }

    /// Nothing is playing: the widget shows its idle face.
    public static func clear(in folder: URL) {
        try? FileManager.default.removeItem(at: folder.appending(path: snapshotName))
        try? FileManager.default.removeItem(at: folder.appending(path: coverName))
    }

    public static func read(in folder: URL) -> NowPlayingSnapshot? {
        guard let data = try? Data(contentsOf: folder.appending(path: snapshotName)) else { return nil }
        return try? JSONDecoder().decode(NowPlayingSnapshot.self, from: data)
    }

    public static func coverData(for snapshot: NowPlayingSnapshot, in folder: URL) -> Data? {
        guard let name = snapshot.coverFile, name == coverName else { return nil }   // only the file this type writes
        return try? Data(contentsOf: folder.appending(path: name))
    }
}
