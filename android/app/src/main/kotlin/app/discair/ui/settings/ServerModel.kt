package app.discair.ui.settings

import app.discair.model.JobRun
import app.discair.model.JobStatus
import app.discair.model.ServerCapabilities
import app.discair.model.ServerReads
import app.discair.model.ServiceCheck
import app.discair.model.ServiceId

/*
 * The pure half of the Server screen (docs/redesign.md 8.2 and 6.2, step A7): the state of each connected service, the summary
 * sentence and the server-activity rows, built from what the screen read. Nothing here touches Compose or the network.
 *
 * Rules carried over from the Mac (6.2): when the Librarian does not answer, everything it would report is Unknown, not failed;
 * Navidrome keeps its own state from the phone's direct check; a configured service that has not been tested is Unknown, not
 * working; the phone only reads, so there is no edit here.
 */

enum class ServerTone { Success, Warning, Danger, Info, Neutral }

/** A state is always a word and a tone; the screen adds the icon, so colour never carries it alone. */
data class StatusWord(val word: String, val tone: ServerTone) {
    val failing: Boolean get() = tone == ServerTone.Danger
    val working: Boolean get() = tone == ServerTone.Success

    companion object {
        val Connected = StatusWord("Connected", ServerTone.Success)
        val NotSetUp = StatusWord("Not set up", ServerTone.Neutral)
        val Unknown = StatusWord("Unknown", ServerTone.Neutral)
        val NoAnswer = StatusWord("No answer", ServerTone.Danger)
        val NotLoaded = StatusWord("Not loaded", ServerTone.Info)
        val Done = StatusWord("Done", ServerTone.Success)
        val Paused = StatusWord("Paused", ServerTone.Info)
        val NotUpdating = StatusWord("Not updating", ServerTone.Warning)
        fun rejected(noun: String) = StatusWord("$noun rejected", ServerTone.Danger)
        fun loaded(coverage: String) = StatusWord("Loaded", ServerTone.Success).let { if (coverage.isBlank()) it else it.copy(word = "Loaded · $coverage") }
    }
}

/** One service row: name, role in a few words and its state. [required] services that are not set up count as needing attention. */
data class ServiceRow(val id: ServiceId, val name: String, val role: String, val status: StatusWord, val required: Boolean = true) {
    val needsAttention: Boolean get() = status.failing || (status == StatusWord.NotSetUp && required)
}

/** A server-activity row: a job, its state word and one line. */
data class ActivityRow(val id: String, val name: String, val status: StatusWord, val line: String)

enum class SummaryKind { Working, Attention, Unreachable }

data class ServerSummary(val kind: SummaryKind, val title: String, val detail: String) {
    val tone: ServerTone get() = when (kind) {
        SummaryKind.Working -> ServerTone.Success
        SummaryKind.Attention -> ServerTone.Warning
        SummaryKind.Unreachable -> ServerTone.Danger
    }
}

data class ServerView(val summary: ServerSummary, val services: List<ServiceRow>, val activity: List<ActivityRow>) {
    val attention: List<ServiceRow> get() = services.filter { it.needsAttention }
}

object ServerRules {
    /** The state of a service the Librarian tests. [configured] is null when its settings were not read. */
    fun testedState(test: ServiceCheck?, configured: Boolean?, noun: String): StatusWord {
        if (configured == false) return StatusWord.NotSetUp
        if (test == null) return StatusWord.Unknown // configured or unread, and not tested: not known to work
        if (test.ok) return StatusWord.Connected
        return when (test.status) {
            "not_configured" -> StatusWord.NotSetUp
            "authentication_failed" -> StatusWord.rejected(noun)
            "not_found" -> StatusWord.rejected("Username")
            else -> StatusWord.NoAnswer
        }
    }

    fun serviceRows(r: ServerReads): List<ServiceRow> {
        val up = r.librarianReachable
        fun viaLibrarian(s: StatusWord) = if (up) s else StatusWord.Unknown
        val navidrome = when {
            up && r.navidromeViaLibrarian != null -> if (r.navidromeViaLibrarian) StatusWord.Connected else StatusWord.NoAnswer
            r.navidromeDirect != null -> if (r.navidromeDirect) StatusWord.Connected else StatusWord.NoAnswer
            else -> StatusWord.Unknown
        }
        val listenBrainzConfigured = r.listenBrainzConfigured ?: r.capabilities?.listenBrainzConnected
        val musicBrainz = r.capabilities?.let { c ->
            if (c.graphCoverage == "none") StatusWord.NotLoaded else StatusWord.loaded(c.graphCoverage)
        } ?: StatusWord.Unknown
        return listOf(
            ServiceRow(ServiceId.Librarian, "Librarian", "Picks, downloads, insights", if (up) StatusWord.Connected else StatusWord.NoAnswer),
            ServiceRow(ServiceId.Navidrome, "Navidrome", "Library and playback", navidrome),
            ServiceRow(ServiceId.Slskd, "slskd", "Downloads", viaLibrarian(testedState(r.tests[ServiceId.Slskd], r.slskdConfigured, "Key"))),
            ServiceRow(ServiceId.LastFm, "Last.fm", "Listening history", viaLibrarian(testedState(r.tests[ServiceId.LastFm], r.lastFmConfigured, "Key"))),
            ServiceRow(ServiceId.ListenBrainz, "ListenBrainz", "Taste, popularity", viaLibrarian(testedState(r.tests[ServiceId.ListenBrainz], listenBrainzConfigured, "Token"))),
            ServiceRow(ServiceId.MusicBrainz, "MusicBrainz data", "Paths", viaLibrarian(musicBrainz)),
        )
    }

