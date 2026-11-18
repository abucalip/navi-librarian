package app.discair.ui

import app.discair.model.AcquisitionJob
import app.discair.model.ServiceId
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexMenuItem
import app.discair.ui.common.IndexSheetRules
import app.discair.ui.common.indexMenuItems
import app.discair.ui.downloads.IndexDownloadsRules
import app.discair.ui.downloads.IndexDownloadsRules.Tab
import app.discair.ui.player.IndexEqRules
import app.discair.ui.settings.IndexSettingsRules
import app.discair.ui.stats.IndexStatsRules
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Step I6 of docs/INDEX_THEME.md: the words and choices behind Index's sheets, Downloads, Stats, Server, Settings, Appearance and Equalizer. */
class IndexStatusRulesTest {
    private fun job(status: String, progress: Map<String, Double> = emptyMap()) = AcquisitionJob(
        "Bark Psychosis", "Hex", status, 1.0, null,
        JsonObject(if (progress.isEmpty()) emptyMap() else mapOf("live_progress" to JsonObject(progress.mapValues { JsonPrimitive(it.value) }))),
    )

    // ----- sheets

    @Test fun optionsAreLetteredInOrder() {
        assertEquals(listOf("A", "B", "C"), (0..2).map(IndexSheetRules::letter))
        assertEquals("Z", IndexSheetRules.letter(25))
        assertEquals("AA", IndexSheetRules.letter(26))
    }

    @Test fun anOptionTakesItsGlyphFromItsWords() {
        assertEquals(IndexIcons.QueueAdd, IndexSheetRules.glyphFor("Play next"))
        assertEquals(IndexIcons.Queue, IndexSheetRules.glyphFor("Add to queue"))
        assertEquals(IndexIcons.Paths, IndexSheetRules.glyphFor("Paths from this album"))
        assertEquals(IndexIcons.Close, IndexSheetRules.glyphFor("Not this album"))
        assertEquals(IndexIcons.Ban, IndexSheetRules.glyphFor("Never suggest this artist"))
        assertEquals(IndexIcons.Ban, IndexSheetRules.glyphFor("Block genre: Jazz"))
        assertEquals(IndexIcons.Download, IndexSheetRules.glyphFor("Download to device"))
        assertNull(IndexSheetRules.glyphFor("Something new"))
    }

    @Test fun onlyTheWaysToDropAnArtistAreRed() {
        assertTrue(IndexSheetRules.isDanger("Never suggest this artist"))
        assertTrue(IndexSheetRules.isDanger("Not this artist"))
        assertFalse(IndexSheetRules.isDanger("Not this album"))
        assertFalse(IndexSheetRules.isDanger("Play next"))
        assertTrue(IndexMenuItem("Never suggest artist") {}.danger)
    }

    @Test fun plainPairsBecomeOptionsThatRunTheirAction() {
        var ran = ""
        val items = indexMenuItems(listOf("Play next" to { ran = "next" }, "Add to queue" to { ran = "queue" }))
        assertEquals(listOf("Play next", "Add to queue"), items.map { it.label })
        items[1].run()
        assertEquals("queue", ran)
    }

    @Test fun theHeaderEyebrowSaysThePlaceOnlyWhenItIsKnown() {
        assertEquals("Pick 01 / 12 · Bark Psychosis", IndexSheetRules.eyebrow("Pick", 1, 12, "Bark Psychosis"))
        assertEquals("Song 05 / 10 · Khruangbin", IndexSheetRules.eyebrow("Song", 5, 10, "Khruangbin"))
        assertEquals("Artist", IndexSheetRules.eyebrow("Artist", null, null, null))
        assertEquals("Station", IndexSheetRules.eyebrow("Station", 0, 4, " "))
    }

    // ----- downloads

    @Test fun recordsFallUnderActiveDoneOrFailed() {
        assertEquals(Tab.Active, IndexDownloadsRules.tabOf(job("downloading")))
        assertEquals(Tab.Active, IndexDownloadsRules.tabOf(job("searching")))
        assertEquals(Tab.Failed, IndexDownloadsRules.tabOf(job("download_failed")))
        assertEquals(Tab.Failed, IndexDownloadsRules.tabOf(job("no_matches")))
        assertEquals(Tab.Done, IndexDownloadsRules.tabOf(job("imported")))
        assertEquals(Tab.Done, IndexDownloadsRules.tabOf(job("dismissed")))
    }

