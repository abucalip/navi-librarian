import Foundation
import Testing
import DiscairLibrarian
@testable import DiscairUI

/// The Paths sheet's Trail rules (docs/MACOS_PATHS_BOOKLET.md, section 4.2): links, groups, role lines, the filter and the order.
@Suite @MainActor struct PathTrailTests {
    // MARK: Builders

    private func entity(_ name: String, _ type: String, owned: Bool = false) -> String {
        #"{"mbid":"\#(name)-id","canonical_name":"\#(name)","type":"\#(type)","owned":\#(owned)}"#
    }

    /// One reason. `evidence` is the relation of its first credit, when it has one.
    private func reason(_ code: String, via: (String, String)? = nil, anchor: (String, String)? = nil, relation: String? = nil) -> String {
        var parts = [#""code":"\#(code)","text":"why""#]
        if let via { parts.append(#""via":\#(entity(via.0, via.1))"#) }
        if let anchor { parts.append(#""anchor":\#(entity(anchor.0, anchor.1))"#) }
        if let relation { parts.append(#""evidence":[{"relation":"\#(relation)","evidence_class":"source_explicit","match_quality":"exact_mbid","source":"musicbrainz_dump"}]"#) }
        return "{" + parts.joined(separator: ",") + "}"
    }

    private func stop(_ name: String, owned: Bool = false, type: String = "release", reasons: [String]) -> String {
        #"{"entity":\#(entity(name, type, owned: owned)),"presentation":{"album_artist":"Someone"},"reasons":[\#(reasons.joined(separator: ","))]}"#
    }

    private func decode(_ stops: [String], kind: String = "album_crew", type: String = "release", extra: String = "") throws -> KnowledgePaths {
        let json = #"{"kind":"\#(kind)","status":"ok","start":\#(entity("Round About Midnight", type, owned: true)),\#(extra)"stops":[\#(stops.joined(separator: ","))]}"#
        return try JSONDecoder().decode(KnowledgePaths.self, from: Data(json.utf8))
    }

    private func album(_ stops: [String], kind: String = "album_crew", extra: String = "") throws -> PathAnswer {
        PathAnswer(album: try decode(stops, kind: kind, extra: extra))
    }

    private func artist(_ stops: [String], kind: PathKind) throws -> PathAnswer {
        PathAnswer(artist: try decode(stops, kind: kind.rawValue, type: "artist"), kind: kind)
    }

    private func text(_ spans: [StorySpan]) -> String { spans.map(\.text).joined() }

    // MARK: Links

    @Test func albumLinksFollowTheTabAndTheFirstReason() throws {
        func kind(_ code: String, _ tab: AlbumPathTab, via: String? = "V", relation: String? = nil) throws -> PathLink? {
            let a = try album([stop("S", reasons: [reason(code, via: via.map { ($0, "artist") }, relation: relation)])])
            return PathTrail.link(album: a.steps[0], tab: tab)
        }
        #expect(try kind("crew_on", .studioCrew, relation: "producer") == PathLink(name: "V", kind: "producer credit"))
        #expect(try kind("crew_on", .studioCrew, relation: "engineer")?.kind == "engineer credit")
        #expect(try kind("crew_on", .studioCrew, relation: "mix")?.kind == "mixing credit")
        #expect(try kind("crew_on", .studioCrew, relation: "mastering")?.kind == "mastering credit")
        #expect(try kind("crew_on", .studioCrew)?.kind == "production credit")
        #expect(try kind("guest_on", .guestList)?.kind == "guest credit")
        #expect(try kind("same_work", .coversAndSources)?.kind == "same work")
        #expect(try kind("derived_work", .coversAndSources)?.kind == "related work")
        #expect(try kind("related_work", .coversAndSources)?.kind == "related work")
        #expect(try kind("same_period_label", .sameYearSameScene)?.kind == "same label")
        #expect(try kind("same_period_area", .sameYearSameScene)?.kind == "same area")
        #expect(try kind("same_period_credit", .sameYearSameScene)?.kind == "shared artist")
        #expect(try kind("recorded_at", .sameRoom)?.kind == "recorded at")
        #expect(try kind("crew_on", .listenThroughGaps)?.kind == "production credit")
        #expect(try kind("guest_on", .listenThroughGaps)?.kind == "guest credit")
        #expect(try kind("sonic_neighbour", .neighboursByEar) == nil)
    }

    @Test func aStepWhoseFirstReasonHasNoViaIsNamedByItsKindAlone() throws {
        let a = try album([stop("S", reasons: [reason("crew_on", relation: "producer")])])
        #expect(PathTrail.link(album: a.steps[0], tab: .studioCrew) == PathLink(name: "", kind: "producer credit"))
        let groups = PathTrail.groups(a, context: .album(.studioCrew), start: "Round About Midnight")
        #expect(groups.count == 1 && groups[0].id == "producer credit|" && groups[0].link?.name == "")
    }

    @Test func theLinkComesFromTheFirstReasonOnly() throws {
        let a = try album([stop("S", reasons: [reason("crew_on", via: ("First", "artist"), relation: "mix"), reason("crew_on", via: ("Second", "artist"), relation: "producer")])])
        #expect(PathTrail.link(album: a.steps[0], tab: .studioCrew) == PathLink(name: "First", kind: "mixing credit"))
    }

    @Test func artistLinksFollowTheKind() throws {
        func link(_ kind: PathKind, code: String, via: (String, String)?) throws -> PathLink? {
            let a = try artist([stop("S", type: "recording", reasons: [reason(code, via: via)])], kind: kind)
            return PathTrail.link(artist: a.steps[0], kind: kind)
        }
        #expect(try link(.followTheMusician, code: "shared_musician", via: ("Coltrane", "artist")) == PathLink(name: "Coltrane", kind: "musician"))
        #expect(try link(.followTheMusician, code: "shared_musician", via: ("Coltrane", "person"))?.name == "Coltrane")
        #expect(try link(.followTheMusician, code: "shared_musician", via: ("Somewhere", "place")) == PathLink(name: "", kind: "musician"))
        #expect(try link(.sidemanToLeader, code: "sideman_on", via: ("Bags' Groove", "release")) == PathLink(name: "Bags' Groove", kind: "a record they led"))
        #expect(try link(.sidemanToLeader, code: "sideman_on", via: ("A Person", "artist")) == PathLink(name: "", kind: "a record they led"))
        #expect(try link(.labelPath, code: "same_label", via: ("Columbia", "label")) == PathLink(name: "Columbia", kind: "same label"))
        #expect(try link(.compositionPath, code: "same_work", via: ("Naima", "work")) == PathLink(name: "Naima", kind: "same work"))
        #expect(try link(.compositionPath, code: "derived_work", via: ("Naima", "work"))?.kind == "related work")
        #expect(try link(.scenePath, code: "same_period_area", via: ("New York", "place")) == PathLink(name: "New York", kind: "same place"))
    }

    @Test func aFollowTheMusicianStepKeepsItsLinkAfterTheDedupe() throws {
        let p = try decode([
            stop("Giant Steps", type: "recording", reasons: [reason("shared_musician", via: ("John Coltrane", "artist"), anchor: ("Round Midnight", "recording"), relation: "instrument")]),
            stop("Giant Steps", type: "recording", reasons: [reason("shared_musician", via: ("Red Garland", "artist"))]),
            stop("Naima", type: "recording", reasons: [reason("shared_musician", via: ("John Coltrane", "artist"), anchor: ("Round Midnight", "recording"), relation: "instrument")]),
        ], kind: "follow_the_musician", type: "artist")
        let a = PathAnswer(artist: p, kind: .followTheMusician)
        #expect(a.steps.map(\.name) == ["Giant Steps", "Naima"])   // the second Giant Steps is a repeat
        #expect(a.steps.map(\.id) == [0, 1])                        // renumbered, as before
        for s in a.steps {
            #expect(PathTrail.link(artist: s, kind: .followTheMusician) == PathLink(name: "John Coltrane", kind: "musician"))
            #expect(s.firstCode == "shared_musician" && s.creditRole == "instrument" && s.anchors.map(\.name) == ["Round Midnight"])
        }
        #expect(a.steps[1].with(id: 7).id == 7 && a.steps[1].with(id: 7).firstVia == a.steps[1].firstVia)
    }

    @Test func withIDChangesOnlyTheID() throws {
        let a = try album([stop("S", reasons: [reason("crew_on", via: ("V", "artist"), anchor: ("Round About Midnight", "release"), relation: "producer")])])
        let s = a.steps[0]
        var expected = s
        let moved = s.with(id: 5)
        #expect(moved.id == 5 && moved.story == s.story && !s.story.isEmpty)
        expected = moved.with(id: s.id)
        #expect(expected == s)
    }

    // MARK: Groups

    @Test func groupsAppearByFirstStepAndStepsKeepServerOrderInsideThem() throws {
        func crew(_ name: String, _ who: String) -> String { stop(name, reasons: [reason("crew_on", via: (who, "artist"), relation: "producer")]) }
        let a = try album([crew("A", "Ann"), crew("B", "Bo"), crew("C", "Ann"), crew("D", "ann"), crew("E", "Bo")])
        let g = PathTrail.groups(a, context: .album(.studioCrew), start: "Round About Midnight")
        #expect(g.map { $0.link?.name } == ["Ann", "Bo"])
        #expect(g.map(\.stepIDs) == [[0, 2, 3], [1, 4]])          // "ann" folds to the same group; C and D move up to join A
        #expect(PathTrail.order(g) == [0, 2, 3, 1, 4])
    }

    @Test func sameNameWithAnotherKindIsAnotherGroup() throws {
        let a = try album([
            stop("A", reasons: [reason("same_work", via: ("Naima", "work"))]),
            stop("B", reasons: [reason("derived_work", via: ("Naima", "work"))]),
        ], kind: "album_works")
        let g = PathTrail.groups(a, context: .album(.coversAndSources), start: "X")
        #expect(g.map { $0.link?.kind } == ["same work", "related work"])
    }

    @Test func sonicIsOneFlatGroupWithNoLinkAndNoFilter() throws {
        let a = PathAnswer(steps: (0..<3).map { i in
            PathStep(id: i, name: "S\(i)", detail: "", why: "", year: nil, cover: nil, symbol: "opticaldisc", reasons: [], evidence: nil,
                     target: nil, artistName: nil, owned: i == 0)
        }, notes: [])
        let g = PathTrail.groups(a, context: .album(.neighboursByEar), start: "X")
        #expect(g.count == 1 && g[0].link == nil && g[0].role.isEmpty && g[0].stepIDs == [0, 1, 2])
        #expect(!PathTrail.offersFilter(a, groups: g))
    }

    // MARK: Role lines

    @Test func roleLineWordsComeFromTheAnchors() throws {
        let start = "Round About Midnight"
        func role(_ tab: AlbumPathTab, _ anchors: [(String, String)], code: String = "crew_on") throws -> String {
            let a = try album([stop("S", reasons: anchors.map { reason(code, via: ("V", "artist"), anchor: $0, relation: "producer") })])
            return text(PathTrail.groups(a, context: .album(tab), start: start)[0].role)
        }
        #expect(try role(.studioCrew, [(start, "release")]) == "On the album itself")
        #expect(try role(.studioCrew, [("Whatever", "release")]) == "On the album itself")
        #expect(try role(.studioCrew, [("Round Midnight", "recording")]) == "On Round Midnight")
        #expect(try role(.studioCrew, [("Round Midnight", "recording"), ("Ah-Leu-Cha", "recording")]) == "On Round Midnight and Ah-Leu-Cha")
        #expect(try role(.studioCrew, ["Round Midnight", "Ah-Leu-Cha", "All of You", "Two Bass Hit", "Round Midnight"].map { ($0, "recording") })
                == "On Round Midnight, Ah-Leu-Cha and 2 more")
        #expect(try role(.listenThroughGaps, [("Ah-Leu-Cha", "recording")], code: "crew_on") == "On Ah-Leu-Cha")
        #expect(try role(.coversAndSources, [("Round Midnight", "recording")], code: "same_work") == "Behind Round Midnight")
        #expect(try role(.studioCrew, []) == "")
        // Nothing is invented for the tabs with no anchors to read.
        #expect(try role(.guestList, [("Round Midnight", "recording")], code: "guest_on") == "")
        #expect(try role(.sameRoom, [("Round Midnight", "recording")], code: "recorded_at") == "")
        #expect(try role(.sameYearSameScene, [("Round Midnight", "recording")], code: "same_period_label") == "")
    }

    @Test func roleLineIgnoresAnchorsOfOtherLinksOnTheSameStep() throws {
        let a = try album([stop("S", reasons: [
            reason("crew_on", via: ("Ann", "artist"), anchor: ("Round Midnight", "recording"), relation: "producer"),
            reason("crew_on", via: ("Bo", "artist"), anchor: ("Round About Midnight", "release"), relation: "mix"),
            reason("crew_on", via: ("Ann", "artist"), anchor: ("Ah-Leu-Cha", "recording"), relation: "producer")])])
        #expect(a.steps[0].anchors.map(\.name) == ["Round Midnight", "Ah-Leu-Cha"])
        #expect(text(PathTrail.groups(a, context: .album(.studioCrew), start: "Round About Midnight")[0].role) == "On Round Midnight and Ah-Leu-Cha")
    }

    @Test func roleLineTitlesAreItalicAndTheRestIsPlain() throws {
        let a = try album([stop("S", reasons: [reason("crew_on", via: ("V", "artist"), anchor: ("Round Midnight", "recording"), relation: "producer")])])
        let spans = PathTrail.groups(a, context: .album(.studioCrew), start: "X")[0].role
        #expect(spans.map(\.kind) == [.plain, .title])
    }

    @Test func artistRoleLinesUseTheSheetsArtist() throws {
        let f = try artist([stop("S", type: "recording", reasons: [reason("shared_musician", via: ("Coltrane", "artist"))])], kind: .followTheMusician)
        #expect(text(PathTrail.groups(f, context: .artist(.followTheMusician), start: "Miles Davis")[0].role) == "Played with Miles Davis")
        let s = try artist([stop("S", type: "artist", reasons: [reason("sideman_on", via: ("Somethin' Else", "release"))])], kind: .sidemanToLeader)
        #expect(text(PathTrail.groups(s, context: .artist(.sidemanToLeader), start: "Miles Davis")[0].role) == "Miles Davis played on it")
        for kind in [PathKind.labelPath, .compositionPath, .scenePath] {
            let a = try artist([stop("S", reasons: [reason("same_label", via: ("V", "label"))])], kind: kind)
            #expect(PathTrail.groups(a, context: .artist(kind), start: "Miles Davis")[0].role.isEmpty)
        }
    }

    @Test func countWords() {
        #expect(PathTrail.countText(shown: 4, of: 4, context: .album(.studioCrew)) == "4 albums")
        #expect(PathTrail.countText(shown: 1, of: 1, context: .album(.studioCrew)) == "1 album")
        #expect(PathTrail.countText(shown: 2, of: 4, context: .album(.studioCrew)) == "2 of 4 albums")
        #expect(PathTrail.countText(shown: 3, of: 3, context: .artist(.followTheMusician)) == "3 songs")
        #expect(PathTrail.countText(shown: 2, of: 2, context: .artist(.sidemanToLeader)) == "2 artists")
        #expect(PathTrail.countText(shown: 2, of: 2, context: .artist(.scenePath)) == "2 artists")
        #expect(PathTrail.countText(shown: 1, of: 1, context: .artist(.compositionPath)) == "1 recording")
    }

    // MARK: Capped notes

    @Test func cappedGoesUnderItsGroupAndElseToTheLooseNotes() throws {
        let a = try album([stop("A", reasons: [reason("crew_on", via: ("George Avakian", "artist"), relation: "producer")])],
                          extra: #""capped":[{"via":"george avakian","more":4},{"via":"Nobody Here","more":2}],"truncated":"rows","#)
        let g = PathTrail.groups(a, context: .album(.studioCrew), start: "X")
        #expect(g[0].cappedMore == 4)
        #expect(PathTrail.cappedText(g[0]) == "4 more albums with George Avakian are not shown.")
        #expect(PathTrail.looseNotes(a, groups: g) == ["The server stopped this path early (row limit), so later steps may be missing.",
                                                      "2 more albums with Nobody Here are not shown."])
        #expect(a.notes == ["The server stopped this path early (row limit), so later steps may be missing."])
    }

    @Test func cappedNeverMatchesAGroupWithNoName() throws {
        let a = try album([stop("A", reasons: [reason("crew_on", relation: "producer")])], extra: #""capped":[{"via":"X","more":3}],"#)
        let g = PathTrail.groups(a, context: .album(.studioCrew), start: "S")
        #expect(g[0].cappedMore == nil && PathTrail.looseNotes(a, groups: g) == ["3 more albums with X are not shown."])
    }

    // MARK: Filter

    private func filtered() throws -> (PathAnswer, [PathTrailGroup]) {
        func crew(_ name: String, _ who: String, owned: Bool) -> String { stop(name, owned: owned, reasons: [reason("crew_on", via: (who, "artist"), relation: "producer")]) }
        let a = try album([crew("A", "Ann", owned: true), crew("B", "Bo", owned: false), crew("C", "Ann", owned: false), crew("D", "Cy", owned: true)])
        return (a, PathTrail.groups(a, context: .album(.studioCrew), start: "X"))
    }

    @Test func theFilterKeepsStepsAndDropsEmptyGroups() throws {
        let (a, g) = try filtered()
        #expect(PathTrail.offersFilter(a, groups: g))
        #expect(PathTrail.order(PathTrail.visible(g, steps: a.steps, filter: .all)) == [0, 2, 1, 3])
        let not = PathTrail.visible(g, steps: a.steps, filter: .notOwned)
        #expect(not.map(\.stepIDs) == [[2], [1]] && PathTrail.order(not) == [2, 1])
        let own = PathTrail.visible(g, steps: a.steps, filter: .owned)
        #expect(own.map { $0.link?.name } == ["Ann", "Cy"])          // Bo has no owned step, so its group is not drawn
        #expect(own.map(\.stepIDs) == [[0], [3]])
    }

    @Test func theFilterIsOfferedOnlyWhenTheAnswerHoldsBothKinds() throws {
        let allOwned = try album([stop("A", owned: true, reasons: [reason("crew_on", via: ("Ann", "artist"))])])
        #expect(!PathTrail.offersFilter(allOwned, groups: PathTrail.groups(allOwned, context: .album(.studioCrew), start: "X")))
        let none = try album([stop("A", owned: false, reasons: [reason("crew_on", via: ("Ann", "artist"))])])
        #expect(!PathTrail.offersFilter(none, groups: PathTrail.groups(none, context: .album(.studioCrew), start: "X")))
    }

    @Test func aDroppedGroupTakesItsCappedNoteWithIt() throws {
        let a = try album([stop("A", owned: true, reasons: [reason("crew_on", via: ("Ann", "artist"))]), stop("B", owned: false, reasons: [reason("crew_on", via: ("Bo", "artist"))])],
                          extra: #""capped":[{"via":"Bo","more":2}],"#)
        let g = PathTrail.groups(a, context: .album(.studioCrew), start: "X")
        let v = PathTrail.visible(g, steps: a.steps, filter: .owned)
        #expect(v.map { $0.link?.name } == ["Ann"])
        // The loose notes read the unfiltered groups, so a hidden group's note is not moved to the bottom.
        #expect(PathTrail.looseNotes(a, groups: g).isEmpty)
    }

    // MARK: Sheet model: order, selection, filter

    private func sheet(_ a: PathAnswer, tab: AlbumPathTab = .studioCrew) -> PathsSheetModel {
        let m = PathsSheetModel(albumTitle: "X", artist: "Y", albumID: "1", year: 1957, sonicAvailable: true)
        m.choose(tab.rawValue)
        m.receive(a, for: tab.rawValue)
        return m
    }

    @Test func moveWalksTheVisualOrderAndStopsAtTheEnds() throws {
        let (a, _) = try filtered()
        let m = sheet(a)
        #expect(m.order == [0, 2, 1, 3] && m.selected == 0)       // the first step in visual order is selected
        m.move(by: 1); #expect(m.selected == 2)
        m.move(by: 1); #expect(m.selected == 1)
        m.move(by: 1); m.move(by: 1); #expect(m.selected == 3)
        m.move(by: -1); #expect(m.selected == 1)
        m.selected = 0; m.move(by: -1); #expect(m.selected == 0)
    }

    @Test func theFirstMoveFromNothingGoesToAnEnd() throws {
        let (a, _) = try filtered()
        let m = sheet(a)
        m.selected = nil; m.move(by: 1); #expect(m.selected == 0)
        m.selected = nil; m.move(by: -1); #expect(m.selected == 3)
    }

    @Test func aFilterThatHidesTheSelectionSelectsTheFirstVisibleStep() throws {
        let (a, _) = try filtered()
        let m = sheet(a)
        #expect(m.filter == .all && m.offersFilter)
        m.selected = 0                          // Ann's owned album
        m.setFilter(.notOwned)
        #expect(m.order == [2, 1] && m.selected == 2)
        m.selected = 1
        m.setFilter(.all)                       // a visible selection stays
        #expect(m.selected == 1)
        m.setFilter(.owned)
        #expect(m.order == [0, 3] && m.selected == 0)
    }

    @Test func theFilterDoesNotApplyWhereItIsNotOffered() throws {
        let a = try album([stop("A", owned: true, reasons: [reason("crew_on", via: ("Ann", "artist"))])])
        let m = sheet(a)
        m.setFilter(.notOwned)
        #expect(!m.offersFilter && m.activeFilter == .all && m.order == [0])
    }

    @Test func aSheetStartsAtAllAndKeepsTheTabCountsOfLoadedTabs() throws {
        let (a, _) = try filtered()
        let m = sheet(a)
        #expect(m.filter == .all)
        #expect(m.count(for: "studioCrew") == 4 && m.count(for: "guestList") == nil)
    }

    @Test func choosingALoadedTabSelectsItsFirstStep() throws {
        let (a, _) = try filtered()
        let m = sheet(a)
        m.choose("guestList"); #expect(m.selected == nil)          // not read yet
        m.choose("studioCrew"); #expect(m.selected == 0)
    }

    @Test func theSheetsLooseNotesAndGroupsComeFromTheChosenTab() throws {
        let a = try album([stop("A", reasons: [reason("crew_on", via: ("Ann", "artist"), relation: "producer")])],
                          extra: #""capped":[{"via":"Ann","more":3},{"via":"Zed","more":1}],"#)
        let m = sheet(a)
        #expect(m.groups.count == 1 && m.groups[0].cappedMore == 3)
        #expect(m.looseNotes == ["1 more album with Zed is not shown."])
    }
}
