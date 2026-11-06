import Testing
@testable import DiscairAudio

struct SkipRuleTests {
    @Test func abandonedBeforeThirtySecondsIsASkip() {
        #expect(SkipRule.isSkip(played: 12, duration: 240, leftByOwner: true, wasLastInQueue: false))
        #expect(!SkipRule.isSkip(played: 30, duration: 240, leftByOwner: true, wasLastInQueue: false))
    }
    @Test func shortSongsUseHalfTheirLength() {
        #expect(SkipRule.limit(duration: 40) == 20)
        #expect(SkipRule.isSkip(played: 19, duration: 40, leftByOwner: true, wasLastInQueue: false))
        #expect(!SkipRule.isSkip(played: 20, duration: 40, leftByOwner: true, wasLastInQueue: false))
    }
    @Test func unknownLengthUsesThirtySeconds() {
        #expect(SkipRule.limit(duration: nil) == 30)
        #expect(SkipRule.limit(duration: 0) == 30)
    }
    @Test func endsAndLastInQueueAreNeverSkips() {
        #expect(!SkipRule.isSkip(played: 5, duration: 240, leftByOwner: false, wasLastInQueue: false))
        #expect(!SkipRule.isSkip(played: 5, duration: 240, leftByOwner: true, wasLastInQueue: true))
        #expect(!SkipRule.isSkip(played: .nan, duration: 240, leftByOwner: true, wasLastInQueue: false))
    }
}
