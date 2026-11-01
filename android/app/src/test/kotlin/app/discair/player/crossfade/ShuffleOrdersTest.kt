package app.discair.player.crossfade

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ShuffleOrdersTest {
    @Test fun aValidWalkReturnsThePlayOrder() {
        val next = mapOf(2 to 0, 0 to 3, 3 to 1)
        assertArrayEquals(intArrayOf(2, 0, 3, 1), ShuffleOrders.walk(4, 2) { next.getValue(it) })
    }

    @Test fun anEmptyQueueIsAnEmptyOrder() = assertEquals(0, ShuffleOrders.walk(0, -1) { -1 }!!.size)

    @Test fun aWalkThatRepeatsOrLeavesTheRangeIsRefusedNotApplied() {
        assertNull(ShuffleOrders.walk(3, 0) { 0 }) // loops back
        assertNull(ShuffleOrders.walk(3, 0) { 7 }) // out of range
        assertNull(ShuffleOrders.walk(3, 5) { 0 }) // bad start
        assertNull(ShuffleOrders.walk(3, 0) { -1 }) // ends early
    }

    @Test fun aSingleSongQueueNeedsNoNext() = assertArrayEquals(intArrayOf(0), ShuffleOrders.walk(1, 0) { error("not asked") })
}
