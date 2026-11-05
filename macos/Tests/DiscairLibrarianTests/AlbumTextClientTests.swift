import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

@Suite("Librarian album text") struct AlbumTextClientTests {
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func client(_ t: MockTransport) throws -> LibrarianClient {
        try LibrarianClient(baseURL: URL(string: "https://lib.example.ts.net")!, credential: cred, transport: t)
    }

    @Test func reviewsAreReadAndTheNamesAreEncoded() async throws {
        let body = #"{"reviews":[{"source":"Outlet","quote":"Fine.","url":"https://o.example/r"}],"retryable":true}"#
        let t = MockTransport { _, _ in (200, Data(body.utf8)) }
        let r = try await client(t).albumReviews(artist: "Simon & Garfunkel", album: "Bridge+Over #1?")
        #expect(r.reviews == [AlbumReview(source: "Outlet", quote: "Fine.", url: "https://o.example/r")] && r.retryable == true)
        let q = t.sent[0].url!.query!
        #expect(t.sent[0].url!.path == "/api/album-reviews")
        #expect(q == "artist=Simon%20%26%20Garfunkel&album=Bridge%2BOver%20%231%3F")
    }

    @Test func descriptionReadsParagraphsAndAnEmptyOneIsNotAnError() async throws {
        let t = MockTransport { _, _ in (200, Data(#"{"paragraphs":["One."],"source":"Apple Music","url":"https://m.example/a"}"#.utf8)) }
        let d = try await client(t).albumDescription(artist: "A", album: "B")
        #expect(d.paragraphs == ["One."] && d.source == "Apple Music" && d.license == nil)
        let t2 = MockTransport { _, _ in (200, Data(#"{"paragraphs":[]}"#.utf8)) }
        #expect(try await client(t2).albumDescription(artist: "A", album: "B").paragraphs.isEmpty)
    }

    @Test func aBadRequestSurfacesAsAnError() async throws {
        let t = MockTransport { _, _ in (400, Data(#"{"detail":"artist and album are required"}"#.utf8)) }
        await #expect(throws: DiscairError.self) { _ = try await client(t).albumReviews(artist: "", album: "") }
    }

    @Test func aPageKeyWithSpacesIsEncodedOnce() async throws {
        let t = MockTransport { _, _ in (200, Data(#"{"sections":{},"done":{"partial":false}}"#.utf8)) }
        _ = try await client(t).artistPage(name: "Pink Floyd", id: "ar1")
        #expect(t.sent[0].url!.absoluteString.hasPrefix("https://lib.example.ts.net/api/artists/pink%20floyd?"))
    }
}
