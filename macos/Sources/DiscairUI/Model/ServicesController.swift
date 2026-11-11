import DiscairCore
import DiscairLibrarian
import Foundation
import Observation

/// The tabs of the Cupertino Settings page (`docs/redesign.md` section 5.3 and 6.2).
public enum SettingsTab: String, CaseIterable, Sendable {
    case services = "Services", playback = "Playback", musicFolder = "Music folder", profiles = "Profiles"
}

/// One labelled field of the edit sheet.
public struct ServiceEditField: Equatable, Identifiable, Sendable {
    public enum Key: String, Sendable { case address, username, secret, downloadsPath, libraryPath }
    public var id: Key { key }
    public let key: Key
    public let label: String
    public let secure: Bool
    public let help: String?
}

/// What the edit sheet shows for each service (section 6.2, item 5): fields with their labels, never placeholders as labels.
public enum ServiceEditSpec {
    public static func summary(_ id: ServicesModel.ServiceID) -> String {
        switch id {
        case .navidrome: "Your library and playback, as the Librarian reaches it."
        case .slskd: "Finds and downloads the albums and songs you Get."
        case .lastfm: "Listening history the server reads for picks."
        case .listenbrainz: "Listening history the server reads for taste."
        case .discogs: "Edition details. Optional."
        default: ""
        }
    }

    /// Services the sheet can edit through the Librarian's settings routes. The Librarian address and the music folder live in
    /// Profiles and Music folder, so their Edit button goes there instead.
    public static func fields(_ id: ServicesModel.ServiceID) -> [ServiceEditField] {
        switch id {
        case .navidrome:
            [.init(key: .address, label: "Address", secure: false, help: nil),
             .init(key: .username, label: "Username", secure: false, help: nil),
             .init(key: .secret, label: "Password", secure: true, help: "Saved on the server. Leave empty to keep the saved password.")]
        case .slskd:
            [.init(key: .address, label: "Address", secure: false, help: nil),
             .init(key: .secret, label: "API key", secure: true, help: "Saved on the server. Leave empty to keep the saved key."),
             .init(key: .downloadsPath, label: "Folder slskd downloads into", secure: false, help: nil),
             .init(key: .libraryPath, label: "Music library folder", secure: false, help: "As the server sees it, not as this Mac does.")]
        case .lastfm:
            [.init(key: .username, label: "Username", secure: false, help: nil),
             .init(key: .secret, label: "API key", secure: true, help: "Saved on the server. Leave empty to keep the saved key.")]
        case .listenbrainz:
            [.init(key: .username, label: "Username", secure: false, help: nil),
             .init(key: .secret, label: "Token", secure: true, help: "Only for a private profile. Leave empty to keep the saved token.")]
        case .discogs:
            [.init(key: .secret, label: "Token", secure: true, help: "Paste a new token to replace the saved one.")]
        default: []
        }
    }

    public static func canEdit(_ id: ServicesModel.ServiceID) -> Bool { !fields(id).isEmpty }

    /// Where Edit goes for a service the sheet does not edit.
    public static func settingsTab(for id: ServicesModel.ServiceID) -> SettingsTab? {
        switch id {
        case .librarian: .profiles
        case .smb: .musicFolder
        default: nil
        }
    }

    /// The routes clear a saved secret for these two only (Discogs with an empty token; ListenBrainz with an empty username).
    public static func canDisconnect(_ id: ServicesModel.ServiceID) -> Bool { id == .discogs || id == .listenbrainz }

    /// The destructive label names what is cut off (section 4.3).
    public static func disconnectLabel(_ id: ServicesModel.ServiceID, name: String) -> String { "Disconnect \(name)" }

    /// The sentence under the alert's title: what stops working, and that nothing stored is deleted.
    public static func disconnectDetail(_ id: ServicesModel.ServiceID, powers: [String]) -> String {
        "\(powers.joined(separator: ", ")) stop updating. Nothing already stored on the server is deleted."
    }
}

/// The values typed into the edit sheet.
public struct ServiceDraft: Equatable, Sendable {
    public var address = "", username = "", secret = "", downloadsPath = "", libraryPath = ""
    public subscript(key: ServiceEditField.Key) -> String {
        get {
            switch key {
            case .address: address
            case .username: username
            case .secret: secret
            case .downloadsPath: downloadsPath
            case .libraryPath: libraryPath
            }
        }
        set {
            switch key {
            case .address: address = newValue
            case .username: username = newValue
            case .secret: secret = newValue
            case .downloadsPath: downloadsPath = newValue
            case .libraryPath: libraryPath = newValue
            }
        }
    }
}

