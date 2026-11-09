import Foundation
import Testing
import DiscairLibrarian
@testable import DiscairUI

@MainActor @Suite("Taste model") struct TasteModelTests {
    private func load(_ model: TasteModel, _ json: String) throws {
        let r = try JSONDecoder().decode(TasteResponse.self, from: Data(json.utf8))
        model.set(r.profiles)
    }

    private func window(_ listens: Int, low: Bool, era: Bool = false) -> String {
        #"{"listens":\#(listens),"low_sample":\#(low),"attributed":{"genre":\#(listens),"era":\#(listens)},"dimension_low_sample":{"genre":false,"era":\#(era)},"dimensions":{"genre":[{"value":"jazz","count":3,"share":0.6}],"era":[{"value":"1980s","count":3,"share":0.6},{"value":"1990s","count":2,"share":0.4}]}}"#
    }

    @Test func noProfilesMeansNothingToShow() {
        let m = TasteModel()
        #expect(m.profiles == nil && m.selectedWindow == nil && m.decades == nil && m.shifts.isEmpty)
    }

    @Test func decadesNeedBothWindowsSound() throws {
        let m = TasteModel()
        try load(m, #"{"profiles":{"windows":{"recent":\#(window(60, low: false)),"all_time":\#(window(900, low: false, era: true))},"shifts":[]}}"#)
        #expect(m.decades == nil)
        try load(m, #"{"profiles":{"windows":{"recent":\#(window(60, low: false)),"all_time":\#(window(900, low: false))},"shifts":[]}}"#)
        #expect(m.decades?.map(\.label) == ["1980s", "1990s"])
    }

    @Test func shiftsAreOnlyTheOnesTheServerListedForTheHeadlineWindow() throws {
        let m = TasteModel()
        let shift = { (w: String, v: String, f: Double, t: Double) in
            #"{"window":"\#(w)","dimension":"genre","value":"\#(v)","direction":"up","from_share":\#(f),"to_share":\#(t)}"#
        }
        try load(m, #"{"profiles":{"headline":{"text":"x","kind":"up","window":"mid","subjects":[]},"windows":{},"shifts":[\#(shift("recent", "a", 0.1, 0.2)),\#(shift("mid", "b", 0.1, 0.3)),\#(shift("mid", "c", 0.1, 0.5))]}}"#)
        #expect(m.shifts.map(\.value) == ["c", "b"])   // mid only, biggest move first
    }
}
