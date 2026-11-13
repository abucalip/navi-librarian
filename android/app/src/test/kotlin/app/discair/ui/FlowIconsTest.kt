package app.discair.ui

import app.discair.ui.common.FlowIcons
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class FlowIconsTest {
    private val all = listOf(
        FlowIcons.Home, FlowIcons.Disc, FlowIcons.Lib, FlowIcons.Search, FlowIcons.Play, FlowIcons.Pause, FlowIcons.Next,
        FlowIcons.Previous, FlowIcons.Download, FlowIcons.Gear, FlowIcons.More, FlowIcons.Chevron, FlowIcons.Back, FlowIcons.Down,
        FlowIcons.Radio, FlowIcons.Get, FlowIcons.Heart, FlowIcons.HeartFilled, FlowIcons.Check, FlowIcons.Close, FlowIcons.Queue,
        FlowIcons.QueueAdd, FlowIcons.Shuffle, FlowIcons.Repeat, FlowIcons.RepeatOne, FlowIcons.Quote, FlowIcons.Tune, FlowIcons.Sun,
        FlowIcons.Server, FlowIcons.Swap, FlowIcons.Wave, FlowIcons.Sort, FlowIcons.Plus, FlowIcons.Minus, FlowIcons.Paths,
        FlowIcons.Info, FlowIcons.SignOut,
    )

    @Test fun everyIconIsA24ViewBoxWithDrawing() {
        all.forEach {
            assertEquals(it.name, 24f, it.viewportWidth, 0f)
            assertEquals(it.name, 24f, it.viewportHeight, 0f)
            assertTrue(it.name, it.root.size > 0)
        }
    }
}
