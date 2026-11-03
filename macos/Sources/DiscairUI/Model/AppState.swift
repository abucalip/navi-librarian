import Observation
import SwiftUI

/// The six screens every theme must provide (contract section 9, M3 mockups).
public enum Screen: String, CaseIterable, Sendable {
    case home, album, nowPlaying, queue, library, artist
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
    public var connectionLabel = "Home network · http (local)"
    public let actions: DiscairActions

    public init(themeID: ThemeID = .cupertino, screen: Screen = .home, actions: DiscairActions = NoopActions()) {
        self.themeID = themeID
        self.screen = screen
        self.actions = actions
    }
}
