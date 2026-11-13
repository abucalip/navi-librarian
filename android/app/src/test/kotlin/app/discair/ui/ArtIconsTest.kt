package app.discair.ui

import app.discair.ui.common.ArtIcons
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ArtIconsTest {
    private val all = listOf(
        ArtIcons.Home, ArtIcons.Disc, ArtIcons.Lib, ArtIcons.Search, ArtIcons.Play, ArtIcons.Pause, ArtIcons.Next,
        ArtIcons.Previous, ArtIcons.Download, ArtIcons.Gear, ArtIcons.More, ArtIcons.Chevron, ArtIcons.Back, ArtIcons.Down,
        ArtIcons.Radio, ArtIcons.Get, ArtIcons.Heart, ArtIcons.HeartFilled, ArtIcons.Check, ArtIcons.Close, ArtIcons.Queue,
        ArtIcons.QueueAdd, ArtIcons.Shuffle, ArtIcons.Repeat, ArtIcons.RepeatOne, ArtIcons.Quote, ArtIcons.Tune, ArtIcons.Sun,
        ArtIcons.Server, ArtIcons.Swap, ArtIcons.Wave, ArtIcons.Sort, ArtIcons.Plus, ArtIcons.Minus, ArtIcons.Paths,
        ArtIcons.Info, ArtIcons.SignOut,
    )

    @Test fun everyIconIsA24ViewBoxWithDrawing() {
        all.forEach {
            assertEquals(it.name, 24f, it.viewportWidth, 0f)
            assertEquals(it.name, 24f, it.viewportHeight, 0f)
            assertTrue(it.name, it.root.size > 0)
        }
    }
}
