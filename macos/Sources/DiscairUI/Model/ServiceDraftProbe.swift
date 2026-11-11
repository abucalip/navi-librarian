import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Foundation

/// The edit sheet's Test (`docs/redesign.md` F7). The Librarian's test routes read what is saved and take no body, so a Test
/// after a change would report on the old values. This asks each service directly with the values typed in the sheet, from this
/// Mac, and changes nothing that is saved. Cancel therefore leaves the saved settings as they were.
///
/// A saved secret is never readable here, so a changed address or username with an empty secret cannot be tested: that says so
/// instead of guessing (`needsSecret`).
public struct ServiceDraftProbe: Sendable {
    let transport: any HTTPTransport
    public init(transport: any HTTPTransport = URLSessionTransport(keepCookies: false, requestTimeout: 10)) { self.transport = transport }

    /// What a sheet's Test should do for a draft.
    public enum Plan: Equatable, Sendable {
        /// Nothing was changed, so the saved values are the typed ones and the server's own test answers for them.
        case useSaved
        /// Ask the service directly with the typed values.
        case probe
        /// The typed values need a secret that is saved on the server and cannot be read back.
        case needsSecret(String)
    }

    /// Whether the draft differs from what the server holds, and whether it can be tested as typed.
    public static func plan(for id: ServicesModel.ServiceID, draft d: ServiceDraft, saved: ServiceDraft) -> Plan {
        func t(_ s: String) -> String { s.trimmingCharacters(in: .whitespacesAndNewlines) }
        let secretTyped = !d.secret.isEmpty
        let changedAddress = t(d.address) != t(saved.address)
        let changedUser = t(d.username) != t(saved.username)
        switch id {
        case .navidrome:
            if !changedAddress && !changedUser && !secretTyped { return .useSaved }
            return secretTyped ? .probe : .needsSecret("Type the password to test a changed address or username. A saved password cannot be read back.")
        case .slskd:
            if !changedAddress && !secretTyped { return .useSaved }
            return secretTyped ? .probe : .needsSecret("Type the API key to test a changed address. A saved key cannot be read back.")
        case .lastfm:
            if !secretTyped { return .useSaved }
            return .probe
        case .listenbrainz:
            if !changedUser { return .useSaved }
            return .probe
        case .discogs:
            if !secretTyped { return .useSaved }
            return .probe
        default: return .useSaved
        }
    }

    public func test(_ id: ServicesModel.ServiceID, draft d: ServiceDraft) async -> ServiceTestResult {
        let address = d.address.trimmingCharacters(in: .whitespacesAndNewlines)
        let user = d.username.trimmingCharacters(in: .whitespacesAndNewlines)
        switch id {
        case .navidrome: return await navidrome(address: address, username: user, password: d.secret)
        case .slskd: return await slskd(address: address, apiKey: d.secret)
        case .lastfm: return await lastFM(apiKey: d.secret.trimmingCharacters(in: .whitespacesAndNewlines))
        case .listenbrainz: return await listenBrainz(username: user)
        case .discogs: return await discogs(token: d.secret.trimmingCharacters(in: .whitespacesAndNewlines))
        default: return ServiceTestResult(ok: false, status: "not_configured", message: "This service has nothing to test here.")
        }
    }

    // MARK: Services

    func navidrome(address: String, username: String, password: String) async -> ServiceTestResult {
        guard let url = URL(string: address), !address.isEmpty else { return Self.failed("Enter the Navidrome address first.") }
        do {
            let client = try NavidromeClient(baseURL: url, credential: Credential(username: username, password: password), transport: transport)
            try await client.ping()
            return ServiceTestResult(ok: true, status: "connected")
        } catch let e as DiscairError {
            if case .unauthorised = e { return ServiceTestResult(ok: false, status: "authentication_failed") }
            return Self.failed(e.summary)
        } catch { return Self.failed("") }
    }

    func slskd(address: String, apiKey: String) async -> ServiceTestResult {
        guard let url = URL(string: address.trimmingSlash + "/api/v0/server"), ["http", "https"].contains(url.scheme), url.host != nil else {
            return Self.failed("The slskd address must be a valid http or https address.")
        }
        var r = URLRequest(url: url); r.setValue(apiKey, forHTTPHeaderField: "X-API-KEY")
        return await run(r) { ServiceTestResult(ok: true, status: "connected") }
    }

    func lastFM(apiKey: String) async -> ServiceTestResult {
        var c = URLComponents(string: "https://ws.audioscrobbler.com/2.0/")!
        c.queryItems = [.init(name: "method", value: "chart.getTopArtists"), .init(name: "api_key", value: apiKey), .init(name: "format", value: "json"), .init(name: "limit", value: "1")]
        var r = URLRequest(url: c.url!); r.setValue("Discair/0.1", forHTTPHeaderField: "User-Agent")
        // Last.fm answers a bad key with a JSON `error`, often under a 403.
        return await run(r, rejectOnError: true) { ServiceTestResult(ok: true, status: "connected") }
    }

    func listenBrainz(username: String) async -> ServiceTestResult {
        guard !username.isEmpty, let encoded = username.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed.subtracting(CharacterSet(charactersIn: "/"))),
              let url = URL(string: "https://api.listenbrainz.org/1/user/\(encoded)/listens?count=1") else { return Self.failed("Enter the ListenBrainz username first.") }
        var r = URLRequest(url: url); r.setValue("Discair/0.1", forHTTPHeaderField: "User-Agent")
        return await run(r, notFound: true) { ServiceTestResult(ok: true, status: "connected") }
    }

    func discogs(token: String) async -> ServiceTestResult {
        var r = URLRequest(url: URL(string: "https://api.discogs.com/oauth/identity")!)
        r.setValue("Discogs token=\(token)", forHTTPHeaderField: "Authorization"); r.setValue("Discair/1.0", forHTTPHeaderField: "User-Agent")
        return await run(r) { ServiceTestResult(ok: true, status: "connected") }
    }

    // MARK: Pieces

    private func run(_ request: URLRequest, rejectOnError: Bool = false, notFound: Bool = false, success: () -> ServiceTestResult) async -> ServiceTestResult {
        do {
            let (data, http) = try await transport.send(request)
            if http.statusCode == 401 || http.statusCode == 403 { return ServiceTestResult(ok: false, status: "authentication_failed") }
            if notFound, http.statusCode == 404 { return ServiceTestResult(ok: false, status: "not_found") }
            if rejectOnError, (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["error"] != nil { return ServiceTestResult(ok: false, status: "authentication_failed") }
            guard (200..<300).contains(http.statusCode) else { return Self.failed("") }
            return success()
        } catch { return Self.failed("") }
    }

    private static func failed(_ message: String) -> ServiceTestResult { ServiceTestResult(ok: false, status: "connection_failed", message: message) }
}

private extension String {
    var trimmingSlash: String { hasSuffix("/") ? String(dropLast()) : self }
}
