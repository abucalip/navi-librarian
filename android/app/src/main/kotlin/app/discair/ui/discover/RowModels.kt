package app.discair.ui.discover

import app.discair.model.DiscoveryEntry
import app.discair.model.DiscoveryList
import app.discair.ui.common.RowLead
import app.discair.ui.common.RowModel
import java.text.DateFormat
import java.util.Date

private val months = listOf("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

/** `YYYY-MM-DD`, `YYYY-MM` or `YYYY` as the server returns it; anything else yields null, as on the web. */
fun releaseDateLead(value: String?): RowLead.Date? {
    val m = Regex("""^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$""").matchEntire(value.orEmpty().trim()) ?: return null
    val month = m.groupValues[2].toIntOrNull() ?: 0
    val day = m.groupValues[3].toIntOrNull() ?: 0
    if ((m.groupValues[2].isNotEmpty() && month !in 1..12) || (m.groupValues[3].isNotEmpty() && day !in 1..31)) return null
    val name = if (month > 0) months[month - 1] else ""
    return RowLead.Date(if (day > 0) "$day $name" else name, m.groupValues[1])
}

/** Builds a row from a list entry. Order and content come from the server; this only labels them. */
fun rowModel(list: DiscoveryList, entry: DiscoveryEntry, position: Int): RowModel {
    val item = entry.item
    return withServerData(buildRow(list, item, position), entry)
}

private fun withServerData(row: RowModel, entry: DiscoveryEntry) =
    row.copy(metadata = entry.raw, owned = entry.item.acquired)

private fun buildRow(list: DiscoveryList, item: app.discair.model.DiscoveryItem, position: Int): RowModel {
    val listeners = (item.albumListeners ?: item.listeners)?.takeIf { it > 0 }?.let { "%,d listeners".format(it) }
    return when (list) {
        DiscoveryList.NewReleases -> RowModel(
            item.artistName, item.album, item.year,
            releaseDateLead(item.firstReleaseDate) ?: RowLead.None, emptyList(), bio = true,
        )
        DiscoveryList.Saved -> RowModel(
            item.artistName, item.album, item.year, RowLead.Rank(position),
            listOfNotNull(
                item.savedAt?.let { "Saved " + DateFormat.getDateInstance(DateFormat.MEDIUM).format(Date((it * 1000).toLong())) },
                if (item.acquired) "Already in your library" else null,
            ),
            bio = false,
        )
        DiscoveryList.Daily -> RowModel(
            item.artistName, item.album, item.year, RowLead.Rank(position),
            listOfNotNull(item.seedTag?.takeIf { it.isNotBlank() }?.let { "Seed tag: $it" }, listeners), bio = false,
        )
        else -> RowModel(
            item.artistName, item.album, item.year, RowLead.Rank(position),
            listOfNotNull(item.year?.toString(), listeners, item.reason.takeIf { it.isNotBlank() }), bio = true,
        )
    }
}
