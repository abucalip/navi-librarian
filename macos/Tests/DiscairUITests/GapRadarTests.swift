import Foundation
import Testing
@testable import DiscairUI

@MainActor
struct GapRadarTests {
    private func album(_ title: String, _ artist: String, _ year: Int, owned: Bool) -> AlbumItem {
        AlbumItem(id: abs((title + artist).hashValue % 10_000), title: title, artist: artist, year: year, genre: "", format: "", owned: owned, hue: 0)
    }

    @Test func onlyArtistsWithAnOwnedAlbumAndAGapAreListed() {
        let owned = [album("A1", "Alpha", 1990, owned: true), album("B1", "Beta", 2000, owned: true)]
        let missing = [album("A2", "Alpha", 0, owned: false), album("Z1", "Stranger", 0, owned: false)]
        let list = GapRadar.build(owned: owned, missing: missing)
        #expect(list.map(\.name) == ["Alpha"])          // Beta has no gap, Stranger is not in the library
    }

    @Test func aPickTheLibraryAlreadyHoldsIsNotAGap() {
        let owned = [album("Same", "Alpha", 1990, owned: true)]
        let list = GapRadar.build(owned: owned, missing: [album("SAME", "alpha", 0, owned: false)])
        #expect(list.isEmpty)
    }

    @Test func biggestGapComesFirstAndMatchingIgnoresCase() {
        let owned = [album("A1", "Alpha", 1990, owned: true), album("B1", "Beta", 2000, owned: true), album("B0", "BETA", 1999, owned: true)]
        let missing = [album("A2", "alpha", 0, owned: false), album("B2", "Beta", 0, owned: false), album("B3", "Beta", 0, owned: false)]
        let list = GapRadar.build(owned: owned, missing: missing)
        #expect(list.map(\.name) == ["Beta", "Alpha"])
        #expect(list[0].owned.count == 2 && list[0].missing.count == 2)
        #expect(list[1].completeness == 0.5)
    }

    @Test func albumsSortByYearWithUnknownYearsLast() {
        let owned = [album("Late", "A", 2010, owned: true), album("Early", "A", 1980, owned: true), album("None", "A", 0, owned: true)]
        let g = GapRadar.build(owned: owned, missing: [album("Gap", "A", 1995, owned: false), album("NoYear", "A", 0, owned: false)])[0]
        #expect(g.owned.map(\.title) == ["Early", "Late", "None"])
        #expect(g.dated.map(\.title) == ["Early", "Gap", "Late"])
        #expect(g.undatedMissing.map(\.title) == ["NoYear"])
        #expect(g.yearSpan == 1980...2010)
    }

    @Test func axisPositionIsProportionalAndASingleYearSitsInTheMiddle() {
        #expect(GapRadar.position(of: 1990, in: 1980...2000) == 0.5)
        #expect(GapRadar.position(of: 1980, in: 1980...2000) == 0)
        #expect(GapRadar.position(of: 1985, in: 1985...1985) == 0.5)
    }

    @Test func sampleRadarShowsTalkTalkWithTwoMissing() {
        let g = LibraryModel.sampleGap
        #expect(g.count == 1 && g[0].name == "Talk Talk" && g[0].missing.count == 2 && g[0].owned.count == 3)
    }
}
