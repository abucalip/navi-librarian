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
    private(set) var downloads: [Int: GetState] = [:]
    private(set) var refreshNotice: String?
    private var downloadKeys: [Int: PlaylistInboxAcquisitionKey] = [:]
    @ObservationIgnored private var downloadScope = UUID()
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
        downloadScope = UUID()
        downloads = [:]
        downloadKeys = [:]
        refreshNotice = nil
        detail = .idle
        editionID = id
    }

    func close() {
        detailRequest = UUID()
        downloadScope = UUID()
        downloads = [:]
        downloadKeys = [:]
        refreshNotice = nil
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

    func loadDetail(id: Int64, refreshing: Bool = false) async {
        guard let librarian, editionID == id else { return }
        let request = UUID()
        detailRequest = request
        if !refreshing { detail = .loading }
        refreshNotice = nil
        do {
            let edition = try await librarian.playlistInboxEdition(id: id)
            guard detailRequest == request, !Task.isCancelled else { return }
            detail = .loaded(edition)
        } catch {
            guard detailRequest == request, !Task.isCancelled else { return }
            if refreshing { refreshNotice = ErrorMapping.map(error).summary }
            else { detail = .failed(ErrorMapping.map(error).summary) }
        }
    }

    func downloadState(for track: PlaylistInboxTrack, jobs: [Acquisition]) -> GetState {
        if track.matchState == "owned" { return .requested("Owned") }
        if let attempt = downloads[track.position] {
            switch attempt {
            case .pending, .failed: return attempt
            default: break
            }
        }
        if let key = downloadKeys[track.position] ?? track.acquisitionKey,
           let job = jobs.first(where: { $0.artist == key.artist && $0.album == key.jobAlbum }) {
            if job.status == "imported" { return .requested("Imported · waiting for library scan") }
            if Self.retryable(job.status) { return .failed(AcquisitionModel.statusText(job)) }
            return AcquisitionModel.describe(job)
        }
        if let status = track.acquisitionStatus {
            if status == "imported" { return .requested("Imported · waiting for library scan") }
            let message = status.replacingOccurrences(of: "_", with: " ").capitalized
            return Self.retryable(status) ? .failed(message) : .requested(message)
        }
        return downloads[track.position] ?? .idle
    }

    private static func retryable(_ status: String) -> Bool {
        ["no_matches", "queue_failed", "settings_required", "slskd_error", "monitor_error", "monitor_timeout",
         "monitor_recovery_failed", "source_switch_failed", "recovery_unavailable", "download_failed",
         "download_complete_move_failed", "dismissed"].contains(status)
    }

    func download(position: Int, jobs: [Acquisition]) async {
        guard let librarian, let id = editionID, case .loaded(let detail) = self.detail,
              let track = detail.tracks.first(where: { $0.position == position }), track.matchState != "owned" else { return }
        switch downloadState(for: track, jobs: jobs) {
        case .pending, .requested: return
        case .idle, .failed: break
        }
        let scope = downloadScope
        downloads[position] = .pending
        do {
            let result = try await librarian.downloadInboxTrack(editionID: id, position: position)
            guard downloadScope == scope, !Task.isCancelled else { return }
            if let artist = result.artist, let album = result.jobAlbum {
                // Use the server's synthetic key, including when the saved track has no album.
                downloadKeys[position] = PlaylistInboxAcquisitionKey(artist: artist, jobAlbum: album)
            }
            let message = result.message ?? "Requested"
            switch result.status {
            case "owned": downloads[position] = .requested("Refreshing ownership…")
            case "imported": downloads[position] = .requested("Imported · waiting for library scan")
            case "already_in_progress", "importing": downloads[position] = .requested(message)
            default:
                if !result.ok || result.status.map(Self.retryable) == true {
                    downloads[position] = .failed(result.message ?? "The Librarian could not download this track.")
                } else {
                    downloads[position] = .requested(message)
                }
            }
            await loadDetail(id: id, refreshing: true)
        } catch {
            guard downloadScope == scope, !Task.isCancelled else { return }
            downloads[position] = .failed(AcquisitionModel.text(ErrorMapping.map(error)))
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
