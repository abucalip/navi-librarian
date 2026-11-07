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

@Suite("Knowledge graph data") struct KnowledgeGraphTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func pathsBody(_ name: String, file: String = #filePath) throws -> Data {
        let url = URL(fileURLWithPath: file).deletingLastPathComponent().appending(path: "Fixtures/\(name).json")
        let object = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
        return try JSONSerialization.data(withJSONObject: (object["response"] as! [String: Any])["body"]!)
    }

    @Test func connectionsKeepDepthCreditAndEvidence() throws {
        let c = try JSONDecoder().decode(KnowledgeConnections.self, from: insightsBody("knowledge_connections"))
        #expect(c.start.name == "Example Artist" && c.truncated == nil && c.nextCursor == nil)
        let first = try #require(c.hops.first)
        #expect(first.depth == 1 && first.credit && first.entity.type == "work")
        #expect(first.evidence.first?.relation == "composer" && first.evidence.first?.direction == "out")
        #expect(c.sources["musicbrainz_dump"]?.coverage == "loaded")
    }

    @Test func connectionsPagesCarryACursor() throws {
        let p1 = try JSONDecoder().decode(KnowledgeConnections.self, from: insightsBody("knowledge_connections_page1"))
        #expect(p1.nextCursor != nil)
    }

    @Test func okPathHasStopsWithReasonsAndEvidence() throws {
        let p = try JSONDecoder().decode(KnowledgePaths.self, from: pathsBody("paths_scene_path"))
        #expect(p.status == "ok" && p.kind == "scene_path" && p.start.owned)
        let reason = try #require(p.stops.first?.reasons.first)
        #expect(reason.code == "same_area" && !reason.text.isEmpty && reason.via?.type == "area" && reason.anchor?.owned == true)
        #expect(reason.evidence.first?.source == "musicbrainz_dump")
        #expect(p.stops.allSatisfy { $0.reasonCount >= $0.reasons.count })
    }

    @Test func sidemanToLeaderStopsAreArtistsExplainedBySidemanOn() throws {
        let p = try JSONDecoder().decode(KnowledgePaths.self, from: pathsBody("paths_sideman_to_leader"))
        #expect(p.status == "ok" && p.kind == "sideman_to_leader" && p.truncated == nil && p.start.owned)
        #expect(!p.stops.isEmpty && p.stops.allSatisfy { $0.entity.type == "artist" })
        let reason = try #require(p.stops.first?.reasons.first)
        #expect(reason.code == "sideman_on" && !reason.text.isEmpty)
        #expect(reason.via?.type == "release" && reason.anchor?.type == "recording")
        #expect(reason.evidence.contains { $0.source == "musicbrainz_dump_releases" })
    }

    @Test func sidemanToLeaderTruncatedKeepsTheStopsNote() throws {
        let p = try JSONDecoder().decode(KnowledgePaths.self, from: pathsBody("paths_sideman_to_leader_truncated"))
        #expect(p.status == "ok" && p.truncated == "stops" && p.stops.count == 30)
        #expect(p.stops.allSatisfy { $0.entity.type == "artist" && !$0.reasons.isEmpty })
    }

    @Test func emptyPathHasNoStops() throws {
        for kind in PathKind.allCases {
            let p = try JSONDecoder().decode(KnowledgePaths.self, from: pathsBody("paths_\(kind.rawValue)_empty"))
            #expect(p.status == "empty" && p.stops.isEmpty)
        }
    }

    @Test func placeHasCoordinatesAreaChainAndRecordings() throws {
        let p = try JSONDecoder().decode(KnowledgePlace.self, from: insightsBody("knowledge_place"))
        #expect(p.facts?.kind == "studio" && p.facts?.hasCoordinates == true && p.facts?.latitude == 48.85)
        #expect(p.area.first?.area.kind == "city" && p.area.first?.containedIn.first?.isoCode == "XX")
        #expect(p.recordings.first?.recording.name == "Example Song (cover)" && p.recordings.first?.credits.first?.relation == "recording location")
        #expect(p.events.first?.facts?.begin == "1971-06" && p.events.first?.facts?.cancelled == false)
        #expect(p.people.first?.credits.first?.relation == "owner")
    }

    @Test func eventHasPlacesAndDates() throws {
        let e = try JSONDecoder().decode(KnowledgeEvent.self, from: insightsBody("knowledge_event"))
        #expect(e.facts?.kind == "festival" && e.facts?.end == "1971-06")
        #expect(e.places.first?.facts?.hasCoordinates == true && e.places.first?.credits.first?.relation == "held at")
        #expect(e.notLoaded.count == 2)
    }

    @Test func clientSendsConnectionsAndPathsQueries() async throws {
        let t = MockTransport { req, _ in
            req.url!.path.hasSuffix("paths") ? (200, try pathsBody("paths_label_path")) : (200, try insightsBody("knowledge_connections"))
        }
        let c = try LibrarianClient(baseURL: base, credential: cred, transport: t)
        _ = try await c.knowledgeConnections(mbid: "m1", type: "artist", depth: 2, limit: 25, creditsOnly: true, cursor: "abc")
        _ = try await c.knowledgePaths(mbid: "m1", kind: .labelPath)
        #expect(t.sent[0].url!.path == "/api/knowledge/connections")
        #expect(t.sent[0].url!.query == "mbid=m1&type=artist&depth=2&limit=25&credits_only=true&cursor=abc")
        #expect(t.sent[1].url!.query == "kind=label_path&mbid=m1&type=artist")
    }

    @Test func atlasKeepsPinnableOwnedFirstPlacesAndDropsTheRest() throws {
        let json = #"""
        {"places":[
          {"entity":{"mbid":"p1","canonical_name":"Paris Studio","type":"place","owned":false},"kind":"studio","latitude":48.85,"longitude":2.41,"recordings":4,"owned_recordings":3},
          {"entity":{"mbid":"p2","canonical_name":"Off the map","type":"place","owned":false},"latitude":123.0,"longitude":2.0,"recordings":1,"owned_recordings":0},
          {"entity":{"mbid":"p3","canonical_name":"No coordinates","type":"place","owned":false},"recordings":1,"owned_recordings":0}],
         "truncated":true,"sources":{"musicbrainz_dump":{"coverage":"loaded"}}}
        """#
        let a = try JSONDecoder().decode(KnowledgeAtlas.self, from: Data(json.utf8))
        #expect(a.places.map(\.id) == ["p1"] && a.truncated)
        #expect(a.places[0].ownedRecordings == 3 && a.places[0].recordings == 4 && a.places[0].kind == "studio")
    }

    @Test func clientAsksForTheAtlasWithALimit() async throws {
        let t = MockTransport { _, _ in (200, Data(#"{"places":[],"truncated":false}"#.utf8)) }
        let c = try LibrarianClient(baseURL: base, credential: cred, transport: t)
        let a = try await c.knowledgeAtlas(limit: 200)
        #expect(a.places.isEmpty)
        #expect(t.sent[0].url!.path == "/api/knowledge/atlas" && t.sent[0].url!.query == "limit=200")
    }
}
