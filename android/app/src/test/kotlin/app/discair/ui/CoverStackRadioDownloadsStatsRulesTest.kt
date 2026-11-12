package app.discair.ui

import app.discair.model.RadioDownload
import app.discair.model.RadioNow
import app.discair.model.RadioNowState
import app.discair.model.RadioPlay
import app.discair.ui.common.ChartRules
import app.discair.ui.downloads.CoverStackDownloadsRules
import app.discair.ui.radio.CoverStackRadioRules
import app.discair.ui.radio.CoverStackRadioRules.Trailing
import app.discair.ui.stats.CoverStackStatsRules
import app.discair.ui.stats.StatsRange
import app.discair.ui.theme.Layout
import app.discair.ui.theme.Family
import app.discair.ui.theme.Palettes
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CoverStackRadioDownloadsStatsRulesTest {
    private fun play(artist: String?, station: String = "FIP") = RadioPlay(1, station, artist, "Roads", null, false, false, null)
    private fun now(state: RadioNowState = RadioNowState.Ok, artist: String? = "Talk Talk", title: String? = "Life's What You Make It") =
        RadioNow(state, null, artist, title, 7L, false, null)

    @Test fun heardRowControlFollowsTheDownloadState() {
        assertEquals(Trailing.Get, CoverStackRadioRules.trailing(true, RadioDownload.Ready))
        assertEquals(Trailing.TryAgain, CoverStackRadioRules.trailing(true, RadioDownload.Failed))
        assertEquals(Trailing.InLibrary, CoverStackRadioRules.trailing(true, RadioDownload.Owned))
        assertEquals(Trailing.Requested, CoverStackRadioRules.trailing(true, RadioDownload.Done))
        assertEquals(Trailing.Working, CoverStackRadioRules.trailing(true, RadioDownload.Working))
    }

    @Test fun aSongWithNoNamedArtistHasNoButton() {
        assertEquals(Trailing.None, CoverStackRadioRules.trailing(false, RadioDownload.Ready))
    }

    @Test fun heardStateIsSaidInWords() {
        assertEquals("In your library", CoverStackRadioRules.stateWords(Trailing.InLibrary))
        assertEquals("Requested", CoverStackRadioRules.stateWords(Trailing.Requested))
        assertEquals("Requesting…", CoverStackRadioRules.stateWords(Trailing.Working))
        assertEquals(null, CoverStackRadioRules.stateWords(Trailing.Get))
    }

    @Test fun heardLineNamesArtistStationAndTime() {
        assertEquals("Talk Talk · FIP · 21:09", CoverStackRadioRules.heardLine(play("Talk Talk"), "21:09"))
        assertEquals("Artist not named · NTS 1 · 17:12", CoverStackRadioRules.heardLine(play(null, "NTS 1"), "17:12"))
        assertEquals("Talk Talk", CoverStackRadioRules.heardLine(play("Talk Talk", ""), null))
    }

    @Test fun liveHeadlineIsTheSongWhenOneIsKnown() {
        assertEquals("Life's What You Make It" to "Talk Talk · heard on FIP", CoverStackRadioRules.headline("FIP", now(), "Live radio"))
        assertEquals("Life's What You Make It" to "Heard on FIP", CoverStackRadioRules.headline("FIP", now(artist = null), "Live radio"))
    }

    @Test fun liveHeadlineFallsBackToTheStation() {
        assertEquals("FIP" to "Live radio", CoverStackRadioRules.headline("FIP", null, "Live radio"))
        assertEquals("FIP" to "Station unreachable.", CoverStackRadioRules.headline("FIP", now(RadioNowState.Unavailable), "Station unreachable."))
    }

    @Test fun getButtonSaysGetThisSongOnlyWhenItCanBeAskedFor() {
        assertEquals("Get this song", CoverStackRadioRules.getLabel(RadioDownload.Ready))
        assertEquals("Try again", CoverStackRadioRules.getLabel(RadioDownload.Failed))
        assertEquals("Owned", CoverStackRadioRules.getLabel(RadioDownload.Owned))
        assertEquals("On air", CoverStackRadioRules.airTag(true))
        assertEquals("Paused", CoverStackRadioRules.airTag(false))
    }

    @Test fun downloadCardLines() {
        assertEquals("Downloading · 64% · 7 of 9 files", CoverStackDownloadsRules.stateLine("Downloading", "64% · 7 of 9 files", null))
        assertEquals("Imported · arrived 18:02", CoverStackDownloadsRules.stateLine("Imported", null, "18:02"))
        assertEquals("Slowdive · 1995", CoverStackDownloadsRules.subLine("Slowdive", false, "Pygmalion", 1995, "Not reported"))
        assertEquals("Slowdive · Song on Pygmalion · FLAC", CoverStackDownloadsRules.subLine("Slowdive", true, "Pygmalion", null, "FLAC"))
    }

    @Test fun statsRangesUseTheMockupWords() {
        assertEquals(listOf("3 months", "12 months", "5 years", "All time"), StatsRange.entries.map(CoverStackStatsRules::rangeLabel))
    }

    @Test fun softBrutChartsAreOutlinedWithAnAreaAndNoOtherLayoutMoved() {
        val soft = ChartRules.style(Palettes.SoftBrut.family, Layout.CoverStack, true)
        assertTrue(soft.area)
        assertEquals(ChartRules.style(Family.Brutal, Layout.Standard, true).copy(area = true), soft)
        // Another Brutal layout keeps its own style.
        assertEquals(false, ChartRules.style(Family.Brutal, Layout.Standard, true).area)
    }
}
