import Testing
@testable import DiscairAudio

@MainActor private final class FakeDevice: OutputDeviceRate {
    var current: Double? = 44100
    var available: [Double] = [44100, 48000, 88200, 96000]
    var sets: [Double] = []
    var refuse = false
    func set(_ rate: Double) -> Bool { if refuse { return false }; sets.append(rate); current = rate; return true }
}

@Suite struct OutputRateTests {
    @Test func exactRateWins() { #expect(OutputRate.target(fileRate: 48000, available: [44100, 48000, 96000]) == 48000) }
    @Test func wholeMultipleWhenNoExact() { #expect(OutputRate.target(fileRate: 44100, available: [48000, 88200, 96000]) == 88200) }
    @Test func noMultipleLeavesTheDevice() { #expect(OutputRate.target(fileRate: 44100, available: [48000, 96000]) == nil) }
    @Test func nonsenseRate() { #expect(OutputRate.target(fileRate: 0, available: [44100]) == nil) }

    @MainActor @Test func changesOnceAndRestoresTheFirstRate() {
        let d = FakeDevice(); let m = RateMatcher(device: d)
        #expect(m.match(fileRate: 96000))
        #expect(!m.match(fileRate: 96000))          // already there
        #expect(m.match(fileRate: 48000))
        #expect(d.current == 48000)
        m.restore()
        #expect(d.current == 44100)
        m.restore()                                  // nothing more to restore
        #expect(d.sets == [96000, 48000, 44100])
    }

    @MainActor @Test func unsupportedRateKeepsCurrentAndNothingToRestore() {
        let d = FakeDevice(); d.available = [48000]
        let m = RateMatcher(device: d)
        #expect(!m.match(fileRate: 44100))
        m.restore()
        #expect(d.sets.isEmpty)
    }

    @MainActor @Test func refusedChangeIsNotRemembered() {
        let d = FakeDevice(); d.refuse = true
        let m = RateMatcher(device: d)
        #expect(!m.match(fileRate: 96000))
        d.refuse = false; m.restore()
        #expect(d.sets.isEmpty)
    }
}
