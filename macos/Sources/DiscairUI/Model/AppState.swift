import Observation
import SwiftUI

/// The six screens every theme must provide (contract section 9, M3 mockups).
public enum Screen: String, CaseIterable, Sendable {
    case home, album, nowPlaying, queue, library, artist
    /// Profiles, logins and the connection (M5; no mockup exists, each theme draws it in its own language).
    case settings
    /// The Albums grid on its own (the queue screen shows the same grid under the Up Next inspector).
    case albums
}

/// What a theme may ask the app to do. Themes call these; they never reach the network or the audio engine.
/// Get, Save and Not for me always exist as actions so every theme can show them with text labels.
@MainActor
public protocol DiscairActions: AnyObject {
    func play(album: AlbumItem)
    func get(album: AlbumItem)
    func save(album: AlbumItem)
    func notForMe(album: AlbumItem)
    func resume()
}

/// Do-nothing actions used by previews, screenshot tests and until the real engine lands (M5).
@MainActor
public final class NoopActions: DiscairActions {
    public init() {}
    public func play(album: AlbumItem) {}
    public func get(album: AlbumItem) {}
    public func save(album: AlbumItem) {}
    public func notForMe(album: AlbumItem) {}
    public func resume() {}
}

/// Everything a theme reads. Themes own layout; this owns state.
@MainActor
@Observable
public final class AppState {
    public var themeID: ThemeID
    public var screen: Screen
    public var selectedAlbum: AlbumItem = Fixtures.albums[0]
    /// The live connection and logins. `nil` in previews and screenshot tests, which show the sample label.
    public let session: SessionModel?
    public var connectionLabel: String { session?.label ?? "Home network · http (local)" }
    public var connectionIsGood: Bool { session?.isGood ?? true }
    public let actions: DiscairActions

    public init(themeID: ThemeID = .cupertino, screen: Screen = .home, actions: DiscairActions = NoopActions(), session: SessionModel? = nil) {
        self.session = session
        self.themeID = themeID
        self.screen = screen
        self.actions = actions
    }
}
