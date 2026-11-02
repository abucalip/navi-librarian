package app.discair

import app.discair.data.addedWithin
import java.time.Instant
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RecentlyAddedTest {
    private val now = Instant.parse("2026-11-02T12:00:00Z")

    @Test fun `an album added yesterday is recent`() = assertTrue(addedWithin("2026-11-01T08:00:00.123456789Z", now))
    @Test fun `an album added 29 days ago is recent`() = assertTrue(addedWithin("2026-10-04T12:00:01Z", now))
    @Test fun `an album added 31 days ago is not`() = assertFalse(addedWithin("2026-10-02T11:00:00Z", now))
    @Test fun `a missing or unreadable date is not recent`() {
        assertFalse(addedWithin(null, now))
        assertFalse(addedWithin("", now))
        assertFalse(addedWithin("last week", now))
    }
}