    @Test fun theTabsCountTheirRecordsAndTheFirstWithOneOpens() {
        val jobs = listOf(job("downloading"), job("importing"), job("imported"), job("download_failed"))
        assertEquals(listOf("Active 2", "Done 1", "Failed 1"), IndexDownloadsRules.tabLabels(jobs))
        assertEquals(Tab.Active, IndexDownloadsRules.firstTab(jobs))
        assertEquals(Tab.Done, IndexDownloadsRules.firstTab(listOf(job("imported"))))
        assertEquals(Tab.Active, IndexDownloadsRules.firstTab(emptyList()))
        assertEquals(1, IndexDownloadsRules.shown(jobs, Tab.Failed).size)
        assertEquals("01", IndexDownloadsRules.number(0))
    }

    @Test fun theFigureIsThePercentWhileLoadingAndAMarkWhenAStepFailed() {
        assertEquals("62", IndexDownloadsRules.figure(job("downloading", mapOf("percent" to 62.4))))
        assertNull(IndexDownloadsRules.figure(job("downloading")))
        assertEquals("!", IndexDownloadsRules.figure(job("download_failed")))
        assertNull(IndexDownloadsRules.figure(job("imported")))
    }

    @Test fun theProgressLineNamesTheSpeedAndTheSongs() {
        assertEquals(
            "2.1 MB/s · 4 of 7 songs",
            IndexDownloadsRules.progress(job("downloading", mapOf("speed_bytes_per_second" to 2.1 * 1024 * 1024, "total_tracks" to 7.0, "remaining_tracks" to 3.0))),
        )
        assertNull(IndexDownloadsRules.progress(job("downloading", mapOf("percent" to 10.0))))
        assertEquals("Bark Psychosis", IndexDownloadsRules.meta(job("downloading")))
    }

    // ----- settings, server, appearance

    @Test fun aShortStateIsMonoAndASentenceIsNot() {
        assertTrue(IndexSettingsRules.monoState("Index · Signal Blue · follows the phone"))
        assertFalse(IndexSettingsRules.monoState("On. A few seconds after a successful import, the server reloads your library."))
    }

    @Test fun serviceLinesAddTheVersionAndThePingOnlyWhereTheyBelong() {
        assertEquals("Recommendations · v0.3.9", IndexSettingsRules.serviceMeta(ServiceId.Librarian, "Recommendations", "0.3.9", 84))
        assertEquals("Library · 84 ms", IndexSettingsRules.serviceMeta(ServiceId.Navidrome, "Library", "0.3.9", 84))
        assertEquals("Downloads", IndexSettingsRules.serviceMeta(ServiceId.Slskd, "Downloads", "0.3.9", 84))
        assertEquals("Recommendations · dev-abc", IndexSettingsRules.serviceMeta(ServiceId.Librarian, "Recommendations", "dev-abc", null))
        assertEquals("Library", IndexSettingsRules.serviceMeta(ServiceId.Navidrome, "Library", null, null))
    }

    @Test fun pageBarsCarryTheirCatalogueLines() {
        assertEquals("Discair 1.8.1", IndexSettingsRules.versionLine("1.8.1"))
        assertEquals("Discair", IndexSettingsRules.versionLine(null))
        assertEquals("Checked 14:02", IndexSettingsRules.checkedLine("14:02"))
    }

    @Test fun appearanceGroupsAndSwatchLines() {
        assertEquals(listOf("Day" to true, "Night" to false), IndexSettingsRules.slots(true))
        assertEquals(listOf("Theme" to null), IndexSettingsRules.slots(false))
        assertEquals("Day", IndexSettingsRules.swatchLine(light = true, chosen = false))
        assertEquals("Night · chosen", IndexSettingsRules.swatchLine(light = false, chosen = true))
    }

    // ----- stats and equalizer

    @Test fun statsDrawOnlyTheFiguresThePhoneKnows() {
        assertEquals(listOf("Albums" to "1,284", "Artists" to "312"), IndexStatsRules.figures(1284, 312))
        assertEquals(listOf("Albums" to "1,284"), IndexStatsRules.figures(1284, null))
        assertEquals(emptyList<Pair<String, String>>(), IndexStatsRules.figures(null, null))
    }

    @Test fun bandWordsAreShortUnderTheColumns() {
        assertEquals("60", IndexEqRules.bandShort(60))
        assertEquals("14K", IndexEqRules.bandShort(14000))
    }
}
