import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Foundation
import Observation

/// Profiles, logins and the live connection (contract sections 3 and 10, M5). Themes read this and call it from
/// their Settings screen; they never touch the network or the Keychain directly.
/// Passwords are written to the Keychain and never read back into the UI, logged or shown.
@MainActor
@Observable
public final class SessionModel {
    public enum Status: Equatable {
        case notConfigured
        case connecting
        case connected(profile: Profile, manualOverride: Bool)
        case failed(DiscairError)
    }

    public private(set) var profiles: ProfileList
    public private(set) var status: Status = .notConfigured
    public private(set) var hasNavidromeLogin = false
    public private(set) var hasLibrarianLogin = false
    public private(set) var navidromeUsername: String?
    public private(set) var librarianUsername: String?
    /// The ListenBrainz account saved in the Keychain (sent to the server at startup); nil when none.
    public private(set) var listenBrainzUsername: String?
    /// The Navidrome and Librarian clients of the active profile, set on a successful connect (used by the data layer).
    public private(set) var navidrome: NavidromeClient?
    public private(set) var librarian: LibrarianClient?
    /// Set when the Librarian login was refused or missing while Navidrome worked; the app is usable without it.
    public private(set) var librarianNote: String?

    /// Called after a successful connect (the app uses it to load the library). Not called on failure.
    public var onConnected: (@MainActor () async -> Void)?

    private let store: ProfileStore
    /// Shared with the SMB model so the app reads the Keychain through one object.
    public let secrets: any SecretStore
    private let resolver: ProfileResolver
    private let transport: (@Sendable () -> any HTTPTransport)?

    public init(store: ProfileStore, secrets: any SecretStore = KeychainSecretStore.shared,
                resolver: ProfileResolver = ProfileResolver(),
                navidromeTransport: (@Sendable () -> any HTTPTransport)? = nil) {
        self.store = store
        self.secrets = secrets
        self.resolver = resolver
        self.transport = navidromeTransport
        self.profiles = (try? store.load()) ?? ProfileList()
        refreshLogins()
    }

    /// `~/Library/Application Support/Discair/profiles.json`.
    public static var defaultStoreURL: URL {
        URL.applicationSupportDirectory.appending(path: "Discair/profiles.json")
    }

    // MARK: Profiles

    public var activeProfile: Profile? {
        if case .connected(let p, _) = status { return p }
        return nil
    }

    public func addProfile(name: String, librarianURL: String, navidromeURL: String) throws {
        let profile = try Profile(name: name, librarianURL: librarianURL, navidromeURL: navidromeURL)
        var list = profiles
        try list.add(profile)
        try store.save(list)
        profiles = list
    }

    public func removeProfile(id: UUID) throws {
        var list = profiles
        list.remove(id: id)
        try store.save(list)
        profiles = list
        if case .connected(let p, _) = status, p.id == id { status = .notConfigured; navidrome = nil; librarian = nil }
    }

    /// `nil` goes back to automatic selection (LAN first, then Tailscale).
    public func setOverride(_ id: UUID?) throws {
        var list = profiles
        list.overrideID = id
        try store.save(list)
        profiles = list
    }

    // MARK: Logins

    public func saveLogin(_ kind: SecretKind, username: String, password: String) throws {
        let user = username.trimmingCharacters(in: .whitespacesAndNewlines)
        // A ListenBrainz login is a username with an optional token; the others need a password.
        guard !user.isEmpty, !password.isEmpty || kind == .listenbrainz else { throw SettingsError.emptyLogin }
        try secrets.save(Credential(username: user, password: password), for: kind)
        refreshLogins()
    }

    /// Told when the Navidrome login is removed (sign-out): the lyrics cache must go with it.
    public var onNavidromeSignOut: (() -> Void)?

    public func removeLogin(_ kind: SecretKind) throws {
        try secrets.delete(kind)
        refreshLogins()
        if kind == .navidrome { onNavidromeSignOut?() }
    }

    private func refreshLogins() {
        let nav = (try? secrets.credential(for: .navidrome)) ?? nil
        let lib = (try? secrets.credential(for: .librarian)) ?? nil
        hasNavidromeLogin = nav != nil; navidromeUsername = nav?.username
        hasLibrarianLogin = lib != nil; librarianUsername = lib?.username
        let lb = (try? secrets.credential(for: .listenbrainz)) ?? nil
        listenBrainzUsername = lb?.username
    }

    // MARK: Connection

    /// Picks the profile (override, else LAN then Tailscale), checks the Navidrome login with `ping` and the Librarian
    /// login if one is saved. Errors keep their kind so the screen can name them and offer Retry.
    public func connect() async {
        await attemptConnect()
        if case .failed(let e) = status { await onConnectFailed?(e) }
    }

