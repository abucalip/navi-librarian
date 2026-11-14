import Foundation
import Testing
@testable import DiscairUI

@MainActor
struct SleepTimerTests {
    private final class Clock { var now = Date(timeIntervalSince1970: 1_000_000) }

    private func make(_ clock: Clock) -> SleepTimer {
        // The tick never fires by itself; the tests call `check()`.
        SleepTimer(now: { clock.now }, pause: { _ in try? await Task.sleep(for: .seconds(3600)) })
    }

    @Test func theLengthsAre15_30_45_60And90() {
        #expect(SleepTimer.lengths == [15, 30, 45, 60, 90])
    }

    @Test func itExpiresOnceWhenTimeIsUp() {
        let clock = Clock(), t = make(clock)
        var fired = 0
        t.onExpire = { fired += 1 }
        t.start(minutes: 15)
        #expect(t.isRunning && t.chosen == 15 && t.minutesLeft == 15)
        clock.now.addTimeInterval(14 * 60); t.check()
        #expect(fired == 0 && t.minutesLeft == 1)
        clock.now.addTimeInterval(60); t.check()
        #expect(fired == 1 && !t.isRunning && t.minutesLeft == nil && t.chosen == nil)
        t.check()
        #expect(fired == 1)
    }

    @Test func minutesAreRoundedUp() {
        let clock = Clock(), t = make(clock)
        t.start(minutes: 30)
        clock.now.addTimeInterval(29 * 60 + 30); t.check()
        #expect(t.minutesLeft == 1)
        t.start(minutes: 15)
        clock.now.addTimeInterval(10 * 60 + 30); t.check()
        #expect(t.minutesLeft == 5)
    }

    @Test func startingAgainReplacesTheTimerAndCancelStopsIt() {
        let clock = Clock(), t = make(clock)
        var fired = 0
        t.onExpire = { fired += 1 }
        t.start(minutes: 15)
        t.start(minutes: 90)
        #expect(t.chosen == 90 && t.minutesLeft == 90)
        clock.now.addTimeInterval(16 * 60); t.check()
        #expect(fired == 0)
        t.cancel()
        clock.now.addTimeInterval(3600); t.check()
        #expect(fired == 0 && !t.isRunning)
        t.start(minutes: 0)
        #expect(!t.isRunning)
    }

    @Test func itIsCancelledWhenNothingPlaysAnyMore() {
        let clock = Clock(), t = make(clock)
        var fired = 0
        t.onExpire = { fired += 1 }
        t.isPlaying = { false }
        t.start(minutes: 15)
        clock.now.addTimeInterval(60); t.check()
        #expect(!t.isRunning && fired == 0)
    }

    @Test func theWords() {
        #expect(SleepTimer.entryTitle(nil) == "Off" && SleepTimer.entryTitle(45) == "45 minutes")
        #expect(SleepTimer.shortText(minutesLeft: 45) == "45 min" && SleepTimer.shortText(minutesLeft: nil) == nil)
        #expect(SleepTimer.spoken(minutesLeft: 45) == "Sleep timer, 45 minutes left")
        #expect(SleepTimer.spoken(minutesLeft: 1) == "Sleep timer, 1 minute left")
        #expect(SleepTimer.spoken(minutesLeft: nil) == "Sleep timer, off")
    }
}
