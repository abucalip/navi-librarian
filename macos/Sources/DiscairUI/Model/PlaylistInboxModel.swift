import DiscairAudio
import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Foundation
import Observation

@MainActor
@Observable
final class PlaylistInboxModel {
    enum Load<Value> {
        case idle, loading, loaded(Value), failed(String)
    }

    private(set) var shelf: Load<PlaylistInbox> = .idle
    private(set) var detail: Load<PlaylistInboxDetail> = .idle
    private(set) var editionID: Int64?
    private(set) var connectionRevision = 0
    private var librarian: LibrarianClient?
    @ObservationIgnored private var shelfRequest = UUID()
    @ObservationIgnored private var detailRequest = UUID()
    var isConnected: Bool { librarian != nil }

    func configure(librarian: LibrarianClient?) {
        self.librarian = librarian
        connectionRevision += 1
        shelfRequest = UUID()
        shelf = .idle
        close()
    }

    func open(_ id: Int64) {
        detailRequest = UUID()
        detail = .idle
        editionID = id
    }

    func close() {
        detailRequest = UUID()
        detail = .idle
        editionID = nil
    }

    func loadShelf() async {
        guard let librarian else { return }
        let request = UUID()
        shelfRequest = request
        shelf = .loading
        do {
            let inbox = try await librarian.playlistInbox()
            guard shelfRequest == request, !Task.isCancelled else { return }
            shelf = .loaded(inbox)
        } catch {
            guard shelfRequest == request, !Task.isCancelled else { return }
            shelf = .failed(ErrorMapping.map(error).summary)
        }
    }

    func loadDetail(id: Int64) async {
        guard let librarian, editionID == id else { return }
        let request = UUID()
        detailRequest = request
        detail = .loading
        do {
            let edition = try await librarian.playlistInboxEdition(id: id)
            guard detailRequest == request, !Task.isCancelled else { return }
            detail = .loaded(edition)
        } catch {
            guard detailRequest == request, !Task.isCancelled else { return }
            detail = .failed(ErrorMapping.map(error).summary)
        }
    }

    static func playbackItems(for detail: PlaylistInboxDetail) -> [QueueItem] {
        guard let count = detail.edition.ownedCount, count > 0 else { return [] }
        return detail.tracks.compactMap { track -> QueueItem? in
            guard track.matchState == "owned", let songID = track.songID, isValidSongID(songID) else { return nil }
            return QueueItem(songID: songID, title: track.displayTitle, artist: track.artist ?? "",
                             album: track.album ?? "", duration: Double(max(0, track.durationMs ?? 0)) / 1_000,
                             mbid: track.recordingMBID)
        }
    }
}

extension PlaylistInboxTrack {
    var displayTitle: String {
        guard let title, !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return "Untitled track" }
        return title
    }
}
