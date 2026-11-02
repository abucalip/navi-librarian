package app.discair.data

private val MONTHS = listOf("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

/**
 * A release date as "Oct 2026". [firstRelease] is what the catalogue gives: "2026-10-17", "2026-10" or
 * "2026". With only a year the answer is the year; with nothing readable it falls back to [year], then null.
 */
fun releaseMonth(firstRelease: String?, year: Int?): String? {
    val parts = firstRelease?.trim()?.split("-").orEmpty()
    val y = parts.getOrNull(0)?.takeIf { it.length == 4 }?.toIntOrNull()
    val m = parts.getOrNull(1)?.toIntOrNull()?.takeIf { it in 1..12 }
    return when {
        y != null && m != null -> "${MONTHS[m - 1]} $y"
        y != null -> "$y"
        else -> year?.toString()
    }
}
