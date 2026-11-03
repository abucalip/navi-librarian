import Foundation

/// The failure kinds the app tells apart (contract section 3). Every case has a retry action in the UI.
/// Values never carry credentials, tokens, salts or full URLs with query strings.
public enum DiscairError: Error, Equatable, Sendable {
    /// The Mac has no usable network interface, or the system reported "not connected".
    case noNetwork
    /// The address did not answer (timeout, refused, DNS failure, TLS failure).
    case serverUnreachable
    /// The address is a Tailscale one and no Tailscale interface is up on this Mac.
    case tailscaleNotConnected
    /// The server answered but refused the login (HTTP 401/403, Subsonic codes 40, 41, 44, 50).
    case unauthorised(message: String?)
    /// The server answered with an error, or with something that is not the expected API.
    case server(status: Int, message: String?)
    /// Librarian login rate limit (HTTP 429). Not retried automatically.
    case tooManyAttempts(message: String?)
    /// The address or profile breaks the transport rules (public http, bad scheme, credentials in the URL).
    case insecureOrInvalidAddress(reason: AddressRejection)
}

public enum AddressRejection: String, Equatable, Sendable {
    case notAURL
    case unsupportedScheme
    case missingHost
    case embeddedCredentials
    case publicHTTP
}

public extension DiscairError {
    /// Short owner-facing text. Contains no secrets.
    var summary: String {
        switch self {
        case .noNetwork: "No network connection."
        case .serverUnreachable: "The server did not answer."
        case .tailscaleNotConnected: "Tailscale is not connected."
        case .unauthorised: "The server refused the login."
        case .server(let status, _): "The server reported an error (\(status))."
        case .tooManyAttempts: "Too many login attempts. Try again later."
        case .insecureOrInvalidAddress(let reason): "This address is not allowed (\(reason.rawValue))."
        }
    }

    /// Whether a retry button makes sense. Everything but an invalid address can be retried.
    var isRetryable: Bool {
        if case .insecureOrInvalidAddress = self { return false }
        return true
    }
}

public enum ErrorMapping {
    /// Maps a transport error to a kind. `tailscaleHint` is true when the target is a Tailscale
    /// address and no Tailscale interface is up.
    public static func map(_ error: any Error, tailscaleHint: Bool = false) -> DiscairError {
        if let e = error as? DiscairError { return e }
        guard let url = error as? URLError else { return .serverUnreachable }
        switch url.code {
        case .notConnectedToInternet, .dataNotAllowed, .internationalRoamingOff:
            return .noNetwork
        case .timedOut, .cannotFindHost, .cannotConnectToHost, .dnsLookupFailed,
             .networkConnectionLost, .secureConnectionFailed, .serverCertificateUntrusted,
             .serverCertificateHasBadDate, .serverCertificateHasUnknownRoot, .clientCertificateRejected,
             .cannotLoadFromNetwork, .resourceUnavailable:
            return tailscaleHint ? .tailscaleNotConnected : .serverUnreachable
        default:
            return .serverUnreachable
        }
    }

    /// Maps an HTTP status from either server. `nil` means the status is a success.
    public static func map(status: Int, message: String? = nil) -> DiscairError? {
        switch status {
        case 200..<300: nil
        case 401, 403: .unauthorised(message: message)
        case 429: .tooManyAttempts(message: message)
        default: .server(status: status, message: message)
        }
    }
}
