import Foundation
import NetFS

/// The music folder over SMB (contract sections 7 and 10). Optional: quick tag reads only, never playback (waveforms come from the Librarian).

// MARK: Address

public enum ShareAddressError: Error, Equatable, Sendable {
    case notAnSMBAddress
    case missingShare
    case embeddedCredentials
}

public enum ShareAddress {
    /// `smb://host/share`. The login goes in the Keychain, never in the address; no query, no fragment, one share name.
    public static func validate(_ text: String) throws -> URL {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: trimmed), url.scheme?.lowercased() == "smb", let host = url.host, !host.isEmpty else {
            throw ShareAddressError.notAnSMBAddress
        }
        guard url.user == nil, url.password == nil else { throw ShareAddressError.embeddedCredentials }
        let parts = url.path.split(separator: "/", omittingEmptySubsequences: true)
        guard parts.count == 1, url.query == nil, url.fragment == nil else { throw ShareAddressError.missingShare }
        return url
    }
}

// MARK: Settings

/// What the owner can edit. Holds no secret (the SMB login is in the Keychain).
public struct ShareSettings: Codable, Equatable, Sendable {
    public var enabled: Bool
    /// `smb://192.168.1.87/media` style; empty until the owner types it.
    public var address: String
    /// The music folder as Navidrome reports it (inside its container).
    public var serverRoot: String
    /// Where the same folder appears on this Mac once mounted.
    public var localRoot: String

    public init(enabled: Bool = false, address: String = "", serverRoot: String = "/music",
                localRoot: String = "/Volumes/media/library/music") {
        self.enabled = enabled; self.address = address; self.serverRoot = serverRoot; self.localRoot = localRoot
    }
}

// MARK: Path mapping

public enum SongPathMapping: Equatable, Sendable {
    case local(URL)
    /// The path does not start with the server root: Navidrome is probably not reporting real paths. Never guessed.
    case outsideServerRoot
    /// `..`, an empty name or a relative path: refused.
    case unsafe
}

/// Swaps the server's music root for the Mac's mount of the same folder.
public struct SongPathMapper: Equatable, Sendable {
    public let serverRoot: String
    public let localRoot: String

    /// Roots must be absolute and free of `..`; a trailing slash is ignored. `nil` if either is not usable.
    public init?(serverRoot: String, localRoot: String) {
        guard let s = Self.normalised(serverRoot), let l = Self.normalised(localRoot) else { return nil }
        self.serverRoot = s; self.localRoot = l
    }

    private static func normalised(_ root: String) -> String? {
        let t = root.trimmingCharacters(in: .whitespacesAndNewlines)
        guard t.hasPrefix("/") else { return nil }
        let parts = t.split(separator: "/", omittingEmptySubsequences: true).map(String.init)
        guard !parts.isEmpty, !parts.contains("..") , !parts.contains(".") else { return nil }
        return "/" + parts.joined(separator: "/")
    }

    public func map(_ serverPath: String) -> SongPathMapping {
        guard serverPath.hasPrefix(serverRoot + "/") else {
            return serverPath.hasPrefix("/") ? .outsideServerRoot : .unsafe
        }
        let rest = serverPath.dropFirst(serverRoot.count + 1)
        let parts = rest.split(separator: "/", omittingEmptySubsequences: false)
        guard !parts.isEmpty, !parts.contains(where: { $0.isEmpty || $0 == ".." || $0 == "." }),
              !rest.contains("\0") else { return .unsafe }
        return .local(URL(fileURLWithPath: localRoot).appending(path: String(rest)))
    }

    /// True when at least one of these paths sits under the server root. Used to detect "Report Real Path" being off.
    public func looksRight(_ serverPaths: [String]) -> Bool {
        serverPaths.contains { $0.hasPrefix(serverRoot + "/") }
    }
}

// MARK: Mounting

public enum ShareMountFailure: Error, Equatable, Sendable {
    case loginRefused
    case shareNotFound
    case unreachable
    case timedOut
    case other(Int32)

    /// One short sentence for Settings. No address, no login.
    public var summary: String {
        switch self {
        case .loginRefused: "The Mac was refused: check the share's username and password."
        case .shareNotFound: "The share name was not found on that server."
        case .unreachable: "The file server could not be reached."
        case .timedOut: "The file server took too long to answer."
        case .other(let code): "The share could not be mounted (error \(code))."
        }
    }

    /// Maps a POSIX / NetFS status. `ENOENT` 2, `ETIMEDOUT` 60, `ECONNREFUSED` 61, `EHOSTDOWN` 64,
    /// `EHOSTUNREACH` 65, `ENETUNREACH` 51, `EAUTH` 80, `EACCES` 13, `EPERM` 1, `ENOTCONN` 57.
    public static func from(status: Int32) -> ShareMountFailure {
        switch status {
        case 80, 13, 1, 45: .loginRefused
        case 2, 22, 6: .shareNotFound
        case 60: .timedOut
        case 51, 61, 64, 65, 57, 50, 6000: .unreachable
        default: .other(status)
        }
    }
}

public enum ShareMountOutcome: Equatable, Sendable {
    case mounted
    case failed(ShareMountFailure)
}

public protocol ShareMounter: Sendable {
    /// Mounts the share like Finder's Connect to Server. Never shows a password dialog. Blocking calls run off the caller.
    func mount(_ address: URL, credential: Credential?) async -> ShareMountOutcome
}

/// Apple's NetFS: `NetFSMountURLSync`. The mount point is chosen by the system (`/Volumes/<share>`).
public struct NetFSMounter: ShareMounter {
    public init() {}

    public func mount(_ address: URL, credential: Credential?) async -> ShareMountOutcome {
        await Task.detached(priority: .utility) { () -> ShareMountOutcome in
            let open = NSMutableDictionary()
            open[kNAUIOptionKey as String] = kNAUIOptionNoUI as String   // fail instead of asking for a password
            var points: Unmanaged<CFArray>?
            let status: Int32 = (credential ?? Credential(username: "", password: "")).withPassword { password in
                NetFSMountURLSync(address as CFURL, nil, credential.map { $0.username as CFString },
                                  credential != nil ? password as CFString : nil,
                                  open as CFMutableDictionary, nil, &points)
            }
            points?.release()
            // 17 (EEXIST): already mounted, which is what we wanted.
            return status == 0 || status == 17 ? .mounted : .failed(.from(status: status))
        }.value
    }
}