/// What the Services screen holds: the model it draws, whether a check is running, which rows are open and the edit sheet's state.
/// The checks themselves run in `AppState.refreshServices()`; this only keeps what they found (and the local history, decision D7).
@MainActor
@Observable
public final class ServicesController {
    public struct EditNotice: Equatable, Sendable {
        public enum Kind: Sendable { case success, danger }
        public let kind: Kind
        public let lead: String
        public let message: String
    }

    public private(set) var model: ServicesModel
    public private(set) var inputs: ServicesModel.Inputs
    public private(set) var checking = false
    /// True once a check has finished, so the screen can tell "Checking…" from a result.
    public private(set) var hasChecked = false
    public var expanded: Set<ServicesModel.ServiceID> = []
    /// Set by "Fix <service>" in the toolbar popover: the Services tab opens this row's edit sheet.
    public var editing: ServicesModel.ServiceID?
    public var draft = ServiceDraft()
    public var editNotice: EditNotice?
    public private(set) var working = false
    public var confirmingDisconnect: ServicesModel.ServiceID?
    /// A sentence from a failed Save or Disconnect, shown in the sheet or under the list.
    public var actionError: String?

    @ObservationIgnored private let defaults: UserDefaults
    private static let historyKey = "discair.services.history"

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        let history = defaults.data(forKey: Self.historyKey).flatMap { try? JSONDecoder().decode(ServicesModel.History.self, from: $0) } ?? ServicesModel.History()
        var start = ServicesModel.Inputs()
        start.history = history
        inputs = start
        model = ServicesModel.build(start)
    }

    public func beginChecking() { checking = true }

    /// Builds the model from a finished check and keeps the history it produced.
    public func finish(_ next: ServicesModel.Inputs) {
        var next = next
        next.history = inputs.history
        let built = ServicesModel.build(next)
        inputs = next
        inputs.history = built.history
        model = built
        checking = false
        hasChecked = true
        if let data = try? JSONEncoder().encode(built.history) { defaults.set(data, forKey: Self.historyKey) }
        // First result: open the row that needs the owner, else the Librarian (the mockups' open rows).
        if expanded.isEmpty { expanded = [built.attention.first?.id ?? .librarian] }
    }

    /// Records one service's fresh test answer without a full re-check.
    public func record(test result: ServiceTestResult, for id: ServicesModel.ServiceID, now: Date = Date()) {
        var next = inputs
        next.tests[id] = result
        next.now = now
        finish(next)
    }

    /// Shows a finished model without a server: screenshots and tests.
    func preview(_ built: ServicesModel, expanded open: Set<ServicesModel.ServiceID> = []) {
        model = built; inputs.history = built.history; hasChecked = true; checking = false; expanded = open
    }

    public func toggle(_ id: ServicesModel.ServiceID) {
        if expanded.contains(id) { expanded.remove(id) } else { expanded.insert(id) }
    }

    /// Opens the edit sheet with the values the server already holds. Secrets are never held, so those fields start empty.
    public func startEditing(_ id: ServicesModel.ServiceID) {
        var d = ServiceDraft()
        switch id {
        case .navidrome: d.address = inputs.navidromeSettings?.url ?? ""; d.username = inputs.navidromeSettings?.username ?? ""
        case .slskd: d.address = inputs.slskdSettings?.url ?? ""; d.downloadsPath = inputs.slskdSettings?.downloadsPath ?? ""; d.libraryPath = inputs.slskdSettings?.musicLibraryPath ?? ""
        case .lastfm: d.username = inputs.lastFMSettings?.username ?? ""
        case .listenbrainz: d.username = inputs.listenBrainzSettings?.username ?? ""
        default: break
        }
        draft = d; editNotice = nil; actionError = nil; editing = id
    }

    public func stopEditing() { editing = nil; editNotice = nil; draft = ServiceDraft() }

    func setWorking(_ on: Bool) { working = on }

    /// Words for a test answer in the sheet: "Test passed. slskd answered and the key was accepted."
    public static func notice(for result: ServiceTestResult, name: String, noun: String) -> EditNotice {
        if result.ok {
            return EditNotice(kind: .success, lead: "Test passed.", message: "\(name) answered and the \(noun.lowercased()) was accepted.")
        }
        switch result.status {
        case "authentication_failed": return EditNotice(kind: .danger, lead: "Test failed.", message: "\(name) did not accept the \(noun.lowercased()).")
        case "not_configured": return EditNotice(kind: .danger, lead: "Test failed.", message: "\(name) is not set up yet. Save the details first.")
        case "not_found": return EditNotice(kind: .danger, lead: "Test failed.", message: "\(name) does not know that username.")
        default: return EditNotice(kind: .danger, lead: "Test failed.", message: result.message.isEmpty ? "\(name) did not answer. Check that it is running and that the address is right." : result.message)
        }
    }
}
