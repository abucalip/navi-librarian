package app.discair.ui.downloads

import app.discair.Check
import app.discair.model.AcquisitionJob

/**
 * Pure rules for the A8 restyle (docs/redesign.md 8.2): where a record sits on the four-step tracker, the line under the
 * Downloads title, the count line under Library's tabs and the state line on Settings' Server row. Nothing here draws.
 */
object DownloadsRules {
    /** [current] is the index of the step in progress (4 = all done); [failed] marks that step as failed. */
    data class Step(val current: Int, val failed: Boolean = false)

    private val found = setOf("searching", "requested", "queued_unconfirmed", "queue_uncertain", "source_switching", "skip_requested", "retry_requested")
    private val downloading = setOf("queued", "downloading", "monitoring", "recovery_started")
    private val importing = setOf("download_complete_waiting_for_folder", "importing", "review_required")
    private val failedFound = setOf("no_matches", "queue_failed", "settings_required", "slskd_error")
    private val failedDownload = setOf(
        "download_failed", "source_switch_failed", "monitor_error", "monitor_timeout", "monitor_recovery_failed", "recovery_unavailable", "error", "failed",
    )
    private val failedImport = setOf("download_complete_move_failed")

    /** Tracker position for a server status. An unknown status sits on the first step, not failed: it is never called a failure it did not report. */
    fun step(status: String): Step {
        val key = status.lowercase()
        return when (key) {
            in downloading -> Step(1)
            in importing -> Step(2)
            "imported" -> Step(4)
            in failedFound -> Step(0, failed = true)
            in failedDownload -> Step(1, failed = true)
            in failedImport -> Step(2, failed = true)
            else -> Step(0)
        }
    }

    /** Fill of the current step, 0 to 1, from the live percentage; only a downloading record has one. */
    fun fill(job: AcquisitionJob): Float =
        if (step(job.status).current == 1 && !step(job.status).failed) ((job.progress?.percent ?: 0.0) / 100.0).toFloat() else 0f

    /** "1 on its way · 1 arrived today". [dayStartSeconds] is local midnight as epoch seconds. */
    fun summary(jobs: List<AcquisitionJob>, dayStartSeconds: Double): String {
        val way = jobs.count { it.isActive }
        val arrived = jobs.count { it.isImported && (it.updatedAt ?: it.createdAt) >= dayStartSeconds }
        val needs = jobs.count { step(it.status).failed }
        val parts = listOfNotNull(
            if (way > 0) (if (way == 1) "1 on its way" else "$way on their way") else null,
            if (arrived > 0) "$arrived arrived today" else null,
            if (needs > 0) "$needs need${if (needs == 1) "s" else ""} you" else null,
        )
        return if (parts.isEmpty()) "Nothing on its way" else parts.joinToString(" · ")
    }
}

/** The count and order line under Library's tabs: "733 artists · A to Z". */
object LibraryText {
    fun countLine(noun: String, total: Int?, order: String): String =
        if (total == null) "Loading…" else "%,d %s · %s".format(total, if (total == 1) noun.removeSuffix("s") else noun, order)
}

/** The Server row's state line on Settings, from the two checks the screen already holds. */
object SettingsRules {
    enum class Tone { Success, Danger, Neutral }
    data class Line(val text: String, val tone: Tone)

    fun serverLine(librarian: Check, navidrome: Check): Line = when {
        librarian is Check.Failed && navidrome is Check.Failed -> Line("Can't reach either server", Tone.Danger)
        librarian is Check.Failed -> Line("Librarian needs attention", Tone.Danger)
        navidrome is Check.Failed -> Line("Navidrome needs attention", Tone.Danger)
        librarian == Check.Ok && navidrome == Check.Ok -> Line("All working", Tone.Success)
        librarian == Check.Pending || navidrome == Check.Pending -> Line("Checking…", Tone.Neutral)
        else -> Line("Not checked yet", Tone.Neutral)
    }
}
