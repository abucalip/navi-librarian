package app.discair.ui

import app.discair.model.ActiveYears
import app.discair.model.AlbumPage
import app.discair.model.ApiJson
import app.discair.model.ArtistPage
import app.discair.model.PathYears
import app.discair.model.SharedAlbum
import app.discair.model.parsePaths
import app.discair.ui.common.IndexDatum
import app.discair.ui.common.IndexPagesRules
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** docs/INDEX_THEME.md step I3: the words and numbers of Index's Album, Artist, Genre and Paths, and the I0 fields they read (section 11a.3). */
class IndexPagesRulesTest {
    @Test fun theAlbumBarSaysItsPlaceInTheLibraryOnlyWhenTheServerGaveIt() {
        assertEquals("Album 0418 / 1284", IndexPagesRules.albumCatalogue(true, 418, 1284))
        assertEquals("Album 12345 / 20000", IndexPagesRules.albumCatalogue(true, 12345, 20000))
        assertEquals("Album", IndexPagesRules.albumCatalogue(true, null, null))
        assertEquals("Album", IndexPagesRules.albumCatalogue(true, 0, 10))
        assertEquals("Not in your library", IndexPagesRules.albumCatalogue(false, 3, 10))
    }

    @Test fun lengthsReadAsMinutesAndSecondsAndHoursPastAnHour() {
        assertEquals("44:12", IndexPagesRules.length(44 * 60 + 12))
        assertEquals("1:19:04", IndexPagesRules.length(3600 + 19 * 60 + 4))
        assertNull(IndexPagesRules.length(0))
        assertEquals("4:10", IndexPagesRules.clock(250))
    }

    @Test fun theNumeralIsThePlayingSongOrElseTheSongCount() {
        assertEquals(IndexPagesRules.Numeral("05", "/ 10", "Playing", true), IndexPagesRules.albumNumeral(4, 10))
        assertEquals(IndexPagesRules.Numeral("10", null, "Songs", false), IndexPagesRules.albumNumeral(null, 10))
        assertEquals(IndexPagesRules.Numeral("01", null, "Song", false), IndexPagesRules.albumNumeral(null, 1))
        assertEquals(IndexPagesRules.Numeral("10", null, "Songs", false), IndexPagesRules.albumNumeral(12, 10))
        assertNull(IndexPagesRules.albumNumeral(null, 0))
    }

    @Test fun numbersAndLetters() {
        assertEquals("01", IndexPagesRules.number(0)); assertEquals("12", IndexPagesRules.number(11))
        assertEquals("A", IndexPagesRules.letter(0)); assertEquals("C", IndexPagesRules.letter(2)); assertEquals("AA", IndexPagesRules.letter(26))
        assertEquals("0031", IndexPagesRules.pad4(31))
    }

    @Test fun theAlbumDataListLeavesOutWhatIsUnknown() {
        assertEquals(
            listOf(IndexDatum("Artist", "Khruangbin"), IndexDatum("Year", "2020"), IndexDatum("Length", "44:12"), IndexDatum("Format", "FLAC")),
            IndexPagesRules.albumRows("Khruangbin", 2020, 2652, "FLAC", null),
        )
        assertEquals(listOf(IndexDatum("Artist", "X"), IndexDatum("Genre", "Dream pop")), IndexPagesRules.albumRows("X", null, 0, " ", "Dream pop"))
        assertEquals(
            listOf(IndexDatum("Artist", "Cocteau Twins"), IndexDatum("Year", "1990"), IndexDatum("Genre", "Dream pop"), IndexDatum("Songs", "10")),
            IndexPagesRules.missingAlbumGrid("Cocteau Twins", 1990, "Dream pop", 10),
        )
        assertEquals(listOf(IndexDatum("Artist", "Y")), IndexPagesRules.missingAlbumGrid("Y", null, null, 0))
    }

    @Test fun activeYearsReadAsARangeOrSince() {
        assertEquals("1967 – 2007", IndexPagesRules.activeYears(ActiveYears(1967, 2007, true)))
        assertEquals("Since 1994", IndexPagesRules.activeYears(ActiveYears(1994, null, false)))
        assertEquals("From 1961", IndexPagesRules.activeYears(ActiveYears(1961, null, true)))
        assertEquals("1970", IndexPagesRules.activeYears(ActiveYears(1970, 1970, true)))
        assertNull(IndexPagesRules.activeYears(null))
        assertNull(IndexPagesRules.activeYears(ActiveYears(null, 2000, true)))
    }

    @Test fun theArtistDataListSaysOwnedOfTotalAndPlaysOnlyForTheLibrary() {
        assertEquals(
            listOf(IndexDatum("Genre", "Spiritual jazz"), IndexDatum("Owned", "5 of 9"), IndexDatum("Plays", "212"), IndexDatum("Active", "1967 – 2007")),
            IndexPagesRules.artistRows("Spiritual jazz", 5, 9, 5, true, 212, ActiveYears(1967, 2007, true)),
        )
        // No provider count: the library's own album count; zero plays is still said for an artist in the library.
        assertEquals(listOf(IndexDatum("Owned", "3"), IndexDatum("Plays", "0")), IndexPagesRules.artistRows(null, null, null, 3, true, 0, null))
        // Not in the library: Owned None in accent, no plays line.
        assertEquals(listOf(IndexDatum("Owned", "None", accent = true)), IndexPagesRules.artistRows(null, null, null, 0, false, 0, null))
        assertEquals("1,284", IndexPagesRules.count(1284))
        assertEquals("4 to get", IndexPagesRules.toGet(4)); assertNull(IndexPagesRules.toGet(0))
    }

