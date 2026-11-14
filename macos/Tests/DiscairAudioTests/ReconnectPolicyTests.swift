import Testing
@testable import DiscairAudio

struct ReconnectPolicyTests {
    @Test func theTriesComeAfter2_5_10_20_And30SecondsThenItGivesUp() {
        var p = ReconnectPolicy()
        var steps: [ReconnectPolicy.Step] = []
        for _ in 0..<6 { steps.append(p.drop()) }
        #expect(steps == [.retry(delay: 2, attempt: 1), .retry(delay: 5, attempt: 2), .retry(delay: 10, attempt: 3),
                          .retry(delay: 20, attempt: 4), .retry(delay: 30, attempt: 5), .giveUp])
        #expect(ReconnectPolicy.attempts == 5)
    }

    @Test func soundStartsTheCountAgain() {
        var p = ReconnectPolicy()
        _ = p.drop(); _ = p.drop()
        p.sound()
        #expect(p.drop() == .retry(delay: 2, attempt: 1))
    }

    @Test func aGivenUpPolicyStaysGivenUpUntilReset() {
        var p = ReconnectPolicy()
        for _ in 0..<5 { _ = p.drop() }
        #expect(p.drop() == .giveUp && p.drop() == .giveUp)
        p.reset()
        #expect(p.drop() == .retry(delay: 2, attempt: 1))
    }

    @Test func twentySecondsWithoutSoundIsTheLimit() {
        #expect(ReconnectPolicy.silenceLimit == 20)
    }
}
