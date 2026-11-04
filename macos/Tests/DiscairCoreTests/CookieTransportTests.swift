import Foundation
import Network
import Testing
@testable import DiscairCore

/// A real URLSession against a tiny local server: login sets a cookie, the next call must carry it. A fake transport
/// cannot catch a cookie jar that stores nothing, which is how the Librarian calls were refused after a good login.
@Suite("Cookie transport", .serialized)
struct CookieTransportTests {
    final class Server: @unchecked Sendable {
        let listener: NWListener
        init() throws { listener = try NWListener(using: .tcp, on: .any) }
        func start() async -> UInt16 {
            listener.newConnectionHandler = { c in
                c.start(queue: .global())
                c.receive(minimumIncompleteLength: 1, maximumLength: 8192) { data, _, _, _ in
                    let req = String(decoding: data ?? Data(), as: UTF8.self)
                    let post = req.hasPrefix("POST")
                    let hasCookie = req.contains("s=abc")
                    let head = post ? "HTTP/1.1 200 OK\r\nSet-Cookie: s=abc; HttpOnly; SameSite=Strict; Path=/\r\n"
                        : (hasCookie ? "HTTP/1.1 200 OK\r\n" : "HTTP/1.1 401 Unauthorized\r\n")
                    c.send(content: (head + "Content-Length: 2\r\nConnection: close\r\n\r\n{}").data(using: .utf8), completion: .contentProcessed { _ in c.cancel() })
                }
            }
            return await withCheckedContinuation { k in
                listener.stateUpdateHandler = { if case .ready = $0 { k.resume(returning: self.listener.port!.rawValue); self.listener.stateUpdateHandler = nil } }
                listener.start(queue: .global())
            }
        }
    }

    private func status(keepCookies: Bool) async throws -> Int {
        let server = try Server(); let port = await server.start()
        defer { server.listener.cancel() }
        let t = URLSessionTransport(keepCookies: keepCookies)
        var login = URLRequest(url: URL(string: "http://127.0.0.1:\(port)/login")!); login.httpMethod = "POST"
        _ = try await t.send(login)
        return try await t.send(URLRequest(url: URL(string: "http://127.0.0.1:\(port)/data")!)).1.statusCode
    }

    @Test func sessionCookieIsSentAfterLogin() async throws { #expect(try await status(keepCookies: true) == 200) }
    @Test func withoutCookiesTheSecondCallIsRefused() async throws { #expect(try await status(keepCookies: false) == 401) }
}