    @Test fun pathsLinesAndSharedAlbums() {
        assertEquals("7 kinds · 4 steps", IndexPagesRules.pathsLine(7, 4))
        assertEquals("5 kinds", IndexPagesRules.pathsLine(5, null))
        assertEquals("1 kind · 1 step", IndexPagesRules.pathsLine(1, 1))
        assertEquals("Studio crew · step 01 / 04", IndexPagesRules.stepLine("Studio crew", 0, 4))
        assertEquals("1969 · In library", IndexPagesRules.stepEyebrow(1969, true))
        assertEquals("Not in library", IndexPagesRules.stepEyebrow(null, false))
        assertEquals("1968 – 1971", IndexPagesRules.withYears(PathYears(1968, 1971)))
        assertEquals("1969", IndexPagesRules.withYears(PathYears(1969, 1969)))
        assertEquals("2 of 4", IndexPagesRules.sharedOwned(listOf(SharedAlbum("a", 1971, true), SharedAlbum("b", 1969, true), SharedAlbum("c", 1974, false), SharedAlbum("d", null, false))))
        assertNull(IndexPagesRules.sharedOwned(null)); assertNull(IndexPagesRules.sharedOwned(emptyList()))
        assertEquals("Played together", IndexPagesRules.reasonWord("sideman_on", "Sideman"))
        assertEquals("Production credit", IndexPagesRules.reasonWord("crew_on", "Studio crew"))
        assertEquals("Label", IndexPagesRules.reasonWord("something_new", "Label"))
        assertEquals("Miles Davis led Karma, a release.", IndexPagesRules.reasonSentence("Miles Davis", "led Karma, a release"))
        assertEquals("Alfred Lion has a credit.", IndexPagesRules.reasonSentence("Go", "Alfred Lion has a credit."))
        assertEquals("", IndexPagesRules.reasonSentence("X", " "))
    }

    // ---------------------------------------------------------------- the I0 fields (SEARCH_CONTRACT.md, SERVER_V2_CONTRACT.md)

    @Test fun theAlbumSectionCarriesItsLibraryPlace() {
        val page = ApiJson.decodeFromString(AlbumPage.serializer(), """{"sections":{"album":{"available":true,"album":{"name":"Mordechai","artist":"Khruangbin","owned":true,"library_position":418,"library_total":1284}}}}""")
        assertEquals(418, page.sections.album.album?.libraryPosition); assertEquals(1284, page.sections.album.album?.libraryTotal)
        val old = ApiJson.decodeFromString(AlbumPage.serializer(), """{"sections":{"album":{"available":true,"album":{"name":"M","library_position":null,"library_total":null}}}}""")
        assertNull(old.sections.album.album?.libraryPosition)
    }

    @Test fun theArtistPageCarriesPlaysYearsAndAlbumCounts() {
        val page = ApiJson.decodeFromString(
            ArtistPage.serializer(),
            """{"sections":{"artist":{"available":true,"artist":{"name":"Alice Coltrane","owned":true,"album_count":5,"play_count":212,"active_years":{"begin":1967,"end":2007,"ended":true}}},
               "albums":{"available":true,"items":[{"name":"x"}],"owned_count":5,"album_count":9}}}""",
        )
        val a = page.sections.artist.artist!!
        assertEquals(212, a.playCount); assertEquals(ActiveYears(1967, 2007, true), a.activeYears)
        assertEquals(5, page.sections.albums.ownedCount); assertEquals(9, page.sections.albums.albumCount)
        // An older server: nothing new, and the elements hide.
        val old = ApiJson.decodeFromString(ArtistPage.serializer(), """{"sections":{"artist":{"available":true,"artist":{"name":"A","active_years":null}}}}""")
        assertNull(old.sections.artist.artist!!.playCount); assertNull(old.sections.artist.artist!!.activeYears); assertNull(old.sections.albums.ownedCount)
    }

    @Test fun aSidemanStopCarriesItsSharedAlbumsAndYears() {
        val body = """{"kind":"sideman_to_leader","status":"ok","stops":[
            {"entity":{"canonical_name":"Pharoah Sanders","type":"person","owned":true,"mbid":"m1"},"reason_count":1,
             "reasons":[{"code":"sideman_on","text":"Alice Coltrane played on Karma."}],
             "presentation":{"years":{"from":1968,"to":1971},"shared_albums":[{"album":"Karma","year":1969,"owned":true},{"album":"Elevation","year":null,"owned":false}]}},
            {"entity":{"canonical_name":"Rashied Ali","type":"person","owned":false},"reason_count":1,"reasons":[{"code":"sideman_on","text":"On a record."}]}]}"""
        val stops = parsePaths(body).stops
        assertEquals(PathYears(1968, 1971), stops[0].years)
        assertEquals(listOf(SharedAlbum("Karma", 1969, true), SharedAlbum("Elevation", null, false)), stops[0].sharedAlbums)
        assertNull(stops[1].years); assertNull(stops[1].sharedAlbums)
    }
}
