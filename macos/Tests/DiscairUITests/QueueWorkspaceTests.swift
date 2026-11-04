import DiscairAudio
import Foundation
import Testing
@testable import DiscairUI

private func song(_ id: String, _ artist: String = "A") -> QueueItem { QueueItem(songID: id, title: id, artist: artist, duration: 120) }
private func defaults() -> UserDefaults { UserDefaults(suiteName: "queue-ws-\(UUID().uuidString)")! }

struct RadioPlannerTests {
    @Test func takesArtistsInTurnAndSkipsQueuedSongs() {
        var g = SystemRandomNumberGenerator()
        let groups = [[song("a1", "A"), song("a2", "A"), song("a3", "A")], [song("b1", "B"), song("b2", "B")]]
        let out = RadioPlanner.pick(groups: groups, exclude: ["a1"], count: 4, using: &g)
        #expect(out.count == 4)
        #expect(!out.contains { $0.songID == "a1" })
        #expect(out.prefix(2).map(\.artist).sorted() == ["A", "B"])   // first round has one of each
    }

    @Test func stopsAtCountAndWhenCandidatesRunOut() {
        var g = SystemRandomNumberGenerator()
        #expect(RadioPlanner.pick(groups: [[song("a")], [song("b")]], exclude: [], count: 1, using: &g).count == 1)
        #expect(RadioPlanner.pick(groups: [[song("a")]], exclude: [], count: 10, using: &g).count == 1)
        #expect(RadioPlanner.pick(groups: [], exclude: [], count: 10, using: &g).isEmpty)
        #expect(RadioPlanner.pick(groups: [[song("a")]], exclude: [], count: 0, using: &g).isEmpty)
    }

    @Test func aSongInTwoListsIsPickedOnce() {
        var g = SystemRandomNumberGenerator()
        let out = RadioPlanner.pick(groups: [[song("x")], [song("x")]], exclude: [], count: 5, using: &g)
        #expect(out.map(\.songID) == ["x"])
    }
}

@MainActor struct RadioModelTests {
    @Test func returnsSongsAndNeverIncludesTheSeed() async {
        let radio = RadioModel(defaults: defaults())
        let seed = song("seed", "A")
        let out = await radio.songs(like: seed, queued: ["q1"]) { _ in [[song("seed"), song("q1"), song("n1", "B")]] }
        #expect(out.map(\.songID) == ["n1"])
        #expect(radio.status == "Added 1 songs like A.")
        #expect(!radio.busy)
    }

    @Test func saysSoWhenNothingSimilarIsHeld() async {
        let radio = RadioModel(defaults: defaults())
        let out = await radio.songs(like: song("s", "Solo"), queued: []) { _ in [] }
        #expect(out.isEmpty)
        #expect(radio.status == "No similar artists in your library for Solo.")
    }

    @Test func aFailureIsReportedNotThrown() async {
        struct Boom: Error {}
        let radio = RadioModel(defaults: defaults())
        let out = await radio.songs(like: song("s"), queued: []) { _ in throw Boom() }
        #expect(out.isEmpty)
        #expect(radio.status == "Could not find similar songs.")
    }

    @Test func autoplayIsRemembered() {
        let d = defaults()
        let a = RadioModel(defaults: d)
        #expect(a.autoplay == false)
        a.autoplay = true
        #expect(RadioModel(defaults: d).autoplay)
    }
}

@MainActor struct SavedQueueStoreTests {
    @Test func savesAndReloads() {
        let d = defaults()
        let store = SavedQueueStore(defaults: d)
        #expect(store.save(name: "Late night", items: [song("1"), song("2")]) != nil)
        let again = SavedQueueStore(defaults: d)
        #expect(again.queues.map(\.name) == ["Late night"])
        #expect(again.queues[0].items.map(\.songID) == ["1", "2"])
        #expect(again.queues[0].minutes == 4)
    }

    @Test func anEmptyQueueIsNotSavedAndABlankNameGetsADefault() {
        let store = SavedQueueStore(defaults: defaults())
        #expect(store.save(name: "x", items: []) == nil)
        let q = store.save(name: "   ", items: [song("1")])
        #expect(q?.name.hasPrefix("Queue ") == true)
    }

    @Test func aUsedNameReplacesTheOldQueueAndMovesFirst() {
        let store = SavedQueueStore(defaults: defaults())
        let first = store.save(name: "Mix", items: [song("1")])
        store.save(name: "Other", items: [song("2")])
        let updated = store.save(name: "mix", items: [song("3")])
        #expect(store.queues.map(\.name) == ["mix", "Other"])
        #expect(updated?.id == first?.id)
        #expect(store.queues[0].items.map(\.songID) == ["3"])
    }

    @Test func limitsQueuesAndSongs() {
        let store = SavedQueueStore(defaults: defaults())
        for n in 0..<(SavedQueueStore.maxQueues + 3) { store.save(name: "q\(n)", items: [song("\(n)")]) }
        #expect(store.queues.count == SavedQueueStore.maxQueues)
        #expect(store.queues[0].name == "q32")
        let big = (0..<(SavedQueueStore.maxSongs + 10)).map { song("s\($0)") }
        #expect(store.save(name: "big", items: big)?.items.count == SavedQueueStore.maxSongs)
    }

    @Test func loadedSongsGetFreshRowIDsAndDeleteWorks() {
        let store = SavedQueueStore(defaults: defaults())
        let saved = store.save(name: "Mix", items: [song("1")])!
        let loaded = store.songs(of: saved.id)
        #expect(loaded.map(\.songID) == ["1"])
        #expect(loaded[0].id != saved.items[0].id)
        store.remove(saved.id)
        #expect(store.queues.isEmpty)
        #expect(store.songs(of: saved.id).isEmpty)
    }
}
