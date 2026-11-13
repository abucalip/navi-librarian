package app.discair.ui.common

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.unit.dp

/**
 * The Flow and Soft Brut themes' icon set, taken from the icon symbols in their mockups (identical in both)
 * (the HTML files in `docs/design/android-art-themes/flow`, 24 by 24 viewBox). Most are 1.8 stroked, round-capped line
 * icons; the transport glyphs, the three dots and the filled heart are solid, as the mockups draw them.
 * Colour comes from the `Icon` tint.
 */
object ArtIcons {
    private fun build(name: String, paths: Array<out String>, filled: Boolean): ImageVector {
        val b = ImageVector.Builder(name, 24.dp, 24.dp, 24f, 24f)
        paths.forEach {
            val nodes = PathParser().parsePathString(it).toNodes()
            if (filled) b.addPath(nodes, fill = SolidColor(Color.Black))
            else b.addPath(
                nodes, fill = null, stroke = SolidColor(Color.Black), strokeLineWidth = 1.8f,
                strokeLineCap = StrokeCap.Round, strokeLineJoin = StrokeJoin.Round,
            )
        }
        return b.build()
    }

    private fun stroked(name: String, vararg paths: String) = build(name, paths, filled = false)
    private fun filled(name: String, vararg paths: String) = build(name, paths, filled = true)

