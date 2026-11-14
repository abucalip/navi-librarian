import DiscairCore
import DiscairLibrarian
import Foundation
import Observation

/// What the Radio settings tab asks of the Librarian. `LibrarianClient` is the real one; tests pass a fake.
public protocol RadioSettingsSource: Sendable {
    func radioScrobbling() async throws -> RadioScrobbling
    func setRadioScrobbling(_ on: Bool) async throws -> RadioScrobbling
    func radioSettings() async throws -> RadioSettings
    func uploadRadioLogo(station: String, data: Data, contentType: String) async throws
    func resetRadioLogo(station: String) async throws
}
extension LibrarianClient: RadioSettingsSource {}

/// Settings › Radio (docs/RADIO_PLAYBACK_PROPOSAL.md S2-4 item 3): the server's scrobbling switch, the app address (read only)
/// and a logo Change and Reset for each station. Everything is read when the tab opens; nothing polls.
@MainActor
@Observable
public final class RadioSettingsModel {
    public enum Phase: Equatable { case idle, loading, loaded, failed(String) }

    public private(set) var phase: Phase = .idle
    public private(set) var scrobbling: RadioScrobbling?
    /// Blank when the server has none saved; nil before the first read.
    public private(set) var appURL: String?
    /// A switch change is on its way to the server.
    public private(set) var scrobblingBusy = false
    /// Station ids whose logo is being changed or reset.
    public private(set) var busyLogos: Set<String> = []
    /// The server's sentence (or the app's short text) after a refused change; cleared by the next good one.
    public private(set) var note: String?
    /// Called with a station id after its logo changed, so the picture is read again.
    @ObservationIgnored public var onLogoChanged: (String) -> Void = { _ in }

    @ObservationIgnored private var source: (any RadioSettingsSource)?

    public init() {}

    public func configure(source: (any RadioSettingsSource)?) {
        self.source = source
        if source == nil { phase = .idle; scrobbling = nil; appURL = nil; note = nil; busyLogos = [] }
    }

    // MARK: What the tab says

    /// The switch can be turned: Last.fm is set up on the server and no change is under way.
    public var canSwitchScrobbling: Bool { scrobbling?.configured == true && !scrobblingBusy }
    public var scrobblingOn: Bool { scrobbling?.enabled ?? false }
    /// The line under the switch.
    public var scrobblingDetail: String {
        switch scrobbling {
        case nil: "Reading the server's setting…"
        case .some(let s) where !s.configured: "Last.fm is not set up on the server"
        case .some: "Songs heard for 30 seconds on a relayed station are sent to Last.fm by the server. Off sends nothing."
        }
    }
    /// "Not set" when the server has no address, so the row never shows an empty value.
    public var appAddressText: String {
        guard let appURL else { return "…" }
        return appURL.isEmpty ? "Not set" : appURL
    }

    // MARK: Loading

    public func load() async {
        guard let source else { return }
        if phase != .loaded { phase = .loading }
        do {
            async let s = source.radioScrobbling()
            async let a = source.radioSettings()
            let (scrobbling, settings) = try await (s, a)
            self.scrobbling = scrobbling
            appURL = settings.appURL
            phase = .loaded
        } catch {
            phase = .failed(StationsModel.message(error))
        }
    }

    // MARK: Scrobbling

    /// Shows the switch at once, sends it, and keeps the server's answer. A refusal puts the old value back with the sentence.
    public func setScrobbling(_ on: Bool) async {
        guard let source, let old = scrobbling, old.configured, old.enabled != on, !scrobblingBusy else { return }
        scrobblingBusy = true; defer { scrobblingBusy = false }
        scrobbling = RadioScrobbling(enabled: on, configured: old.configured)
        do {
            scrobbling = try await source.setRadioScrobbling(on)
            note = nil
        } catch {
            scrobbling = old
            note = StationsModel.message(error)
        }
    }

    // MARK: Logos

    /// The sentence for an image that cannot be sent, or nil when it can. The server checks the bytes; this only avoids sending
    /// a file it would refuse for its size.
    static func problem(withImageOfSize bytes: Int) -> String? {
        if bytes <= 0 { return "The image is empty." }
        if bytes > radioLogoUploadLimit { return "The image is too large. Choose one up to 2 MB." }
        return nil
    }

    /// Sends the owner's image for a station. The size is checked first; a refusal is the note and the logo is left as it was.
    public func changeLogo(station: String, image: Data, contentType: String = "application/octet-stream") async {
        if let problem = Self.problem(withImageOfSize: image.count) { note = problem; return }
        await changeLogo(station) { try await $0.uploadRadioLogo(station: station, data: image, contentType: contentType) }
    }

    /// Clears the owner's image; the server finds the logo from its sources again.
    public func resetLogo(station: String) async {
        await changeLogo(station) { try await $0.resetRadioLogo(station: station) }
    }

    private func changeLogo(_ station: String, _ send: (any RadioSettingsSource) async throws -> Void) async {
        guard let source, !busyLogos.contains(station) else { return }
        busyLogos.insert(station); defer { busyLogos.remove(station) }
        do {
            try await send(source)
            note = nil
            onLogoChanged(station)
        } catch {
            note = StationsModel.message(error)
        }
    }

    public func showNote(_ text: String?) { note = text }

    /// Previews and render tests.
    public func showForPreview(scrobbling: RadioScrobbling?, appURL: String?, note: String? = nil) {
        self.scrobbling = scrobbling; self.appURL = appURL; self.note = note; phase = .loaded
    }
}
