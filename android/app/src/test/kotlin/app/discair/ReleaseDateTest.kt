package app.discair

import app.discair.data.releaseMonth
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ReleaseDateTest {
    @Test fun `a full date reads as month and year`() = assertEquals("Oct 2026", releaseMonth("2026-10-17", 2026))
    @Test fun `a month and year reads the same`() = assertEquals("Jan 2026", releaseMonth("2026-01", null))
    @Test fun `a bare year stays a year`() = assertEquals("2026", releaseMonth("2026", null))
    @Test fun `no date falls back to the year`() = assertEquals("2025", releaseMonth(null, 2025))
    @Test fun `an unreadable date falls back to the year, then nothing`() {
        assertEquals("2025", releaseMonth("soon", 2025))
        assertEquals("2026", releaseMonth("2026-13-01", null))
        assertNull(releaseMonth("", null))
    }
}
