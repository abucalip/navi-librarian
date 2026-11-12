package app.discair.ui.downloads

import app.discair.Check
import app.discair.model.AcquisitionJob
import app.discair.net.ConnectionFailure
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** A8 pure rules: tracker position, Downloads summary, Library count line, Settings server line. */
class DownloadsRulesTest {
    private fun job(status: String, updated: Double? = null, percent: Double? = null) = AcquisitionJob(
        "A", "B", status, 1.0, updated,
        JsonObject(if (percent == null) emptyMap() else mapOf("live_progress" to JsonObject(mapOf("percent" to JsonPrimitive(percent))))),
    )

    @Test fun everyStatusTheAppKnowsLandsOnAStep() {
        assertEquals(DownloadsRules.Step(0), DownloadsRules.step("searching"))
        assertEquals(DownloadsRules.Step(1), DownloadsRules.step("Downloading"))
        assertEquals(DownloadsRules.Step(2), DownloadsRules.step("importing"))
        assertEquals(DownloadsRules.Step(4), DownloadsRules.step("imported"))
    }

    @Test fun failuresMarkTheStepThatFailed() {
        assertEquals(DownloadsRules.Step(0, true), DownloadsRules.step("no_matches"))
        assertEquals(DownloadsRules.Step(1, true), DownloadsRules.step("download_failed"))
        assertEquals(DownloadsRules.Step(2, true), DownloadsRules.step("download_complete_move_failed"))
    }

    @Test fun anUnknownStatusIsNotCalledAFailure() {
        assertEquals(DownloadsRules.Step(0, false), DownloadsRules.step("something_new"))
    }

    @Test fun onlyADownloadingJobHasAFill() {
        assertEquals(0.64f, DownloadsRules.fill(job("downloading", percent = 64.0)), 0.001f)
        assertEquals(0f, DownloadsRules.fill(job("importing", percent = 64.0)), 0f)
        assertEquals(0f, DownloadsRules.fill(job("downloading")), 0f)
    }

    @Test fun summaryCountsWayArrivedAndNeedsYou() {
        val jobs = listOf(job("downloading"), job("imported", updated = 2000.0), job("imported", updated = 500.0), job("no_matches"))
        assertEquals("1 on its way · 1 arrived today · 1 needs you", DownloadsRules.summary(jobs, 1000.0))
        assertEquals("Nothing on its way", DownloadsRules.summary(emptyList(), 1000.0))
        assertEquals("2 on their way", DownloadsRules.summary(listOf(job("queued"), job("importing")), 0.0))
    }

    @Test fun libraryCountLineHasSeparatorsAndSingular() {
        assertEquals("1,284 albums · A to Z", LibraryText.countLine("albums", 1284, "A to Z"))
        assertEquals("1 artist · A to Z", LibraryText.countLine("artists", 1, "A to Z"))
        assertEquals("Loading…", LibraryText.countLine("albums", null, "A to Z"))
    }

    @Test fun serverLineSaysWhichServerNeedsAttention() {
        val bad = Check.Failed(ConnectionFailure.Unreachable)
        assertEquals("All working", SettingsRules.serverLine(Check.Ok, Check.Ok).text)
        assertEquals("Librarian needs attention", SettingsRules.serverLine(bad, Check.Ok).text)
        assertEquals("Navidrome needs attention", SettingsRules.serverLine(Check.Ok, bad).text)
        assertEquals(SettingsRules.Tone.Danger, SettingsRules.serverLine(bad, bad).tone)
        assertEquals("Checking…", SettingsRules.serverLine(Check.Pending, Check.Ok).text)
        assertFalse(SettingsRules.serverLine(Check.Idle, Check.Idle).tone == SettingsRules.Tone.Success)
        assertTrue(SettingsRules.serverLine(Check.Idle, Check.Idle).text.startsWith("Not checked"))
    }
}
