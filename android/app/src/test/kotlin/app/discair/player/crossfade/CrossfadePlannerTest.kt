package app.discair.player.crossfade

import app.discair.player.RepeatMode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CrossfadePlannerTest {
    private val on = CrossfadeSettings(enabled = true, seconds = 5, skipSameAlbum = true)
    private val a = JoinSong("a", albumId = "album1", durationMs = 200_000)
    private val b = JoinSong("b", albumId = "album2", durationMs = 180_000)

    private fun join(
        current: JoinSong? = a,
        next: JoinSong? = b,
        repeat: RepeatMode = RepeatMode.Off,
        sameEntry: Boolean = false,
        automatic: Boolean = true,
        buffered: Long = 30_000,
    ) = JoinContext(current, next, repeat, sameEntry, automatic, buffered)

    private fun reason(settings: CrossfadeSettings = on, join: JoinContext = join()) =
        (CrossfadePlanner.plan(settings, join) as CrossfadeDecision.None).reason

    @Test fun anOrdinaryJoinFadesForTheSettingAndStartsThatLongBeforeTheEnd() {
        assertEquals(CrossfadeDecision.Fade(5_000, 195_000), CrossfadePlanner.plan(on, join()))
    }

    @Test fun offGivesNoFade() = assertEquals(NoFadeReason.Off, reason(settings = on.copy(enabled = false)))

    @Test fun aManualChangeGivesNoFade() = assertEquals(NoFadeReason.NotAutomatic, reason(join = join(automatic = false)))

    @Test fun noNextSongOrNoCurrentSongGivesNoFade() {
        assertEquals(NoFadeReason.NoNextSong, reason(join = join(next = null)))
        assertEquals(NoFadeReason.NoNextSong, reason(join = join(current = null)))
    }

    @Test fun repeatOneAndTheSameEntryNeverFadeIntoThemselves() {
        assertEquals(NoFadeReason.SameEntry, reason(join = join(repeat = RepeatMode.One)))
        assertEquals(NoFadeReason.SameEntry, reason(join = join(sameEntry = true, repeat = RepeatMode.All)))
    }

    @Test fun repeatAllAtTheEndOfTheQueueFadesIntoTheFirstSong() {
        val last = JoinSong("last", "album9", 150_000)
        val first = JoinSong("first", "album1", 150_000)
        assertEquals(CrossfadeDecision.Fade(5_000, 145_000), CrossfadePlanner.plan(on, join(current = last, next = first, repeat = RepeatMode.All)))
    }

    @Test fun anUnknownOrZeroDurationOnEitherSongGivesNoFade() {
        assertEquals(NoFadeReason.UnknownDuration, reason(join = join(current = a.copy(durationMs = null))))
        assertEquals(NoFadeReason.UnknownDuration, reason(join = join(next = b.copy(durationMs = null))))
        assertEquals(NoFadeReason.UnknownDuration, reason(join = join(next = b.copy(durationMs = 0))))
        assertEquals(NoFadeReason.UnknownDuration, reason(join = join(current = a.copy(durationMs = -1))))
    }

    @Test fun aShortSongGetsAShorterFadeOfAThirdOfItsLength() {
        val short = a.copy(durationMs = 9_000)
        assertEquals(CrossfadeDecision.Fade(3_000, 6_000), CrossfadePlanner.plan(on, join(current = short)))
        assertEquals(CrossfadeDecision.Fade(3_000, 197_000), CrossfadePlanner.plan(on, join(next = b.copy(durationMs = 9_000))))
    }

    @Test fun aSongTooShortForTheMinimumFadeHasNone() {
        assertEquals(NoFadeReason.TooShort, reason(join = join(current = a.copy(durationMs = 2_000))))
        assertEquals(NoFadeReason.TooShort, reason(join = join(next = b.copy(durationMs = 2_999))))
        assertEquals(CrossfadeDecision.Fade(1_000, 2_000), CrossfadePlanner.plan(on, join(current = a.copy(durationMs = 3_000))))
    }

    @Test fun consecutiveSongsOfOneAlbumStayGaplessWhenTheRuleIsOn() {
        val same = b.copy(albumId = "album1")
        assertEquals(NoFadeReason.SameAlbum, reason(join = join(next = same)))
        assertTrue(CrossfadePlanner.plan(on.copy(skipSameAlbum = false), join(next = same)) is CrossfadeDecision.Fade)
    }

    @Test fun songsWithNoAlbumIdAreNeverTreatedAsOneAlbum() {
        val x = a.copy(albumId = ""); val y = b.copy(albumId = "")
        assertTrue(CrossfadePlanner.plan(on, join(current = x, next = y)) is CrossfadeDecision.Fade)
    }

    @Test fun aNextSongThatIsNotBufferedEnoughGivesNoFadeAndNoWait() {
        assertEquals(NoFadeReason.NextNotReady, reason(join = join(buffered = 6_999)))
        assertTrue(CrossfadePlanner.plan(on, join(buffered = 7_000)) is CrossfadeDecision.Fade)
    }

    @Test fun theReadyCheckUsesTheFadeActuallyUsedNotTheSetting() {
        val short = a.copy(durationMs = 6_000) // fade 2 s, so 4 s of buffer is enough
        assertTrue(CrossfadePlanner.plan(on, join(current = short, buffered = 4_000)) is CrossfadeDecision.Fade)
    }

    @Test fun refusalsAreCheckedInTheContractOrder() {
        val everythingWrong = join(current = a.copy(durationMs = null), next = b.copy(albumId = "album1"), repeat = RepeatMode.One, automatic = false, buffered = 0)
        assertEquals(NoFadeReason.Off, reason(settings = on.copy(enabled = false), join = everythingWrong))
        assertEquals(NoFadeReason.NotAutomatic, reason(join = everythingWrong))
        assertEquals(NoFadeReason.SameEntry, reason(join = everythingWrong.copy(automatic = true)))
        assertEquals(NoFadeReason.UnknownDuration, reason(join = everythingWrong.copy(automatic = true, repeat = RepeatMode.Off)))
    }

    @Test fun hostileLengthsAreClamped() {
        assertEquals(1, CrossfadeSettings.sanitizeSeconds(-5))
        assertEquals(1, CrossfadeSettings.sanitizeSeconds(0))
        assertEquals(12, CrossfadeSettings.sanitizeSeconds(10_000))
        assertEquals(5, CrossfadeSettings.sanitizeSeconds(null))
        assertEquals(1_000L, CrossfadeSettings(seconds = -9).lengthMs)
        assertEquals(12_000L, CrossfadeSettings(seconds = Int.MAX_VALUE).lengthMs)
    }

    @Test fun storedTextThatIsNotAWholeNumberGivesTheDefault() {
        for (bad in listOf(null, "", "  ", "NaN", "abc", "5.5", "1e9", "99999999999999999999999")) {
            assertEquals(bad, 5, CrossfadeSettings.parseSeconds(bad))
        }
        assertEquals(1, CrossfadeSettings.parseSeconds("-3"))
        assertEquals(1, CrossfadeSettings.parseSeconds("0"))
        assertEquals(12, CrossfadeSettings.parseSeconds("10000"))
        assertEquals(7, CrossfadeSettings.parseSeconds(" 7 "))
    }

    @Test fun aFadeNeverRunsLongerThanTheClampedSettingOrAThirdOfTheShorterSong() {
        for (sec in -3..20) for (dur in listOf(0L, 500L, 2_999L, 3_000L, 20_000L, 600_000L)) {
            val d = CrossfadePlanner.plan(CrossfadeSettings(true, sec), join(current = a.copy(durationMs = dur)))
            if (d is CrossfadeDecision.Fade) {
                assertTrue(d.lengthMs in 1_000L..12_000L)
                assertTrue(d.lengthMs <= dur / 3)
                assertEquals(dur - d.lengthMs, d.startAtMs)
            }
        }
    }
}
