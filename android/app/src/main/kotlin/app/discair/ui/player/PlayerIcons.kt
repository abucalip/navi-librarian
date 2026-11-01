package app.discair.ui.player

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.unit.dp

/** Transport icons (Material path data), because the bundled icon set has only the core icons. */
object PlayerIcons {
    private fun icon(name: String, vararg paths: String): ImageVector {
        val b = ImageVector.Builder(name, 24.dp, 24.dp, 24f, 24f)
        paths.forEach { b.addPath(PathParser().parsePathString(it).toNodes(), fill = SolidColor(Color.Black)) }
        return b.build()
    }

    val Play = icon("play", "M8,5v14l11,-7z")
    val Pause = icon("pause", "M6,19h4V5H6v14zm8,-14v14h4V5h-4z")
    val Next = icon("next", "M6,18l8.5,-6L6,6v12zM16,6v12h2V6h-2z")
    val Previous = icon("previous", "M6,6h2v12H6zm3.5,6l8.5,6V6z")
    val Shuffle = icon(
        "shuffle",
        "M10.59,9.17L5.41,4 4,5.41l5.17,5.17 1.42,-1.41zM14.5,4l2.04,2.04L4,18.59 5.41,20 17.96,7.46 20,9.5V4h-5.5zm0.33,9.41l-1.41,1.41 3.13,3.13L14.5,20H20v-5.5l-2.04,2.04 -3.13,-3.13z",
    )
    private const val REPEAT = "M7,7h10v3l4,-4 -4,-4v3H5v6h2V7zm10,10H7v-3l-4,4 4,4v-3h12v-6h-2v4z"
    val Repeat = icon("repeat", REPEAT)
    val RepeatOne = icon("repeat_one", REPEAT, "M13,15V9h-1l-2,1v1h1.5v4H13z")
    val Queue = icon(
        "queue",
        "M15,6H3v2h12V6zm0,4H3v2h12v-2zM3,16h8v-2H3v2zM17,6v8.18c-0.31,-0.11 -0.65,-0.18 -1,-0.18 -1.66,0 -3,1.34 -3,3s1.34,3 3,3 3,-1.34 3,-3V8h3V6h-5z",
    )
    val List = icon("list", "M3,13h2v-2H3v2zm0,4h2v-2H3v2zm0,-8h2V7H3v2zm4,4h14v-2H7v2zm0,4h14v-2H7v2zM7,7v2h14V7H7z")
    val MusicNote = icon("music_note", "M12,3v10.55c-0.59,-0.34 -1.27,-0.55 -2,-0.55 -2.21,0 -4,1.79 -4,4s1.79,4 4,4 4,-1.79 4,-4V7h4V3h-6z")
    val Quote = icon("quote", "M6,17h3l2,-4V7H5v6h3zm8,0h3l2,-4V7h-6v6h3z")
    val Swap = icon("swap", "M6.99,11L3,15l3.99,4v-3H14v-2H6.99v-3zM21,9l-3.99,-4v3H10v2h7.01v3L21,9z")
    /** Sound wave over a faint centre line (stroked, unlike the filled icons above). */
    val Wave: ImageVector = ImageVector.Builder("wave", 24.dp, 24.dp, 24f, 24f).apply {
        addPath(
            PathParser().parsePathString("M2,12H22").toNodes(), fill = null, stroke = SolidColor(Color.Black),
            strokeAlpha = 0.6f, strokeLineWidth = 1.2f, strokeLineCap = StrokeCap.Round,
        )
        addPath(
            PathParser().parsePathString("M2,12C4,3 7,3 9,12S14,21 16,12 19,5 22,12").toNodes(), fill = null, stroke = SolidColor(Color.Black),
            strokeLineWidth = 1.8f, strokeLineCap = StrokeCap.Round, strokeLineJoin = StrokeJoin.Round,
        )
    }.build()
    val Remove = icon("remove", "M19,13H5v-2h14v2z")
    val Add = icon("add", "M19,13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z")
    val Down = icon("down", "M7.41,8.59L12,13.17l4.59,-4.58L18,10l-6,6 -6,-6 1.41,-1.41z")
}
