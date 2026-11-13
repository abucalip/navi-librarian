import Testing
import Foundation
@testable import DiscairLibrarian

/// The radio decoders (S2-1 item 1), against the Android contract fixtures. The client calls arrive in the next piece.
@Suite("Radio decoders") struct RadioDecoderTests {
    func decode<T: Decodable>(_ type: T.Type, _ json: String) throws -> T { try JSONDecoder().decode(type, from: Data(json.utf8)) }
    func fixture<T: Decodable>(_ type: T.Type, _ name: String) throws -> T { try JSONDecoder().decode(type, from: fixtureBody(name)) }

    @Test func stationsFixtureKeepsServerOrderAndFields() throws {
        let list = try fixture(RadioStationsPayload.self, "radio_stations").items
        #expect(list.map(\.id) == ["11", "12", "13"])
        #expect(list[0].name == "Example Rock FM" && list[0].proxied && list[0].favourite)
        #expect(list[0].tags == ["rock", "local"] && list[0].lastPlayedAt == nil)
        #expect(list[0].playableURL == "https://librarian.example.invalid/radio/stream/fixturetoken")
        #expect(list[0].homepageURL == "http://rock.example.invalid/" && list[0].logoPath == "/api/radio/stations/11/logo")
        #expect(!list[1].proxied && !list[1].favourite && list[1].tags.isEmpty && list[1].homepageURL == nil)
        #expect(list[1].lastPlayedAt == 1_700_000_000)
    }

    @Test func emptyStationsFixtureIsEmpty() throws {
        #expect(try fixture(RadioStationsPayload.self, "radio_stations_empty").items.isEmpty)
    }

    @Test func oneUnreadableRowDoesNotHideTheRest() throws {
        let body = #"{"items":[{"id":"1","name":"A","playable_url":"http://a.example.invalid/s"},{"id":"2","name":"no address"},{"name":"no id","playable_url":"http://x.example.invalid/"},{"id":"3","name":"C","playable_url":"http://c.example.invalid/s","tags":["x",5,"y"],"favourite":"yes"}]}"#
        let list = try decode(RadioStationsPayload.self, body).items
        #expect(list.map(\.id) == ["1", "3"])
        #expect(list[0].logoPath == "/api/radio/stations/1/logo")   // generated path when the server sent none
        #expect(list[1].tags == ["x", "y"] && !list[1].favourite)
        #expect(try decode(RadioStationsPayload.self, "{}").items.isEmpty)
    }

    @Test func stationDescriptionNeverContainsTheAddress() throws {
        for s in try fixture(RadioStationsPayload.self, "radio_stations").items {
            for text in ["\(s)", String(describing: s), String(reflecting: s), { var o = ""; dump(s, to: &o); return o }()] {
                #expect(!text.contains("example.invalid") && !text.contains("fixturetoken"))
                #expect(text.contains(s.name))
            }
        }
    }

    @Test func nowFixturesDecodeEveryState() throws {
        let ok = try fixture(RadioNow.self, "radio_now_ok")
        #expect(ok.state == .ok && ok.artist == "Pink Floyd" && ok.title == "Time" && ok.rawTitle == "Pink Floyd - Time")
        #expect(ok.playID == 1 && ok.inLibrary && ok.coverPath == "/api/owned/artwork/al-42" && ok.canDownload)

        let waiting = try fixture(RadioNow.self, "radio_now_ok_waiting")
        #expect(waiting.state == .ok && waiting.playID == nil && !waiting.inLibrary && waiting.coverPath == nil && !waiting.canDownload)

        let unparsed = try fixture(RadioNow.self, "radio_now_unparsed")
        #expect(unparsed.state == .unparsed && unparsed.rawTitle == "Station jingle" && unparsed.artist == nil && !unparsed.canDownload)

        for (name, state) in [("radio_now_no_metadata", RadioNowState.noMetadata), ("radio_now_not_proxied", .notProxied),
                              ("radio_now_unavailable", .unavailable), ("radio_now_idle", .idle)] {
            let now = try fixture(RadioNow.self, name)
            #expect(now.state == state && now.rawTitle == nil && now.playID == nil && !now.canDownload)
        }
    }

    @Test func unknownStateDecodesAsUnknownAndNeverEnablesDownload() throws {
        let now = try decode(RadioNow.self, #"{"state":"buffering_soon","raw_title":"A - B","artist":"A","title":"B","play_id":9,"in_library":false}"#)
        #expect(now.state == .unknown && !now.canDownload)
        #expect(try decode(RadioNow.self, "{}").state == .unknown)
    }

    @Test func nowReadsLooseValuesWithoutFailing() throws {
        let now = try decode(RadioNow.self, #"{"state":"ok","artist":"  ","title":"T","play_id":4.0,"in_library":"no","cover_url":""}"#)
        #expect(now.artist == nil && now.title == "T" && now.playID == 4 && !now.inLibrary && now.coverPath == nil)
    }

    @Test func nowAllIsKeyedByStationIDAndDropsRowsWithoutOne() throws {
        let all = try fixture(RadioNowAll.self, "radio_now_all")
        #expect(Set(all.byStation.keys) == ["11", "12"])
        #expect(all.byStation["11"]?.state == .ok && all.byStation["11"]?.playID == 1 && all.byStation["12"]?.state == .idle)
        let partial = try decode(RadioNowAll.self, #"{"items":[{"state":"ok","title":"x"},{"id":"5","state":"unparsed","raw_title":"jingle"},7]}"#)
        #expect(Array(partial.byStation.keys) == ["5"] && partial.byStation["5"]?.state == .unparsed)
        #expect(try decode(RadioNowAll.self, "{}").byStation.isEmpty)
    }

    @Test func scrobblingReadsOffAndNotSetUpWhenUnreadable() throws {
        #expect(try decode(RadioScrobbling.self, #"{"enabled":true,"configured":true}"#) == RadioScrobbling(enabled: true, configured: true))
        #expect(try decode(RadioScrobbling.self, #"{"enabled":true}"#) == RadioScrobbling(enabled: true, configured: false))
        #expect(try decode(RadioScrobbling.self, "{}") == RadioScrobbling(enabled: false, configured: false))
    }
}