    fun summary(rows: List<ServiceRow>, r: ServerReads, checked: String): ServerSummary {
        if (!r.librarianReachable) return ServerSummary(
            SummaryKind.Unreachable, "Can't reach Librarian",
            "Picks, downloads and insights are paused. Playback from Navidrome is not affected. $checked",
        )
        val attention = rows.filter { it.needsAttention }
        return when (attention.size) {
            0 -> ServerSummary(SummaryKind.Working, "Everything is working", checked)
            1 -> ServerSummary(SummaryKind.Attention, "One service needs attention", "${attention[0].name}: ${attention[0].status.word}. $checked")
            else -> ServerSummary(SummaryKind.Attention, "${attention.size} services need attention", attention.joinToString(", ") { it.name } + ". $checked")
        }
    }

    /** "Refreshed 2 hours ago · next in 4 hours", or the failure; Unknown when the route was not read. */
    fun lensRow(job: JobStatus?, nowMillis: Long): ActivityRow {
        if (job == null || (job.status == null && job.lastGood == null)) {
            return ActivityRow("lenses", "Insight lenses", StatusWord.NotLoaded, "Not read yet")
        }
        val finished = job.lastGood?.finishedAt
        val refreshed = finished?.let { "Refreshed ${ago(nowMillis, it)}" } ?: "Not refreshed yet"
        val next = job.retryAfter?.let { if (it <= 0) "next due now" else "next in ${duration(it)}" }
        val line = listOfNotNull(refreshed, next).joinToString(" · ")
        return when {
            job.status?.state == "failed" -> ActivityRow("lenses", "Insight lenses", StatusWord.NotUpdating, "The last refresh failed. $line")
            job.running -> ActivityRow("lenses", "Insight lenses", StatusWord.Done, "Refreshing now · $line")
            else -> ActivityRow("lenses", "Insight lenses", StatusWord.Done, line)
        }
    }

    /** Artist popularity is filled by hand only, so the row says how many artists are left; the phone does not start the fill. */
    fun popularityRow(job: JobStatus?, nowMillis: Long): ActivityRow {
        val name = "Artist popularity"
        if (job == null) return ActivityRow("popularity", name, StatusWord.NotLoaded, "Not read yet")
        val newest: JobRun = job.status ?: job.lastGood
            ?: return ActivityRow("popularity", name, StatusWord.Paused, "No figures yet · runs only when you ask")
        val pending = (newest.progress["pending"] ?: job.lastGood?.progress?.get("pending") ?: 0.0).toInt()
        val left = "${app.discair.ui.common.ChartRules.formatCount(pending.toDouble())} artists left"
        if (job.running) return ActivityRow("popularity", name, StatusWord.Paused, "Filling now" + if (pending > 0) " · $left" else "")
        return when {
            newest.state == "failed" -> ActivityRow(
                "popularity", name, StatusWord.NotUpdating,
                "The last fill failed" + (newest.error?.let { ": $it" } ?: "") + ". Earlier figures are kept.",
            )
            newest.state == "queued" || pending > 0 -> ActivityRow("popularity", name, StatusWord.Paused, "$left · runs only when you ask")
            else -> ActivityRow("popularity", name, StatusWord.Done, "Figures are up to date" + (newest.finishedAt?.let { " · filled ${ago(nowMillis, it)}" } ?: ""))
        }
    }

    fun build(r: ServerReads, checkedClock: String): ServerView {
        val rows = serviceRows(r)
        // Jobs live on the Librarian: with it down they are not known, so they are left out rather than shown as failed.
        val activity = if (r.librarianReachable) listOf(lensRow(r.lenses, r.checkedAtMillis), popularityRow(r.popularity, r.checkedAtMillis)) else emptyList()
        return ServerView(summary(rows, r, "Checked at $checkedClock."), rows, activity)
    }

    /** "35 minutes", "1 minute", "4 hours". */
    fun duration(seconds: Double): String {
        val minutes = maxOf(1, Math.round(seconds / 60.0).toInt())
        if (minutes < 90) return "$minutes minute" + if (minutes == 1) "" else "s"
        val hours = Math.round(minutes / 60.0).toInt()
        return "$hours hour" + if (hours == 1) "" else "s"
    }

    /** Relative only under a day (section 3): "2 hours ago"; older is a date. [finishedSeconds] is Unix seconds. */
    fun ago(nowMillis: Long, finishedSeconds: Double): String {
        val seconds = (nowMillis / 1000.0 - finishedSeconds).coerceAtLeast(0.0)
        if (seconds < 90) return "just now"
        if (seconds >= 86_400) {
            val date = java.time.Instant.ofEpochSecond(finishedSeconds.toLong()).atZone(java.time.ZoneOffset.UTC).toLocalDate()
            return "on ${date.dayOfMonth} ${date.month.getDisplayName(java.time.format.TextStyle.FULL, java.util.Locale.ENGLISH)}"
        }
        return duration(seconds) + " ago"
    }
}
