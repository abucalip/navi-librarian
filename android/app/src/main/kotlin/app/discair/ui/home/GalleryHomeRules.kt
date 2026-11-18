package app.discair.ui.home

import app.discair.model.RadioPlay
import app.discair.model.RadioStation
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * The pure rules behind Gallery's Home (docs/archive/completed/GALLERY_THEME.md section 9, mockup gallery/pages/home): the pager label, the catalogue line over the hero,
 * the words for when a station was last heard, and the Radio section's rows. No Compose here, so each rule has a unit test.
 */
object GalleryHomeRules {
    const val HERO_DP = 246
    const val STATION_DP = 76
    const val PLAYED_SHOWN = 2
    const val STATIONS_SHOWN = 4
    const val PLAYS_SHOWN = 2

    /** "01 / 12": the pager's label, both numbers at least two digits. */
    fun pagerLabel(index: Int, count: Int): String = "%02d / %02d".format(index + 1, count)

    /** The catalogue line over the title of the hero. */
    fun eyebrow(tab: FlowHomeRules.Tab): String = when (tab) {
        FlowHomeRules.Tab.Picks -> "Pick for tonight"
        FlowHomeRules.Tab.New -> "New in your library"
        FlowHomeRules.Tab.Played -> "Recently played"
    }

    /** "Bark Psychosis, 1994": the artist and the year, each only when known. */
    fun by(artist: String, year: Int?): String = listOfNotNull(artist.ifBlank { null }, year?.toString()).joinToString(", ")

    /** "Post-rock · not in your library": the genre (picks only) and the owned state. */
    fun status(tab: FlowHomeRules.Tab, genre: String?, owned: Boolean): String {
        val state = when {
            tab == FlowHomeRules.Tab.Picks -> "not in your library"
            owned -> "in your library"
            else -> "not in your library"
        }
        return listOfNotNull(genre?.takeIf { it.isNotBlank() }, state).joinToString(" · ")
    }

    /** "Today", "Yesterday", a weekday inside the last week, else "2 Nov"; "" when never heard. [heardAt] is epoch seconds. */
    fun lastHeard(heardAt: Double?, now: Instant, zone: ZoneId = ZoneId.systemDefault()): String {
        if (heardAt == null) return ""
        val day = Instant.ofEpochMilli((heardAt * 1000).toLong()).atZone(zone).toLocalDate()
        val ago = java.time.temporal.ChronoUnit.DAYS.between(day, now.atZone(zone).toLocalDate())
        return when {
            ago <= 0 -> "Today"
            ago == 1L -> "Yesterday"
            ago < 7 -> day.dayOfWeek.getDisplayName(java.time.format.TextStyle.FULL, Locale.getDefault())
            else -> DateTimeFormatter.ofPattern("d MMM", Locale.getDefault()).format(day)
        }
    }

    /** One station plate: the station, when it was last heard (words) and whether that was today (drawn in the accent). */
    data class Plate(val station: RadioStation, val heard: String, val today: Boolean)

    /** The first [STATIONS_SHOWN] stations with their last-heard words; the newest play of a station (by name) decides. */
    fun plates(stations: List<RadioStation>, plays: List<RadioPlay>, now: Instant, zone: ZoneId = ZoneId.systemDefault()): List<Plate> =
        stations.take(STATIONS_SHOWN).map { s ->
            val at = plays.filter { it.stationName == s.name }.mapNotNull { it.heardAt }.maxOrNull()
            val words = lastHeard(at, now, zone)
            Plate(s, words, words == "Today")
        }

    /** What sits at the end of a "Heard on" row. */
    enum class Trailing { InLibrary, Requested, Get, None }

    fun trailing(play: RadioPlay): Trailing = when {
        play.inLibrary -> Trailing.InLibrary
        play.grabbed -> Trailing.Requested
        play.hasArtist -> Trailing.Get
        else -> Trailing.None
    }

    /** The newest [PLAYS_SHOWN] plays, newest first by time heard (the server's order is kept for plays with no time). */
    fun newestPlays(plays: List<RadioPlay>): List<RadioPlay> =
        plays.withIndex().sortedWith(compareByDescending<IndexedValue<RadioPlay>> { it.value.heardAt ?: Double.NEGATIVE_INFINITY }.thenBy { it.index })
            .map { it.value }.take(PLAYS_SHOWN)

    /** "Heard on FIP this morning": the newest play's station and when; older than yesterday it names the date. */
    fun heardHeading(play: RadioPlay?, now: Instant, zone: ZoneId = ZoneId.systemDefault()): String {
        if (play == null) return "Heard on radio"
        val station = play.stationName.ifBlank { null }
        val on = if (station != null) "Heard on $station" else "Heard on radio"
        val at = play.heardAt ?: return on
        val time = Instant.ofEpochMilli((at * 1000).toLong()).atZone(zone)
        val ago = java.time.temporal.ChronoUnit.DAYS.between(time.toLocalDate(), now.atZone(zone).toLocalDate())
        return when {
            ago <= 0 -> on + when {
                time.hour < 12 -> " this morning"
                time.hour < 18 -> " this afternoon"
                else -> " this evening"
            }
            ago == 1L -> "$on yesterday"
            else -> on + ", " + lastHeard(at, now, zone)
        }
    }

    /** "Cocteau Twins · 08:42": the artist and the time heard, each only when known. */
    fun playLine(play: RadioPlay, zone: ZoneId = ZoneId.systemDefault()): String {
        val time = play.heardAt?.let { DateTimeFormatter.ofPattern("HH:mm").format(Instant.ofEpochMilli((it * 1000).toLong()).atZone(zone)) }
        return listOfNotNull(play.artist?.takeIf { it.isNotBlank() }, time).joinToString(" · ")
    }

    /** The initials of a station with no logo: a short single word whole ("FIP", "KEXP"), a longer one its first two letters, several words their first letters ("Radio Paradise" gives "RP"). */
    fun initials(name: String): String {
        val words = name.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        return when {
            words.isEmpty() -> ""
            words.size == 1 -> (if (words[0].length <= 4) words[0] else words[0].take(2)).uppercase()
            else -> (words[0].take(1) + words[1].take(1)).uppercase()
        }
    }

    /** "1,284 albums · 312 artists · 7 new this month": the parts that are known, never a zero for an unknown. */
    fun libraryLine(hero: HeroFigures?, artists: Int?): String {
        val parts = ArrayList<String>()
        if (hero != null) parts += DashboardRules.formatCount(hero.count) + (if (hero.count == 1) " album" else " albums")
        if (artists != null) parts += DashboardRules.formatCount(artists) + (if (artists == 1) " artist" else " artists")
        if (hero != null) parts += "${hero.added30} new this month"
        return if (parts.isEmpty()) "Library stats" else parts.joinToString(" · ")
    }

    /** What a screen says when there is no listening yet (frame 6). */
    const val NO_LISTENING = "Play a few albums and the artists you come back to are hung here."

    /** An artist's line under the name: "5 albums"; null when the count is not known. */
    fun albumCount(n: Int?): String? = n?.let { "$it " + if (it == 1) "album" else "albums" }
}
