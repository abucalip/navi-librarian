import Foundation
import Testing
import DiscairLibrarian
@testable import DiscairUI

private func item(_ id: String, _ kind: String, _ date: String?, owned: Bool = false) -> TimelineItem {
    let d = date.map { #""\#($0)""# } ?? "null"
    let json = #"{"kind":"\#(kind)","entity":{"mbid":"\#(id)","canonical_name":"T \#(id)","type":"release_group"},"owned":\#(owned),"date":\#(d),"why":"credited as trumpet","evidence":[{"source":"musicbrainz_dump","evidence_class":"source_explicit","match_quality":"exact_mbid"}]}"#
    return try! JSONDecoder().decode(TimelineItem.self, from: Data(json.utf8))
}

@Suite("Timeline grouping") struct TimelineGroupingTests {
    @Test func yearAndDecadeBandsKeepServerOrder() {
        let items = [item("a", "album", "1966-03-02"), item("b", "event", "1966"), item("c", "album", "1974-05"), item("d", "album", "1979")]
        #expect(TimelineGrouping.groups(items, byDecade: false).map(\.label) == ["1966", "1974", "1979"])
        let decades = TimelineGrouping.groups(items, byDecade: true)
        #expect(decades.map(\.label) == ["1960s", "1970s"] && decades[0].items.count == 2 && decades[1].items.count == 2)
    }

    @Test func anUndatedItemIsNeverPlaced() {
        let items = [item("a", "album", nil), item("b", "album", "abc"), item("c", "album", "1972")]
        #expect(items[0].year == nil && items[1].year == nil && items[2].year == 1972)
        #expect(TimelineGrouping.groups(items, byDecade: false).flatMap(\.items).map(\.entity.mbid) == ["c"])
    }

    @Test func dateTextIsNeverPadded() {
        #expect(TimelineGrouping.display("1972") == "1972")
        #expect(TimelineGrouping.display("1972-06") == "June 1972")
        #expect(TimelineGrouping.display("1972-06-02") == "2 June 1972")
        #expect(TimelineGrouping.display(nil) == "No stated date")
    }
}

@MainActor @Suite("Timeline model") struct TimelineModelTests {
    @Test func decodesThePageAndSplitsDatedFromUndated() throws {
        let body = #"{"person":{"mbid":"a1","canonical_name":"Mulatu","type":"artist"},"items":[{"kind":"album","entity":{"mbid":"g1","canonical_name":"LP","type":"release_group"},"owned":true,"date":"1972"},{"kind":"event","entity":{"mbid":"v1","canonical_name":"Gig","type":"event"},"date":null,"cancelled":true,"event_kind":"concert"}],"undated":1,"truncated":false,"not_loaded":["recording_dates"],"sources":{"musicbrainz_dump":{"coverage":"loaded"}}}"#
        let page = try JSONDecoder().decode(KnowledgeTimeline.self, from: Data(body.utf8))
        let model = TimelineModel()
        model.preview(person: page.person, items: page.items, undated: page.undated)
        #expect(model.dated.count == 1 && model.undated.count == 1 && model.undated[0].cancelled && model.undatedCount == 1)
        #expect(model.groups.map(\.label) == ["1972"] && page.notLoaded == ["recording_dates"])
        model.selectedID = "album:g1"
        #expect(model.selected?.owned == true)
    }

    @Test func withoutALibraryItSaysSo() async {
        let model = TimelineModel()
        await model.start(artistRemoteID: nil, name: "X", navidrome: nil, librarian: nil)
        #expect(model.items.isEmpty && model.note != nil)
    }
}
