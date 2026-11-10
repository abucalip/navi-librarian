import Foundation
import Testing
@testable import DiscairUI

@MainActor
struct CupertinoRound1Tests {
    private func sentences(_ n: Int) -> String { (1...n).map { "Sentence number \($0) has exactly seven words." }.joined(separator: " ") }

    @Test func shortBioStaysOneParagraph() {
        #expect(BioParagraphs.split(sentences(10)).count == 1)   // 70 words
    }

    @Test func sourceBreaksAreKept() {
        #expect(BioParagraphs.split("One.\n\nTwo.\nThree.") == ["One.", "Two.", "Three."])
    }

    @Test func longBioSplitsAtFullStopsNearEveryHundredWords() {
        let parts = BioParagraphs.split(sentences(40))   // 280 words
        #expect(parts.count >= 2)
        for p in parts.dropLast() {
            #expect(p.hasSuffix("."))
            #expect(abs(p.split(separator: " ").count - 100) <= 50)
        }
        #expect(parts.joined(separator: " ") == sentences(40))
    }

    @Test func randomPickIsStablePerSaltAndBounded() {
        struct Item: Identifiable { let id: Int }
        let list = (0..<20).map(Item.init)
        let a = RandomPick.pick(list, 6, salt: 1), b = RandomPick.pick(list, 6, salt: 1), c = RandomPick.pick(list, 6, salt: 2)
        #expect(a.count == 6 && a.map(\.id) == b.map(\.id))
        #expect(a.map(\.id) != c.map(\.id))
    }

    @Test func nowPlayingRemembersWhereItWasOpenedFrom() {
        let s = AppState(screen: .artists)
        s.screen = .nowPlaying
        #expect(s.nowPlayingReturn == .artists)
        s.closeNowPlaying()
        #expect(s.screen == .artists)
    }
}
