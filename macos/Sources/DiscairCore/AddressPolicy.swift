import Foundation

/// Transport rules (contract section 3): `https` for any host; plain `http` only for RFC 1918 addresses,
/// `.local` names and 100.64.0.0/10. Everything else over http is blocked. Credentials in the URL are refused.
public enum AddressPolicy {
    /// Validates a server base URL and returns it normalised (no trailing path slash, no query, no fragment).
    public static func validate(_ text: String) throws -> URL {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let comps = URLComponents(string: trimmed), let scheme = comps.scheme?.lowercased() else {
            throw DiscairError.insecureOrInvalidAddress(reason: .notAURL)
        }
        guard scheme == "http" || scheme == "https" else {
            throw DiscairError.insecureOrInvalidAddress(reason: .unsupportedScheme)
        }
        guard let host = comps.host, !host.isEmpty else {
            throw DiscairError.insecureOrInvalidAddress(reason: .missingHost)
        }
        guard comps.user == nil, comps.password == nil else {
            throw DiscairError.insecureOrInvalidAddress(reason: .embeddedCredentials)
        }
        if scheme == "http", !isPlainHTTPAllowed(host: host) {
            throw DiscairError.insecureOrInvalidAddress(reason: .publicHTTP)
        }
        var clean = comps
        clean.scheme = scheme
        clean.query = nil
        clean.fragment = nil
        while clean.path.hasSuffix("/") { clean.path.removeLast() }
        guard let url = clean.url else { throw DiscairError.insecureOrInvalidAddress(reason: .notAURL) }
        return url
    }

    /// Validates an already-built URL (used by the URL builders before they add any secret).
    public static func validate(_ url: URL) throws -> URL { try validate(url.absoluteString) }

    /// True when the URL is plain http (the UI shows the "unencrypted" badge).
    public static func isUnencrypted(_ url: URL) -> Bool { url.scheme?.lowercased() == "http" }

    public static func isPlainHTTPAllowed(host rawHost: String) -> Bool {
        let host = rawHost.lowercased().trimmingCharacters(in: CharacterSet(charactersIn: "."))
        if let v4 = IPv4(host) { return v4.isPrivate || v4.isCGNAT }
        // Only strict dotted-decimal counts as an address; anything else is treated as a name.
        return host.hasSuffix(".local") && host.count > ".local".count
    }

    /// Host belongs to Tailscale: a `*.ts.net` name or an address in 100.64.0.0/10.
    public static func isTailscaleHost(_ rawHost: String) -> Bool {
        let host = rawHost.lowercased().trimmingCharacters(in: CharacterSet(charactersIn: "."))
        if let v4 = IPv4(host) { return v4.isCGNAT }
        return host.hasSuffix(".ts.net")
    }
}

/// Strict dotted-decimal IPv4. Rejects octal, hex, short forms and trailing text, so
/// `192.168.1.1.example.com` and `0xC0.168.1.1` are names, not addresses.
public struct IPv4: Equatable, Sendable {
    public let octets: [UInt8]

    public init?(_ text: String) {
        let parts = text.split(separator: ".", omittingEmptySubsequences: false)
        guard parts.count == 4 else { return nil }
        var out: [UInt8] = []
        for p in parts {
            guard !p.isEmpty, p.count <= 3, p.allSatisfy({ $0 >= "0" && $0 <= "9" }),
                  !(p.count > 1 && p.first == "0"), let n = UInt8(p) else { return nil }
            out.append(n)
        }
        octets = out
    }

    /// 10/8, 172.16/12, 192.168/16.
    public var isPrivate: Bool {
        octets[0] == 10 || (octets[0] == 172 && (16...31).contains(octets[1])) || (octets[0] == 192 && octets[1] == 168)
    }

    /// 100.64.0.0/10 (Tailscale and carrier-grade NAT).
    public var isCGNAT: Bool { octets[0] == 100 && (64...127).contains(octets[1]) }
}
