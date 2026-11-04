import Foundation

/// One request in, one answer out. Tests supply a fake; the app uses `URLSessionTransport`.
public protocol HTTPTransport: Sendable {
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse)
}

/// `URLSession` with no redirects, no cache and no credential storage of its own.
/// Cookies are kept in memory only when asked for (the Librarian session cookie).
public struct URLSessionTransport: HTTPTransport {
    private let session: URLSession

    public init(keepCookies: Bool, requestTimeout: TimeInterval = 30) {
        let cfg = URLSessionConfiguration.ephemeral
        cfg.timeoutIntervalForRequest = requestTimeout
        cfg.urlCache = nil
        cfg.requestCachePolicy = .reloadIgnoringLocalCacheData
        // An ephemeral configuration already has its own in-memory jar; a bare `HTTPCookieStorage()` never stores anything.
        if !keepCookies { cfg.httpCookieStorage = nil }
        cfg.httpShouldSetCookies = keepCookies
        session = URLSession(configuration: cfg, delegate: NoRedirectDelegate(), delegateQueue: nil)
    }

    public func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw DiscairError.serverUnreachable }
        return (data, http)
    }
}
