import DiscairCore
import DiscairNavidrome
import Foundation
import Testing
@testable import DiscairUI

/// A fake Navidrome holding `total` songs; answers `search3` by songOffset and songCount like the real one.
private final class SongServer: HTTPTransport, @unchecked Sendable {
    let total: Int
    var failFrom: Int?
    private let lock = NSLock()
    private var count = 0
    var requests: Int { lock.withLock { count } }
    init(total: Int, failFrom: Int? = nil) { self.total = total; self.failFrom = failFrom }
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        lock.withLock { count += 1 }
        let q = URLComponents(url: request.url!, resolvingAgainstBaseURL: false)?.queryItems ?? []
        let offset = Int(q.first { $0.name == "songOffset" }?.value ?? "0") ?? 0
        let size = Int(q.first { $0.name == "songCount" }?.value ?? "0") ?? 0
        if let failFrom, offset >= failFrom { throw URLError(.cannotConnectToHost) }
        let songs = (min(offset, total)..<min(offset + size, total)).map { #"{"id":"s\#($0)","title":"T\#($0)","artist":"A"}"# }
        let json = #"{"subsonic-response":{"status":"ok","version":"1.16.1","searchResult3":{"song":[\#(songs.joined(separator: ","))]}}}"#
        return (Data(json.utf8), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

@MainActor
struct BulkSongLoadTests {
    private func model() -> LibraryModel {
        let m = LibraryModel()
        m.apply(newest: [], first: [], artists: [], picks: [])
        return m
    }
    private func client(_ t: SongServer) throws -> NavidromeClient {
        try NavidromeClient(baseURL: URL(string: "https://navi.example.ts.net")!, credential: Credential(username: "o", password: "pw"), transport: t)
    }

    @Test func readsTheWholeLibraryInOrderWithoutGapsOrRepeats() async throws {
        let server = SongServer(total: 4321)
        let m = model()
        await m.loadAllSongs(navidrome: try client(server))
        #expect(m.songs.count == 4321)
        #expect(m.songs.map(\.remoteID) == (0..<4321).map { "s\($0)" })
        #expect(Set(m.songs.map(\.id)).count == 4321)
        #expect(!m.songsHaveMore && m.songsError == nil && !m.songsLoading)
    }

    @Test func anExactMultipleOfThePageSizeStillEnds() async throws {
        let m = model()
        await m.loadAllSongs(navidrome: try client(SongServer(total: 3000)))
        #expect(m.songs.count == 3000 && !m.songsHaveMore)
    }

    @Test func aSmallLibraryNeedsOnlyTheFirstPage() async throws {
        let server = SongServer(total: 50)
        let m = model()
        await m.loadAllSongs(navidrome: try client(server))
        #expect(m.songs.count == 50 && server.requests == 1)
    }

    @Test func aFailureKeepsWhatLoadedAndCanBeContinued() async throws {
        let server = SongServer(total: 3000, failFrom: 1200)
        let m = model()
        let c = try client(server)
        await m.loadAllSongs(navidrome: c)
        #expect(m.songsError != nil && m.songsHaveMore)
        #expect(m.songs.count == 200)          // the first page; the failed group added nothing, nothing is duplicated
        server.failFrom = nil
        await m.loadAllSongs(navidrome: c)
        #expect(m.songs.count == 3000 && m.songsError == nil)
        #expect(Set(m.songs.compactMap(\.remoteID)).count == 3000)
    }
}
