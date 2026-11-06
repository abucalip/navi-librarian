import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

@Suite("Knowledge pages") struct KnowledgeTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func decode<T: Decodable>(_ type: T.Type, _ name: String) throws -> T {
        try JSONDecoder().decode(T.self, from: insightsBody(name))
    }

    @Test func albumKeepsEditionsTracksAndCredits() throws {
        let a = try decode(KnowledgeAlbum.self, "knowledge_album")
        #expect(a.album.owned && a.releaseGroup?.type == "release_group")
        #expect(a.editions.first?.country == "GB" && a.editions.first?.trackCount == 1 && a.editions.first?.status == "official")
        #expect(a.tracks.first?.title == "Example Song" && a.tracks.first?.position == "1/1")
        #expect(a.people.first?.credits.map(\.label) == ["executive", "guitar"])
        #expect(a.people.first?.credits.last?.track == "Example Song")
        #expect(a.labels.first?.entity.name == "Example Records" && a.sources["musicbrainz_dump"]?.coverage == "loaded")
        #expect(a.notLoaded.contains("catalogue_numbers") && !a.creditsTruncated)
    }

    @Test func personHasLifeSpanAndLibraryWhy() throws {
        let p = try decode(KnowledgePerson.self, "knowledge_person")
        #expect(p.lifeSpan?.begin == "1970" && p.lifeSpan?.ended == false)
        #expect(p.inLibrary.first?.why == "credited as executive, guitar on Example Song")
        #expect(p.inLibrary.first?.credits.first?.relation == "producer")
    }

    @Test func pendingSliceIsReportedNotHidden() throws {
        let p = try decode(KnowledgePerson.self, "knowledge_person_slice_pending")
        #expect(p.sources["musicbrainz_dump"]?.coverage == "pending")
        #expect(p.sources["musicbrainz_dump"]?.dumpTimestamp == nil)
    }

    @Test func labelCatalogueReadsRelations() throws {
        let l = try decode(KnowledgeLabel.self, "knowledge_label")
        #expect(l.ownedCatalogue.first?.credits.first?.relation == "publisher")
        #expect(l.ownedCatalogue.first?.credits.first?.direction == "out")
    }

    @Test func workHasVersionsPerformersAndSummary() throws {
        let w = try decode(KnowledgeWork.self, "knowledge_work")
        #expect(w.recordings == 2 && w.covers == 1 && w.inLibrary == 1)
        #expect(w.writtenBy.first?.credits.first?.relation == "composer")
        let v = try #require(w.versions.first)
        #expect(v.owned && v.performers.first?.credits.first?.label == "guitar" && v.albums.first?.album.owned == true)
    }

    @Test func recordingWorksCountsOtherRecordings() throws {
        let r = try decode(KnowledgeRecordingWorks.self, "knowledge_recording_works")
        #expect(r.works.first?.otherRecordings == 1 && r.works.first?.work.type == "work")
    }

    @Test func unknownAndMissingFieldsDoNotBreakAPage() throws {
        let json = #"{"label":{"mbid":"m","canonical_name":"L","type":"label"},"surprise":[1]}"#
        let l = try JSONDecoder().decode(KnowledgeLabel.self, from: Data(json.utf8))
        #expect(l.label.owned == false && l.ownedCatalogue.isEmpty && l.sources.isEmpty)
    }

    @Test func clientAsksForOnePageByMBID() async throws {
        let t = MockTransport { _, _ in (200, try insightsBody("knowledge_person")) }
        let c = try LibrarianClient(baseURL: base, credential: cred, transport: t)
        let p = try await c.knowledgePerson(mbid: "00000001-0000-4000-8000-000000000000")
        #expect(p.person.name == "Example Artist")
        #expect(t.sent[0].httpMethod == "GET" && t.sent[0].url!.path == "/api/knowledge/person")
        #expect(t.sent[0].url!.query == "mbid=00000001-0000-4000-8000-000000000000")
    }
}
