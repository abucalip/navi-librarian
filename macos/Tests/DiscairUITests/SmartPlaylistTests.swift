import Foundation
import Testing
@testable import DiscairUI

@MainActor
struct SmartPlaylistTests {
    private let now = Date(timeIntervalSince1970: 1_800_000_000)
    private func song(_ id: Int, _ title: String, artist: String = "Alpha", genre: String = "Rock", year: Int = 1990, plays: Int = 0,
                      rating: Int = 0, kbps: Int = 0, addedDaysAgo: Int? = nil, playedDaysAgo: Int? = nil, remote: Bool = true) -> SongRow {
        var s = SongRow(id: id, album: 0, title: title, artist: artist, genre: genre, format: "", bitrate: "", lastPlayed: "", added: "", year: year, plays: plays)
        s.remoteID = remote ? "s\(id)" : nil
        s.rating = rating; s.bitrateKbps = kbps
        s.addedAt = addedDaysAgo.map { now.addingTimeInterval(-Double($0) * 86_400) }
        s.playedAt = playedDaysAgo.map { now.addingTimeInterval(-Double($0) * 86_400) }
        return s
    }
    private func run(_ rules: [SmartRule], all: Bool = true, over songs: [SongRow], order: SmartOrder = .title, limit: Int = 0) -> [String] {
        SmartEngine.run(SmartPlaylist(name: "t", matchAll: all, rules: rules, order: order, limit: limit), over: songs, now: now).map(\.title)
    }

    @Test func textRulesIgnoreCaseAndAccents() {
        let songs = [song(1, "Café", genre: "Jazz"), song(2, "Rock song", genre: "Rock")]
        #expect(run([SmartRule(field: .genre, op: .contains, value: "JAZ")], over: songs) == ["Café"])
        #expect(run([SmartRule(field: .title, op: .contains, value: "cafe")], over: songs) == ["Café"])
        #expect(run([SmartRule(field: .genre, op: .notContains, value: "jazz")], over: songs) == ["Rock song"])
        #expect(run([SmartRule(field: .genre, op: .equals, value: "rock")], over: songs) == ["Rock song"])
    }

    @Test func allAndAnyCombineRules() {
        let songs = [song(1, "A", plays: 5, rating: 5), song(2, "B", plays: 5, rating: 1), song(3, "C", plays: 0, rating: 5)]
        let rules = [SmartRule(field: .plays, op: .atLeast, value: "3"), SmartRule(field: .rating, op: .atLeast, value: "4")]
        #expect(run(rules, over: songs) == ["A"])
        #expect(run(rules, all: false, over: songs) == ["A", "B", "C"])
    }

    @Test func numberRulesUseTheOperator() {
        let songs = [song(1, "A", year: 1985), song(2, "B", year: 1995), song(3, "C", year: 0)]
        #expect(run([SmartRule(field: .year, op: .atMost, value: "1990")], over: songs) == ["A"])     // unknown year never matches
        #expect(run([SmartRule(field: .year, op: .equals, value: "1995")], over: songs) == ["B"])
    }

    @Test func notPlayedForAWhileCatchesNeverPlayedSongs() {
        let songs = [song(1, "Old", playedDaysAgo: 200), song(2, "Recent", playedDaysAgo: 3), song(3, "Never")]
        #expect(run([SmartRule(field: .playedDaysAgo, op: .atLeast, value: "90")], over: songs) == ["Never", "Old"])
        #expect(run([SmartRule(field: .playedDaysAgo, op: .atMost, value: "30")], over: songs) == ["Recent"])
    }

    @Test func addedDaysAgoNeedsADate() {
        let songs = [song(1, "New", addedDaysAgo: 2), song(2, "Old", addedDaysAgo: 400), song(3, "Undated")]
        #expect(run([SmartRule(field: .addedDaysAgo, op: .atMost, value: "30")], over: songs) == ["New"])
    }

    @Test func anUnfinishedRuleMatchesEverythingAndSongsWithoutAnIDAreSkipped() {
        let songs = [song(1, "A"), song(2, "B", remote: false)]
        #expect(run([SmartRule(field: .artist, op: .contains, value: "")], over: songs) == ["A"])
        #expect(run([SmartRule(field: .plays, op: .atLeast, value: "abc")], over: songs) == ["A"])
    }

    @Test func orderAndLimitApply() {
        let songs = [song(1, "A", plays: 1), song(2, "B", plays: 9), song(3, "C", plays: 5)]
        #expect(run([], over: songs, order: .mostPlayed) == ["B", "C", "A"])
        #expect(run([], over: songs, order: .mostPlayed, limit: 2) == ["B", "C"])
        #expect(run([], over: songs, order: .leastPlayed, limit: 1) == ["A"])
    }

    @Test func rulesSurviveSavingAndReloading() throws {
        let suite = "smart-test-\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let model = SmartPlaylistModel(defaults: defaults)
        model.add()
        var p = try #require(model.selected)
        p.name = "Mine"; p.rules = [SmartRule(field: .rating, op: .atLeast, value: "4")]
        model.update(p)
        let again = SmartPlaylistModel(defaults: defaults)
        #expect(again.lists.contains { $0.name == "Mine" && $0.rules.first?.value == "4" })
        again.remove(p.id)
        #expect(!SmartPlaylistModel(defaults: defaults).lists.contains { $0.id == p.id })
    }

    @Test func savedNamesNeverCollideWithServerPlaylists() {
        #expect(SmartPlaylistModel.freeName("Mix", taken: ["other"]) == "Mix")
        #expect(SmartPlaylistModel.freeName("Mix", taken: ["mix", "Mix 2"]) == "Mix 3")
        #expect(SmartPlaylistModel.freeName("  ", taken: []) == "Smart playlist")
    }
}
