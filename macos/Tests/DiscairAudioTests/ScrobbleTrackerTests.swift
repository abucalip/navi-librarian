import Testing
@testable import DiscairAudio

struct ScrobbleTrackerTests {
    /// Plays `seconds` of a song in quarter-second readings from `from`.
    private func play(_ t: inout ScrobbleTracker, from: Double, seconds: Double, duration: Double? = nil) -> [ScrobbleTracker.Action] {
        var out: [ScrobbleTracker.Action] = []
        var pos = from
        out += t.update(position: pos, playerDuration: duration, isPlaying: true)
        for _ in 0..<Int(seconds * 4) { pos += 0.25; out += t.update(position: pos, playerDuration: duration, isPlaying: true) }
        return out
    }

    @Test func nowPlayingOnceThenScrobbleAtHalf() {
        var t = ScrobbleTracker(serverDuration: 200)
        let a = play(&t, from: 0, seconds: 120, duration: 200)
        #expect(a == [.nowPlaying, .scrobble])
    }

    @Test func belowTheThresholdNothingIsScrobbled() {
        var t = ScrobbleTracker(serverDuration: 200)
        #expect(play(&t, from: 0, seconds: 99, duration: 200) == [.nowPlaying])
    }

    @Test func longSongsScrobbleAt240Seconds() {
        var t = ScrobbleTracker(serverDuration: 900)
        #expect(play(&t, from: 0, seconds: 239, duration: 900) == [.nowPlaying])
        #expect(play(&t, from: 239, seconds: 2, duration: 900) == [.scrobble])
    }

    @Test func songsUnder30SecondsSendNowPlayingOnly() {
        var t = ScrobbleTracker(serverDuration: 20)
        #expect(play(&t, from: 0, seconds: 20, duration: 20) == [.nowPlaying])
    }

    @Test func seekingForwardPastTheThresholdDoesNotScrobble() {
        var t = ScrobbleTracker(serverDuration: 200)
        _ = play(&t, from: 0, seconds: 10, duration: 200)
        #expect(t.update(position: 150, playerDuration: 200, isPlaying: true).isEmpty)
        #expect(t.played < 11)
    }

    @Test func pausingAddsNothingAndSeekingBackRemovesNothing() {
        var t = ScrobbleTracker(serverDuration: 200)
        _ = play(&t, from: 0, seconds: 60, duration: 200)
        for _ in 0..<400 { _ = t.update(position: 60, playerDuration: 200, isPlaying: false) }
        #expect(t.played >= 59.9 && t.played <= 60.1)
        _ = t.update(position: 5, playerDuration: 200, isPlaying: true)       // seek back
        #expect(t.played >= 59.9 && t.played <= 60.1)
        #expect(play(&t, from: 5, seconds: 41, duration: 200).contains(.scrobble))
    }

    @Test func nowPlayingWaitsUntilTheSongIsReallyPlaying() {
        var t = ScrobbleTracker(serverDuration: 200)
        #expect(t.update(position: 0, playerDuration: 200, isPlaying: false).isEmpty)
        #expect(t.update(position: 0, playerDuration: 200, isPlaying: true) == [.nowPlaying])
    }

    @Test func unknownLengthFallsBackTo240Seconds() {
        var t = ScrobbleTracker(serverDuration: nil)
        #expect(play(&t, from: 0, seconds: 200, duration: nil) == [.nowPlaying])
        #expect(play(&t, from: 200, seconds: 41, duration: nil) == [.scrobble])
    }

    @Test func theLargerLengthWinsWhenTheyDisagreeByMoreThanTenPercent() {
        #expect(ScrobbleTracker.effectiveDuration(server: 100, player: 300) == 300)
        #expect(ScrobbleTracker.effectiveDuration(server: 100, player: 105) == 100)
        #expect(ScrobbleTracker.effectiveDuration(server: 0, player: 180) == 180)
        #expect(ScrobbleTracker.effectiveDuration(server: nil, player: nil) == nil)
    }

    @Test func aNewTrackerIsANewPlay() {
        var t = ScrobbleTracker(serverDuration: 60)
        #expect(play(&t, from: 0, seconds: 30, duration: 60) == [.nowPlaying, .scrobble])
        var again = ScrobbleTracker(serverDuration: 60)
        #expect(play(&again, from: 0, seconds: 30, duration: 60) == [.nowPlaying, .scrobble])
    }
}