    val Home = stroked("home",
            "M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z",
        )
    val Disc = stroked("disc",
            "M12 3l1.800 5.200L19 10l-5.200 1.800L12 17l-1.800-5.200L5 10l5.200-1.800zM18.500 16l.7 1.800 1.800.7-1.800.7-.7 1.800-.7-1.800-1.800-.7 1.800-.7z",
        )
    val Lib = stroked("lib",
            "M5 4v16M9.500 4v16M14 5l4.500 14.500",
        )
    val Search = stroked("search",
            "M4.5,11a6.5,6.5 0 1,0 13,0a6.5,6.5 0 1,0 -13,0",
            "M16 16l4.500 4.500",
        )
    val Play = filled("play",
            "M7 4.500v15l12.500-7.500z",
        )
    val Pause = filled("pause",
            "M7 5h3.500v14H7zM13.500 5H17v14h-3.500z",
        )
    val Next = filled("next",
            "M5 5v14l10-7zM17 5h2.500v14H17z",
        )
    val Previous = filled("prev",
            "M19 5v14L9 12zM4.500 5H7v14H4.500z",
        )
    val Download = stroked("dl",
            "M3.5,12a8.5,8.5 0 1,0 17,0a8.5,8.5 0 1,0 -17,0",
            "M12 7.500v8M8.500 12.500L12 16l3.500-3.500",
        )
    val Gear = stroked("gear",
            "M9,12a3,3 0 1,0 6,0a3,3 0 1,0 -6,0",
            "M12 2.500v3M12 18.500v3M2.500 12h3M18.500 12h3M5.300 5.300l2.100 2.100M16.600 16.600l2.100 2.100M5.300 18.700l2.100-2.100M16.600 7.400l2.100-2.100",
        )
    val More = filled("more",
            "M3.4,12a1.6,1.6 0 1,0 3.2,0a1.6,1.6 0 1,0 -3.2,0",
            "M10.4,12a1.6,1.6 0 1,0 3.2,0a1.6,1.6 0 1,0 -3.2,0",
            "M17.4,12a1.6,1.6 0 1,0 3.2,0a1.6,1.6 0 1,0 -3.2,0",
        )
    val Chevron = stroked("chev",
            "M9 5l7 7-7 7",
        )
    val Back = stroked("back",
            "M15 5l-7 7 7 7",
        )
    val Down = stroked("down",
            "M5 9l7 7 7-7",
        )
    val Radio = stroked("radio",
            "M5,8h14a2,2 0 0 1 2,2v8a2,2 0 0 1 -2,2h-14a2,2 0 0 1 -2,-2v-8a2,2 0 0 1 2,-2z",
            "M7 8l9-4",
            "M6,14a2.5,2.5 0 1,0 5,0a2.5,2.5 0 1,0 -5,0",
            "M14 12.500h4M14 15.500h4",
        )
    val Get = stroked("get",
            "M7 18a4.500 4.500 0 0 1-.6-8.960 6 6 0 0 1 11.700 1.500A3.800 3.800 0 0 1 17.500 18M12 11v8M9 16.500l3 3 3-3",
        )
    val Heart = stroked("heart",
            "M12 20s-7-4.300-7-9.500A4 4 0 0 1 12 8a4 4 0 0 1 7 2.500C19 15.700 12 20 12 20z",
        )
    val HeartFilled = filled("heart_filled",
            "M12 20s-7-4.300-7-9.500A4 4 0 0 1 12 8a4 4 0 0 1 7 2.500C19 15.700 12 20 12 20z",
        )
    val Bookmark = stroked("bookmark",
            "M7 4h10a1 1 0 0 1 1 1v15l-6-4-6 4V5a1 1 0 0 1 1-1z",
        )
    val BookmarkFilled = filled("bookmark_filled",
            "M7 4h10a1 1 0 0 1 1 1v15l-6-4-6 4V5a1 1 0 0 1 1-1z",
        )
    val Check = stroked("check",
            "M5 12.500l4.500 4.500L19 7.500",
        )
    val Close = stroked("close",
            "M6 6l12 12M18 6L6 18",
        )
    val Queue = stroked("queue",
            "M4 7h16M4 12h16M4 17h10",
        )
    val QueueAdd = stroked("qadd",
            "M4 7h12M4 12h12M4 17h7M18 14v6M15 17h6",
        )
    val Shuffle = stroked("shuffle",
            "M4 7h3l10 10h3M4 17h3l3-3M14 10l3-3h3M18 5l2 2-2 2M18 15l2 2-2 2",
        )
    val Repeat = stroked("repeat",
            "M5 11V9a2 2 0 0 1 2-2h11M16 4l3 3-3 3M19 13v2a2 2 0 0 1-2 2H6M8 20l-3-3 3-3",
        )
    val RepeatOne = stroked("repeat_one",
            "M5 11V9a2 2 0 0 1 2-2h11M16 4l3 3-3 3M19 13v2a2 2 0 0 1-2 2H6M8 20l-3-3 3-3",
            "M11,10l1.2,-0.8v5.3",
        )
    val Quote = stroked("quote",
            "M5 6h14v10H10l-4 3v-3H5z",
        )
    val Tune = stroked("tune",
            "M6 4v16M12 4v16M18 4v16",
            "M4,9a2,2 0 1,0 4,0a2,2 0 1,0 -4,0",
            "M10,15a2,2 0 1,0 4,0a2,2 0 1,0 -4,0",
            "M16,8a2,2 0 1,0 4,0a2,2 0 1,0 -4,0",
        )
    val Sun = stroked("sun",
            "M8,12a4,4 0 1,0 8,0a4,4 0 1,0 -8,0",
            "M12 3v2M12 19v2M3 12h2M19 12h2M5.600 5.600l1.400 1.400M17 17l1.400 1.400M5.600 18.400L7 17M17 7l1.400-1.400",
        )
    val Server = stroked("server",
            "M5.5,4h13a1.5,1.5 0 0 1 1.5,1.5v4a1.5,1.5 0 0 1 -1.5,1.5h-13a1.5,1.5 0 0 1 -1.5,-1.5v-4a1.5,1.5 0 0 1 1.5,-1.5z",
            "M5.5,13h13a1.5,1.5 0 0 1 1.5,1.5v4a1.5,1.5 0 0 1 -1.5,1.5h-13a1.5,1.5 0 0 1 -1.5,-1.5v-4a1.5,1.5 0 0 1 1.5,-1.5z",
            "M7.500 7.500h.01M7.500 16.500h.01",
        )
    val Swap = stroked("swap",
            "M4 8h13M14 5l3 3-3 3M20 16H7M10 13l-3 3 3 3",
        )
    val Wave = stroked("wave",
            "M4 12h2l2-6 3 12 3-9 2 5 1-2h3",
        )
    val Sort = stroked("sort",
            "M7 5v14M4 16l3 3 3-3M14 7h6M14 12h4M14 17h2",
        )
    val Plus = stroked("plus",
            "M12 5v14M5 12h14",
        )
    val Minus = stroked("minus",
            "M5 12h14",
        )
    val Paths = stroked("path",
            "M4,18a2,2 0 1,0 4,0a2,2 0 1,0 -4,0",
            "M16,6a2,2 0 1,0 4,0a2,2 0 1,0 -4,0",
            "M8 18h5a3 3 0 0 0 0-6h-2a3 3 0 0 1 0-6h5",
        )
    val Info = stroked("info",
            "M3.5,12a8.5,8.5 0 1,0 17,0a8.5,8.5 0 1,0 -17,0",
            "M12 11v5M12 8h.01",
        )
    val SignOut = stroked("out",
            "M10 5H5v14h5M14 8l4 4-4 4M18 12H9",
        )
    val Up = stroked("up",
            "M5 15l7-7 7 7",
        )
    val Warning = stroked("warning",
            "M12 4l9 16H3z",
            "M12 10v4M12 17h.01",
        )
    val Delete = stroked("delete",
            "M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13M10 11v6M14 11v6",
        )
    val Refresh = stroked("refresh",
            "M19 12a7 7 0 1 1-2.050-4.950M19 4v4h-4",
        )
    val Place = stroked("place",
            "M12 21s-6-5.500-6-11a6 6 0 0 1 12 0c0 5.500-6 11-6 11z",
            "M10,10a2,2 0 1,0 4,0a2,2 0 1,0 -4,0",
        )
    val Album = stroked("album",
            "M3,12a9,9 0 1,0 18,0a9,9 0 1,0 -18,0",
            "M9.500,12a2.500,2.500 0 1,0 5,0a2.500,2.500 0 1,0 -5,0",
        )
    val Photos = stroked("photos",
            "M5,5h14a1,1 0 0 1 1,1v12a1,1 0 0 1 -1,1h-14a1,1 0 0 1 -1,-1v-12a1,1 0 0 1 1,-1z",
            "M4 16l5-5 4 4 3-3 4 4M14.500 8.500h.01",
        )
    val MusicNote = stroked("music_note",
            "M9 18V6l10-2v12",
            "M5,18a2,2 0 1,0 4,0a2,2 0 1,0 -4,0",
            "M15,16a2,2 0 1,0 4,0a2,2 0 1,0 -4,0",
        )
}
