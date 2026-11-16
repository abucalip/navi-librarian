package app.discair.ui

import app.discair.model.AcquisitionJob
import app.discair.ui.common.ConfirmSpecs
import app.discair.ui.downloads.GalleryDownloadsRules as D
import app.discair.ui.settings.GallerySettingsRules as S
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** Step G6 of docs/GALLERY_THEME.md: the words and choices behind Gallery's Downloads, Server, Settings, Appearance and confirmation sheets. */
class GalleryStatusRulesTest {
    private fun job(status: String, percent: Double? = null) = AcquisitionJob(
        "A", "B", status, 1.0, null,
        JsonObject(if (percent == null) emptyMap() else mapOf("live_progress" to JsonObject(mapOf("percent" to JsonPrimitive(percent))))),
    )

    @Test fun theCatalogueLineCountsWhatIsUnderWayAndWhatNeedsTheOwner() {
        assertEquals("2 in progress · 1 needs you", D.eyebrow(listOf(job("downloading"), job("importing"), job("download_failed"))))
        assertEquals("1 in progress", D.eyebrow(listOf(job("downloading"), job("imported"))))
        assertEquals("2 need you", D.eyebrow(listOf(job("no_matches"), job("download_failed"))))
        assertEquals("Nothing in progress", D.eyebrow(listOf(job("imported"))))
        assertEquals("Nothing in progress", D.eyebrow(emptyList()))
    }

    @Test fun theProgressLineNamesSongsAndSaysNothingWithoutFigures() {
        assertEquals("64%", D.progress(job("downloading", percent = 64.0)))
        assertNull(D.progress(job("downloading")))
    }

    @Test fun theStateLineJoinsTheStatusTheFiguresAndTheArrival() {
        assertEquals("Downloading · 64% · 7 of 9 songs", D.stateLine("Downloading", "64% · 7 of 9 songs", null))
        assertEquals("In your library · arrived 21:14", D.stateLine("In your library", null, "21:14"))
    }

    @Test fun theTrackerCountsTheStepUnderWayAsReachedAndMarksAFailedOne() {
        assertEquals(2 to -1, D.tracker(job("downloading")))
        assertEquals(4 to -1, D.tracker(job("imported")))
        assertEquals(2 to 2, D.tracker(job("download_complete_move_failed")))
        assertEquals(0 to 0, D.tracker(job("no_matches")))
    }

    @Test fun theServerAndSettingsPagesHaveTheirCatalogueLines() {
        assertEquals("Checked at 14:32", S.checkedLine("14:32"))
        assertEquals("Discair 1.3", S.versionLine("1.3"))
        assertEquals("Discair", S.versionLine(null))
        assertEquals("Discair", S.versionLine(" "))
    }

    @Test fun appearanceShowsDayAndNightWhenFollowingThePhoneAndOneGroupOtherwise() {
        assertEquals(listOf("Day" to true, "Night" to false), S.slots(true))
        assertEquals(listOf("Theme" to null), S.slots(false))
    }

    @Test fun theConfirmationsNameTheirPageOverTheQuestion() {
        assertEquals("Downloads", ConfirmSpecs.dismissJob("Hats").eyebrow)
        assertEquals("Downloads", ConfirmSpecs.dismissImports(2).eyebrow)
        assertEquals("Equalizer", ConfirmSpecs.resetEqualizer().eyebrow)
        assertEquals("Settings", ConfirmSpecs.signOut().eyebrow)
    }
}
