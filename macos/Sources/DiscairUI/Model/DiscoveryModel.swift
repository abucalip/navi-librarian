import DiscairCore
import DiscairLibrarian
import Foundation
import Observation

/// The Discover lists. The Librarian ranks; this only fetches and shows them in the order received.
@MainActor
@Observable
public final class DiscoveryModel {
    public enum Kind: String, CaseIterable, Sendable, Identifiable {
        case personal, classics, newReleases = "new_releases", saved = "for_me"
        public var id: String { rawValue }
        public var title: String {
            switch self { case .personal: "For you"; case .classics: "Classics"; case .newReleases: "New releases"; case .saved: "Saved" }
        }
        var emptyText: String {
            switch self {
            case .saved: "Nothing saved yet. Save an album from any list and it appears here."
            default: "No saved list yet."
            }
        }
    }

    public enum Phase: Equatable, Sendable { case idle, loading, loaded, failed(String) }

    public struct Page: Equatable {
        public var phase: Phase = .idle
        public var albums: [AlbumItem] = []
        /// The server's words for an empty list.
        public var message: String?
        public var building = false
    }

    public private(set) var pages: [Kind: Page] = [:]
    public var selected: Kind = .personal
    /// The row under the pointer (Discover's covers peek opens while it is hovered).
    public var hoveredAlbum: Int?
    private var librarian: LibrarianClient?

    public init() {}

    public func configure(librarian: LibrarianClient?) {
        self.librarian = librarian
        pages = [:]
    }

    public func page(_ k: Kind) -> Page { pages[k] ?? Page() }

    /// Screenshot tests and previews show sample lists without a server.
    func show(_ k: Kind, _ albums: [AlbumItem], message: String? = nil) {
        pages[k] = Page(phase: .loaded, albums: albums, message: message)
    }

    /// Loads a list once; `force` re-reads it (Try again, after building).
    public func load(_ k: Kind, force: Bool = false) async {
        guard let librarian else { return }
        if !force, page(k).phase == .loaded || page(k).phase == .loading { return }
        var p = page(k); p.phase = .loading; pages[k] = p
        do {
            let list = try await librarian.discoveryList(k.rawValue)
            let albums = list.items.enumerated().map { entry -> AlbumItem in
                var album = LibraryModel.item(entry.element, index: 8000 + entry.offset)
                album.releaseGroupMBID = Self.peekReleaseGroup(k, entry.element)
                return album
            }
            pages[k] = Page(phase: .loaded, albums: albums, message: albums.isEmpty ? (list.message ?? k.emptyText) : nil)
        } catch let e as DiscairError {
            pages[k] = Page(phase: .failed(AcquisitionModel.text(e)))
        } catch {
            pages[k] = Page(phase: .failed(ErrorMapping.map(error).summary))
        }
    }

    /// The release group a row's covers are looked up by (idea 9): `mbid` on new releases, `release_group_mbid` elsewhere.
    /// Only a well-formed UUID is kept, so nothing else reaches the server.
    static func peekReleaseGroup(_ k: Kind, _ pick: DashboardPick) -> String? {
        let raw = pick.releaseGroupMBID ?? (k == .newReleases ? pick.mbid : nil)
        guard let raw, let id = UUID(uuidString: raw.trimmingCharacters(in: .whitespaces)) else { return nil }
        return id.uuidString.lowercased()
    }

    /// "Build this list": asks the Librarian to make it, then reads it. Not offered for Saved.
    public func build(_ k: Kind) async {
        guard let librarian, k != .saved else { return }
        var p = page(k); p.building = true; pages[k] = p
        do { try await librarian.refreshDiscoveryList(k.rawValue) }
        catch let e as DiscairError {
            pages[k] = Page(phase: .failed("Could not build this list: " + AcquisitionModel.text(e)))
            return
        } catch { pages[k] = Page(phase: .failed("Could not build this list.")); return }
        await load(k, force: true)
    }
}
