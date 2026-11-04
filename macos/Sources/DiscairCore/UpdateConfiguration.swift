import Foundation

/// Whether the running copy of the app can check for updates (contract section 10). Pure: reads the app's Info.plist
/// values. Sparkle is only started when this says `ready`; a bare `swift run` build, a build without the update key and a
/// plain-http feed all land in `unavailable`, and the app works the same without updates.
public enum UpdateConfiguration: Equatable, Sendable {
    case ready(feedURL: URL)
    case unavailable(Reason)

    public enum Reason: String, Equatable, Sendable {
        /// Not running from a `.app` (for example `swift run`).
        case notBundled
        case noFeed
        /// The feed address is not https, or has a login in it.
        case insecureFeed
        /// The EdDSA public key is missing or is not a 32-byte base64 key. Updates are never accepted without it.
        case noPublicKey
    }

    public static let feedKey = "SUFeedURL"
    public static let publicKeyKey = "SUPublicEDKey"

    public init(info: [String: Any]?, isBundledApp: Bool) {
        guard isBundledApp, let info else { self = .unavailable(.notBundled); return }
        guard let feed = info[Self.feedKey] as? String, let url = URL(string: feed) else { self = .unavailable(.noFeed); return }
        guard url.scheme == "https", url.host?.isEmpty == false, url.user == nil, url.password == nil else {
            self = .unavailable(.insecureFeed); return
        }
        guard let key = info[Self.publicKeyKey] as? String, Data(base64Encoded: key)?.count == 32 else {
            self = .unavailable(.noPublicKey); return
        }
        self = .ready(feedURL: url)
    }

    /// The running app's own configuration.
    public static var current: UpdateConfiguration {
        UpdateConfiguration(info: Bundle.main.infoDictionary, isBundledApp: Bundle.main.bundleURL.pathExtension == "app")
    }

    public var isReady: Bool { if case .ready = self { true } else { false } }

    /// One line for the menu item's explanation and for Settings.
    public var summary: String {
        switch self {
        case .ready: "Updates are checked daily and installed only if they carry the Discair update signature."
        case .unavailable(.notBundled): "Updates need the packaged Discair app; this is a development build."
        case .unavailable(.noFeed): "This build has no update feed address."
        case .unavailable(.insecureFeed): "The update feed address must be https."
        case .unavailable(.noPublicKey): "This build has no update signing key, so it will not accept updates."
        }
    }
}