    /// Told when a connect attempt ends in failure (the app then shows the saved library, if there is one).
    public var onConnectFailed: (@MainActor (DiscairError) async -> Void)?

    private func attemptConnect() async {
        guard !profiles.profiles.isEmpty else { status = .notConfigured; return }
        status = .connecting
        navidrome = nil; librarian = nil; librarianNote = nil
        do {
            let selection = try await resolver.select(from: profiles)
            guard let nav = try secrets.credential(for: .navidrome) else {
                status = .failed(.unauthorised(message: "No Navidrome login is saved.")); return
            }
            let hint: @Sendable () -> Bool = { !TailscaleDetector.isConnected(NetworkInterfaces.current()) }
            let client: NavidromeClient
            if let transport {
                client = try NavidromeClient(baseURL: selection.profile.navidromeURL, credential: nav, transport: transport(), tailscaleHint: hint)
            } else {
                client = try NavidromeClient(baseURL: selection.profile.navidromeURL, credential: nav, tailscaleHint: hint)
            }
            try await client.ping()
            navidrome = client
            if let lib = try secrets.credential(for: .librarian) {
                let l = try LibrarianClient(baseURL: selection.profile.librarianURL, credential: lib, tailscaleHint: hint)
                do { try await l.login(); librarian = l; await syncListenBrainz(l) }
                catch let e as DiscairError { librarianNote = "Librarian: \(e.summary)" }
            } else {
                librarianNote = "No Librarian login is saved, so recommendations and Get are off."
            }
            status = .connected(profile: selection.profile, manualOverride: selection.isManualOverride)
            await onConnected?()
        } catch let e as DiscairError {
            status = .failed(e)
        } catch ProfileError.notFound {
            status = .failed(.serverUnreachable)
        } catch {
            status = .failed(ErrorMapping.map(error))
        }
    }

    /// The saved ListenBrainz login is pushed to the server at startup when the server holds a different username, or has no
    /// token while one is saved here. Failures are not fatal: the Settings card shows what the server holds.
    func syncListenBrainz(_ l: LibrarianClient) async {
        guard let lb = (try? secrets.credential(for: .listenbrainz)) ?? nil, let server = try? await l.listenBrainzSettings() else { return }
        let token = lb.withPassword { $0 }
        guard server.username != lb.username || (!token.isEmpty && !server.tokenConfigured) else { return }
        do { try await l.saveListenBrainz(username: lb.username, token: token) }
        catch { librarianNote = "ListenBrainz: could not send the saved account to the server." }
    }

    // MARK: Presentation

    /// Short text for the connection indicator.
    public var label: String {
        switch status {
        case .notConfigured: "No profile set up"
        case .connecting: "Connecting…"
        case .connected(let p, _):
            "\(p.name) · \(p.isUnencrypted ? "http (unencrypted)" : "https")"
        case .failed(let e): "Not connected · \(e.summary)"
        }
    }

    public var isGood: Bool { if case .connected = status { true } else { false } }
    public var isUnencrypted: Bool { activeProfile?.isUnencrypted ?? false }

    /// Names the error kind and what to do (contract section 3). Never includes a credential or URL query.
    public var statusDetail: String {
        switch status {
        case .notConfigured: "Add a profile and the two logins, then connect."
        case .connecting: "Looking for your server."
        case .connected: librarianNote ?? "Connected to Navidrome and the Librarian."
        case .failed(let e):
            switch e {
            case .tailscaleNotConnected: "Tailscale is not connected. Turn it on, then retry."
            case .noNetwork: "No network connection. Check Wi-Fi, then retry."
            case .serverUnreachable: "The server did not answer. Check the address and that it is running, then retry."
            case .unauthorised: "The server refused the login. Check the username and password."
            case .tooManyAttempts: "Too many login attempts. Wait a few minutes before retrying."
            case .server(let s, _): "The server reported an error (\(s)). Retry, or check its logs."
            case .insecureOrInvalidAddress: "That address is not allowed. Use https, or a home-network address over http."
            }
        }
    }

    public var canRetry: Bool {
        if case .failed(let e) = status { return e.isRetryable }
        return false
    }
}

public extension ProfileNetwork {
    var displayName: String { self == .lan ? "LAN" : rawValue.capitalized }
}

public enum SettingsError: Error, Equatable, Sendable {
    case emptyLogin
}

public extension Error {
    /// A sentence for the Settings screen. Profile and address errors are explained, anything else is generic.
    var settingsMessage: String {
        if let e = self as? ProfileError {
            switch e {
            case .emptyName: return "Give the profile a name."
            case .duplicateName: return "A profile with that name already exists."
            case .notFound: return "That profile no longer exists."
            }
        }
        if self is SettingsError { return "Enter a username and a password." }
        if let e = self as? DiscairError { return e.summary }
        if self is SecretStoreError { return "The Keychain refused the change." }
        return "Could not save the change."
    }
}
