import DiscairCore
import DiscairLibrarian
import Foundation
import Observation

/// What the blocklist needs of the Librarian. `LibrarianClient` is the real one; tests pass a fake.
public protocol BlocklistSource: Sendable {
    func blocklist() async throws -> Blocklist
    func blockGenre(_ genre: String) async throws
    func unblockGenre(_ genre: String) async throws
    func unblockArtist(_ artist: String) async throws
    func setArtistLean(_ artist: String, _ lean: ArtistLeanKind, genres: [String]) async throws
    func clearArtistLean(_ artist: String) async throws
}
extension LibrarianClient: BlocklistSource {}

/// Star Operation S2c. Settings › Blocklist lists blocked genres, artists hidden with Not this artist and artists marked More or
/// Less like this, each with a button that lifts it. The same model sends the album menu's More like this, Less like this and
/// Block genre. A block hides picks only, never the library or Saved. Read when the tab opens; nothing polls.
@MainActor
@Observable
public final class BlocklistModel {
    public enum Phase: Equatable { case idle, loading, loaded, failed(String) }

    public private(set) var phase: Phase = .idle
    public private(set) var list = Blocklist()
    /// A lift is on its way to the server.
    public private(set) var busy = false
    /// The answer to the last menu action or refused change: a sentence the app shows in its notice.
    public private(set) var note: String?
    @ObservationIgnored private var source: (any BlocklistSource)?
    /// Called with a short sentence after a menu action, so the window's notice shows it.
    @ObservationIgnored public var onNotice: (String) -> Void = { _ in }
    /// Called after a genre was blocked, so the open Discover list is read again without it.
    @ObservationIgnored public var onBlocked: () -> Void = {}

    public init() {}

    public func configure(source: (any BlocklistSource)?) {
        self.source = source
        if source == nil { phase = .idle; list = Blocklist(); note = nil; busy = false }
    }

    public func load() async {
        guard let source else { return }
        if phase != .loaded { phase = .loading }
        do { list = try await source.blocklist(); phase = .loaded; note = nil }
        catch { phase = .failed(StationsModel.message(error)) }
    }

    // MARK: Lifting

    public func unblockGenre(_ genre: String) async { await lift { try await $0.unblockGenre(genre) } }
    public func unblockArtist(_ artist: String) async { await lift { try await $0.unblockArtist(artist) } }
    public func clearLean(_ artist: String) async { await lift { try await $0.clearArtistLean(artist) } }

    /// Sends the change, then reads the lists again so the screen shows what the server holds.
    private func lift(_ send: (any BlocklistSource) async throws -> Void) async {
        guard let source, !busy else { return }
        busy = true; defer { busy = false }
        do { try await send(source); note = nil; await load() }
        catch { note = StationsModel.message(error) }
    }

    // MARK: Album menu

    /// The genre the menu offers to block: the album's own (the Librarian matches on the album's genres), or nil when it has none.
    public static func blockableGenre(of album: AlbumItem) -> String? {
        let g = album.genre.split(whereSeparator: \.isWhitespace).joined(separator: " ")
        return g.isEmpty ? nil : g
    }

    public func lean(_ kind: ArtistLeanKind, on album: AlbumItem) async {
        guard let source else { onNotice("Not connected to the Librarian. Check Settings."); return }
        let genres = Self.blockableGenre(of: album).map { [$0] } ?? []
        do {
            try await source.setArtistLean(album.artist, kind, genres: genres)
            onNotice(kind == .more ? "More like \(album.artist) next time." : "Fewer picks like \(album.artist). Nothing is hidden.")
        } catch { onNotice("Could not save that: " + StationsModel.message(error)) }
    }

    public func blockGenre(of album: AlbumItem) async {
        guard let genre = Self.blockableGenre(of: album) else { return }
        guard let source else { onNotice("Not connected to the Librarian. Check Settings."); return }
        do {
            try await source.blockGenre(genre)
            onNotice("Blocked \(genre). Your library is not affected. Undo it in Settings › Blocklist.")
            onBlocked()
        } catch { onNotice("Could not block \(genre): " + StationsModel.message(error)) }
    }

    /// Previews and render tests.
    public func showForPreview(_ list: Blocklist, note: String? = nil) { self.list = list; self.note = note; phase = .loaded }
}
