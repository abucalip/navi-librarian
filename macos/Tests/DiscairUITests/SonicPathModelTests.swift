import DiscairAudio
import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

@MainActor
@Suite struct SonicPathModelTests {
    private func item(_ id: String) -> QueueItem { QueueItem(songID: id, title: "T\(id)", artist: "A", album: "Al", albumID: nil, coverArt: nil, duration: 100, mbid: nil) }
    private func response(_ ids: [String]) throws -> SonicResponse {
        let tracks = ids.map { #"{"navidrome_id":"\#($0)","title":"T\#($0)","artist":"A"}"# }.joined(separator: ",")
        return try JSONDecoder().decode(SonicResponse.self, from: Data(#"{"status":"ok","tracks":[\#(tracks)]}"#.utf8))
    }

    @Test func keepsTheServersOrderAndAsksForTenSteps() async throws {
        let m = SonicPathModel(start: item("a"), target: item("z"))
        let r = try response(["a", "m", "m", "z"])
        await m.load { s, e, n in #expect(s == "a" && e == "z" && n == 10); return r }
        guard case .ready(let steps) = m.phase else { Issue.record("not ready"); return }
        #expect(steps.map(\.songID) == ["a", "m", "z"])
    }

    @Test func aPathWithoutStepsIsEmpty() async throws {
        let m = SonicPathModel(start: item("a"), target: item("z"))
        let r = try response([])
        await m.load { _, _, _ in r }
        #expect(m.phase == .empty)
    }

    @Test func aFailureBecomesWords() async {
        let m = SonicPathModel(start: item("a"), target: item("z"))
        await m.load { _, _, _ in throw URLError(.notConnectedToInternet) }
        guard case .failed(let text) = m.phase else { Issue.record("not failed"); return }
        #expect(!text.isEmpty)
    }
}
