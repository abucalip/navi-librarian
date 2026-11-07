import DiscairAudio
import DiscairCore
import DiscairLibrarian
import Foundation
import Observation

/// One sonic path from the playing song to a chosen song (Server V2 Phase 7). The steps are the server's order;
/// the score is not used. Opened from a song or queue row, asked only while the sheet is open, never saved.
@MainActor @Observable
public final class SonicPathModel: Identifiable {
    public enum Phase: Equatable { case loading, ready([QueueItem]), empty, failed(String) }
    public let id = UUID()
    public let start: QueueItem
    public let target: QueueItem
    public private(set) var phase = Phase.loading
    /// Steps asked for one path, start and end included.
    static let steps = 10

    public init(start: QueueItem, target: QueueItem) { self.start = start; self.target = target }

    static func item(_ t: SonicTrack) -> QueueItem {
        QueueItem(songID: t.songID, title: t.title, artist: t.artist.isEmpty ? "Unknown artist" : t.artist, album: t.album,
                  albumID: t.albumID, coverArt: t.coverArt, duration: t.duration, mbid: t.mbid)
    }

    /// Asks the server (`fetch` takes start, end and the step count) and settles on a phase.
    public func load(fetch: (String, String, Int) async throws -> SonicResponse) async {
        phase = .loading
        do {
            let response = try await fetch(start.songID, target.songID, Self.steps)
            var seen = Set<String>()
            let steps = response.tracks.filter { seen.insert($0.songID).inserted }.map(Self.item)
            phase = steps.count >= 2 ? .ready(steps) : .empty
        } catch {
            phase = .failed((error as? DiscairError).map(AcquisitionModel.text) ?? "Could not find a sonic path.")
        }
    }
}
