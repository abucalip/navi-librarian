import DiscairCore
import Foundation
import Observation

/// The optional SMB mount of the music folder (contract sections 7 and 10). It mounts at launch and when the profile
/// changes, and reports one status line for Settings. If anything fails, SMB features stay off and playback is unaffected.
@MainActor
@Observable
public final class ShareModel {
    public enum Status: Equatable {
        case off
        case needsAddress
        case mounting
        /// Mounted and the music folder is there.
        case ready
        case unavailable(String)
    }

    public private(set) var settings: ShareSettings
    public private(set) var status: Status = .off
    public private(set) var username: String?
    /// Set when Navidrome's paths do not start with the server root ("Report Real Path" is probably off).
    public private(set) var pathHint: String?
    /// Last message from a Save that was refused (bad address or root), for the Settings screen.
    public private(set) var settingsError: String?

    @ObservationIgnored private let defaults: UserDefaults
    @ObservationIgnored private let secrets: any SecretStore
    @ObservationIgnored private let mounter: any ShareMounter
    @ObservationIgnored private let folderExists: @Sendable (String) -> Bool
    @ObservationIgnored private var attempt: Task<Void, Never>?
    private static let key = "discair.libraryShare"

    public init(defaults: UserDefaults = .standard, secrets: any SecretStore = KeychainSecretStore(),
                mounter: any ShareMounter = NetFSMounter(),
                folderExists: @escaping @Sendable (String) -> Bool = {
                    var isDir: ObjCBool = false
                    return FileManager.default.fileExists(atPath: $0, isDirectory: &isDir) && isDir.boolValue
                }) {
        self.defaults = defaults; self.secrets = secrets; self.mounter = mounter; self.folderExists = folderExists
        settings = defaults.data(forKey: Self.key).flatMap { try? JSONDecoder().decode(ShareSettings.self, from: $0) } ?? ShareSettings()
        username = ((try? secrets.credential(for: .smb)) ?? nil)?.username
        status = settings.enabled ? .needsAddress : .off
    }

    public var isReady: Bool { status == .ready && pathHint == nil }

    /// Where a song's file is on this Mac, or nil when SMB is not usable or the path is not safe.
    public func localURL(forServerPath path: String) -> URL? {
        guard isReady, let mapper = SongPathMapper(serverRoot: settings.serverRoot, localRoot: settings.localRoot),
              case .local(let url) = mapper.map(path) else { return nil }
        return url
    }

    // MARK: Settings

    /// Saves the address and roots after checking them. Does not mount.
    public func save(address: String, serverRoot: String, localRoot: String) {
        do {
            if !address.trimmingCharacters(in: .whitespaces).isEmpty { _ = try ShareAddress.validate(address) }
            guard SongPathMapper(serverRoot: serverRoot, localRoot: localRoot) != nil else {
                settingsError = "The two folders must be full paths such as /music and /Volumes/media/library/music."
                return
            }
            var s = settings
            s.address = address.trimmingCharacters(in: .whitespacesAndNewlines)
            s.serverRoot = serverRoot.trimmingCharacters(in: .whitespacesAndNewlines)
            s.localRoot = localRoot.trimmingCharacters(in: .whitespacesAndNewlines)
            store(s); settingsError = nil
        } catch ShareAddressError.embeddedCredentials {
            settingsError = "Leave the username and password out of the address; they go in the boxes below."
        } catch {
            settingsError = "Use an address like smb://192.168.1.87/media (one share name, nothing after it)."
        }
    }

    public func saveLogin(username: String, password: String) throws {
        let user = username.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !user.isEmpty, !password.isEmpty else { throw SettingsError.emptyLogin }
        try secrets.save(Credential(username: user, password: password), for: .smb)
        self.username = user
    }

    public func removeLogin() throws {
        try secrets.delete(.smb)
        username = nil
    }

    /// The on/off switch. Turning it on mounts straight away; turning it off keeps whatever is mounted (the owner may use it).
    public func setEnabled(_ on: Bool) {
        var s = settings; s.enabled = on; store(s)
        if on { start() } else { attempt?.cancel(); status = .off; pathHint = nil }
    }

    /// Test hook: marks the share enabled without starting a mount.
    func setEnabledWithoutMounting() { var s = settings; s.enabled = true; store(s) }

    private func store(_ s: ShareSettings) {
        settings = s
        if let data = try? JSONEncoder().encode(s) { defaults.set(data, forKey: Self.key) }
    }

    // MARK: Mounting

    /// Launch and profile change: mount if enabled. A second call while one is running replaces it.
    public func start() {
        attempt?.cancel()
        guard settings.enabled else { status = .off; return }
        attempt = Task { await mountNow() }
    }

    /// Profile change: try again only when the share is not already up or being mounted.
    public func startIfNeeded() {
        if status == .ready || status == .mounting { return }
        start()
    }

    /// Mounts and waits. Failures become a status line, never an error to the caller.
    public func mountNow() async {
        guard settings.enabled else { status = .off; return }
        guard let url = try? ShareAddress.validate(settings.address) else { status = .needsAddress; return }
        // Already there (mounted by hand or earlier): nothing to do.
        if folderExists(settings.localRoot) { status = .ready; return }
        status = .mounting
        let credential = (try? secrets.credential(for: .smb)) ?? nil
        let outcome = await mounter.mount(url, credential: credential)
        guard !Task.isCancelled else { return }
        switch outcome {
        case .mounted:
            status = folderExists(settings.localRoot) ? .ready
                : .unavailable("The share mounted, but \(settings.localRoot) is not on it. Check the folder path below.")
        case .failed(let failure):
            status = .unavailable(failure.summary)
        }
    }

    /// Reads a page of Navidrome song paths. If none starts with the server root, SMB stays off with one line of advice.
    public func noteServerPaths(_ paths: [String]) {
        guard !paths.isEmpty, let mapper = SongPathMapper(serverRoot: settings.serverRoot, localRoot: settings.localRoot) else { return }
        pathHint = mapper.looksRight(paths) ? nil
            : "Navidrome's paths do not start with \(mapper.serverRoot). Turn on “Report Real Path” for this app's player in Navidrome, or fix the server folder."
    }

    /// One line for Settings.
    public var statusLine: String {
        if let pathHint, status == .ready { return pathHint }
        switch status {
        case .off: return "Off. Playback never needs the share."
        case .needsAddress: return "Enter the share address, then save."
        case .mounting: return "Connecting to the share…"
        case .ready: return "Connected. Waveforms and quick tag reads can use the music folder."
        case .unavailable(let why): return "Not connected. \(why) Playback is not affected."
        }
    }
}
