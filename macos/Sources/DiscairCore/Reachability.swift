import Foundation
#if canImport(Darwin)
import Darwin
#endif

/// One network interface as seen from `getifaddrs` (or a test double).
public struct NetworkInterface: Equatable, Sendable {
    public let name: String
    public let isUp: Bool
    public let isLoopback: Bool
    public let addresses: [String]

    public init(name: String, isUp: Bool, isLoopback: Bool = false, addresses: [String]) {
        self.name = name; self.isUp = isUp; self.isLoopback = isLoopback; self.addresses = addresses
    }
}

public enum NetworkInterfaces {
    /// Reads the interfaces from the system. No Tailscale SDK is involved.
    public static func current() -> [NetworkInterface] {
        var head: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&head) == 0, let first = head else { return [] }
        defer { freeifaddrs(head) }
        var byName: [String: (up: Bool, loop: Bool, addrs: [String])] = [:]
        var cursor: UnsafeMutablePointer<ifaddrs>? = first
        while let ifa = cursor {
            defer { cursor = ifa.pointee.ifa_next }
            let name = String(cString: ifa.pointee.ifa_name)
            let flags = Int32(ifa.pointee.ifa_flags)
            var entry = byName[name] ?? (flags & IFF_UP != 0 && flags & IFF_RUNNING != 0, flags & IFF_LOOPBACK != 0, [])
            if let sa = ifa.pointee.ifa_addr, sa.pointee.sa_family == UInt8(AF_INET) || sa.pointee.sa_family == UInt8(AF_INET6) {
                var host = [CChar](repeating: 0, count: Int(NI_MAXHOST))
                if getnameinfo(sa, socklen_t(sa.pointee.sa_len), &host, socklen_t(host.count), nil, 0, NI_NUMERICHOST) == 0 {
                    // Drop the zone suffix ("fe80::1%utun4").
                    entry.addrs.append(String(decoding: host.prefix { $0 != 0 }.map { UInt8(bitPattern: $0) }, as: UTF8.self).split(separator: "%").first.map(String.init) ?? "")
                }
            }
            byName[name] = entry
        }
        return byName.map { NetworkInterface(name: $0.key, isUp: $0.value.up, isLoopback: $0.value.loop, addresses: $0.value.addrs) }
            .sorted { $0.name < $1.name }
    }
}

public enum TailscaleDetector {
    /// Tailscale is considered connected when an up `utun` interface holds an address in 100.64.0.0/10
    /// or in Tailscale's IPv6 range `fd7a:115c:a1e0::/48`.
    public static func isConnected(_ interfaces: [NetworkInterface]) -> Bool {
        interfaces.contains { iface in
            iface.isUp && iface.name.hasPrefix("utun") && iface.addresses.contains(where: isTailscaleAddress)
        }
    }

    static func isTailscaleAddress(_ address: String) -> Bool {
        if let v4 = IPv4(address) { return v4.isCGNAT }
        return address.lowercased().hasPrefix("fd7a:115c:a1e0:")
    }

    /// True when at least one non-loopback interface is up with an address (anything but link-local alone).
    public static func hasAnyNetwork(_ interfaces: [NetworkInterface]) -> Bool {
        interfaces.contains { iface in
            iface.isUp && !iface.isLoopback && iface.addresses.contains { !$0.lowercased().hasPrefix("fe80:") && !$0.hasPrefix("169.254.") }
        }
    }
}

/// The result of asking one server address "are you there?".
public enum ProbeOutcome: Equatable, Sendable {
    /// Any HTTP answer below 500 counts: the host is up even if it wants a login.
    case reachable
    case failed(DiscairError)
}

public protocol Prober: Sendable {
    func probe(_ url: URL) async -> ProbeOutcome
}

/// Probes with a short-timeout GET. Redirects are not followed.
public struct HTTPProber: Prober {
    private let session: URLSession
    public init(timeout: TimeInterval = 3) {
        let cfg = URLSessionConfiguration.ephemeral
        cfg.timeoutIntervalForRequest = timeout
        cfg.timeoutIntervalForResource = timeout
        cfg.waitsForConnectivity = false
        cfg.httpCookieStorage = nil
        session = URLSession(configuration: cfg, delegate: NoRedirectDelegate(), delegateQueue: nil)
    }

    public func probe(_ url: URL) async -> ProbeOutcome {
        do {
            _ = try AddressPolicy.validate(url)
            let (_, response) = try await session.data(from: url)
            guard let http = response as? HTTPURLResponse else { return .failed(.serverUnreachable) }
            return http.statusCode < 500 ? .reachable : .failed(.server(status: http.statusCode, message: nil))
        } catch {
            return .failed(ErrorMapping.map(error))
        }
    }
}

/// Refuses every redirect (the answer of the first host is the answer).
final class NoRedirectDelegate: NSObject, URLSessionTaskDelegate, Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest) async -> URLRequest? { nil }
}

public struct ProfileSelection: Equatable, Sendable {
    public let profile: Profile
    /// `true` when the owner picked it by hand (no probing was done).
    public let isManualOverride: Bool
}

/// Picks the active profile: manual override first, otherwise LAN, then Tailscale, then others.
/// A profile is reachable when both its Librarian and Navidrome addresses answer.
public struct ProfileResolver: Sendable {
    private let prober: any Prober
    private let interfaces: @Sendable () -> [NetworkInterface]

    public init(prober: any Prober = HTTPProber(),
                interfaces: @escaping @Sendable () -> [NetworkInterface] = NetworkInterfaces.current) {
        self.prober = prober
        self.interfaces = interfaces
    }

    public func select(from list: ProfileList) async throws -> ProfileSelection {
        if let id = list.overrideID {
            guard let chosen = list.profiles.first(where: { $0.id == id }) else { throw ProfileError.notFound }
            return ProfileSelection(profile: chosen, isManualOverride: true)
        }
        let nics = interfaces()
        guard TailscaleDetector.hasAnyNetwork(nics) else { throw DiscairError.noNetwork }
        let tailscaleUp = TailscaleDetector.isConnected(nics)
        var sawTailscaleDown = false
        var lastFailure: DiscairError = .serverUnreachable
        for profile in list.probeOrder {
            if profile.usesTailscaleAddress && !tailscaleUp {
                sawTailscaleDown = true
                continue // no point waiting for a timeout
            }
            if let failure = await firstFailure(of: profile) {
                lastFailure = failure
                continue
            }
            return ProfileSelection(profile: profile, isManualOverride: false)
        }
        if sawTailscaleDown { throw DiscairError.tailscaleNotConnected }
        throw lastFailure
    }

    /// Single check of one profile (used by the manual override and the retry action).
    public func check(_ profile: Profile) async -> DiscairError? {
        let nics = interfaces()
        guard TailscaleDetector.hasAnyNetwork(nics) else { return .noNetwork }
        if profile.usesTailscaleAddress && !TailscaleDetector.isConnected(nics) { return .tailscaleNotConnected }
        return await firstFailure(of: profile)
    }

    private func firstFailure(of profile: Profile) async -> DiscairError? {
        async let lib = prober.probe(profile.librarianURL)
        async let navi = prober.probe(profile.navidromeURL)
        for outcome in await [lib, navi] {
            if case .failed(let e) = outcome { return e }
        }
        return nil
    }
}
