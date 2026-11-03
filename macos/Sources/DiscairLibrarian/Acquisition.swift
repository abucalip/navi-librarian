import Foundation

/// What the Librarian answered to Get (album or song). A refusal such as `settings_required` arrives as HTTP 200 with
/// `ok: false`, so callers must read `ok` and `status`, never the HTTP code alone (Android contract, Phase 0).
public struct AcquireResult: Decodable, Equatable, Sendable {
    public let ok: Bool
    public let status: String?
    public let message: String?
    public let artist: String?
    public let album: String?

    enum CodingKeys: String, CodingKey { case ok, status, message, artist, album }

    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        ok = try c.decodeIfPresent(Bool.self, forKey: .ok) ?? false
        status = try c.decodeIfPresent(String.self, forKey: .status)
        message = try c.decodeIfPresent(String.self, forKey: .message)
        artist = try c.decodeIfPresent(String.self, forKey: .artist)
        album = try c.decodeIfPresent(String.self, forKey: .album)
    }

    public init(ok: Bool, status: String?, message: String?, artist: String? = nil, album: String? = nil) {
        self.ok = ok; self.status = status; self.message = message; self.artist = artist; self.album = album
    }
}

/// Live download progress of one job (only present while downloading).
public struct LiveProgress: Decodable, Equatable, Sendable {
    public let available: Bool
    public let totalTracks: Int?
    public let completedTracks: Int?
    public let percent: Double?
    public let speedBytesPerSecond: Double?

    enum CodingKeys: String, CodingKey {
        case available, percent
        case totalTracks = "total_tracks"
        case completedTracks = "completed_tracks"
        case speedBytesPerSecond = "speed_bytes_per_second"
    }
}

/// One acquisition job from `GET /api/acquisitions`. Unknown fields are ignored.
public struct Acquisition: Decodable, Equatable, Sendable, Identifiable {
    public struct Details: Decodable, Equatable, Sendable {
        public let kind: String?
        public let albumName: String?
        public let trackTitle: String?
        public let message: String?
        public let liveProgress: LiveProgress?

        enum CodingKeys: String, CodingKey {
            case kind, message
            case albumName = "album_name"
            case trackTitle = "track_title"
            case liveProgress = "live_progress"
        }
    }

    public let artist: String
    public let album: String
    public let status: String
    public let details: Details?
    public let createdAt: Double?
    public let updatedAt: Double?

    public var id: String { "\(artist.lowercased())|\(album.lowercased())" }
    /// A song job reads as "Title (song on Album)" in `album`; this gives the plain title to show.
    public var title: String { details?.trackTitle ?? album }
    public var isSong: Bool { details?.kind == "track" }

    enum CodingKeys: String, CodingKey {
        case artist, album, status, details
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    /// Where a job stands, grouped for the ticker and the Downloads badge.
    public enum Phase: Equatable, Sendable { case working, queued, imported, failed, other }

    public var phase: Phase {
        switch status {
        case "downloading", "download_complete_waiting_for_folder", "importing", "searching", "monitoring": .working
        case "requested", "queued", "queued_unconfirmed", "retry_requested", "recovery_started": .queued
        case "imported": .imported
        case "no_matches", "queue_failed", "settings_required", "slskd_error", "monitor_error", "monitor_recovery_failed",
             "source_switch_failed", "recovery_unavailable": .failed
        default: .other
        }
    }
}

/// The four feedback actions of `POST /api/discovery/feedback`.
public enum FeedbackAction: String, Sendable {
    case save
    case dismiss
    case dismissArtist = "dismiss_artist"
    case removeForMe = "remove_for_me"
}

struct AcquisitionsPayload: Decodable { let acquisitions: [Acquisition] }
