package app.discair.ui.discover

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.model.InsightCard
import app.discair.model.InsightNarrative
import app.discair.model.InsightsResponse
import app.discair.ui.common.Target
import app.discair.ui.theme.Ink
import app.discair.ui.theme.themeShape

private val LensNames = mapOf(
    "forgotten_gem" to "Forgotten gems",
    "series_completion" to "Series",
    "blind_spot" to "Blind spots",
    "hidden_canon" to "Hidden canon",
    "anniversary" to "Anniversaries",
)

internal fun lensName(kind: String) = LensNames[kind] ?: kind.replace('_', ' ').replaceFirstChar { it.uppercase() }

/** Lenses listed on the page: the five known ones always (so "off" is visible), then any kind the server added. */
internal fun lensKinds(response: InsightsResponse) =
    InsightsResponse.KnownOrder + response.orderedKinds.filter { it !in InsightsResponse.KnownOrder }

/**
 * The Insights tab: one section per lens, in the server's order. A lens the server has not enabled says "off"; an
 * enabled lens with no cards says so. The app never fills a gap with a card of its own, and a card's wording is the
 * server's. Dismissed cards leave at once; [onDismiss] sends it and offers Undo.
 */
@Composable
fun InsightsPage(
    response: InsightsResponse,
    hidden: Set<String>,
    onDismiss: (InsightCard) -> Unit,
) {
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 16.dp, top = 8.dp, end = 16.dp, bottom = 16.dp + app.discair.ui.LocalBottomClearance.current),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        for (kind in lensKinds(response)) {
            val lens = response.lenses[kind]
            val enabled = lens?.enabled == true
            val cards = lens?.cards.orEmpty().filter { it.id !in hidden }
            item(key = "head:$kind") {
                Row(Modifier.fillMaxWidth().padding(top = 8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(lensName(kind), style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
                    Text(
                        if (enabled) "${cards.size}" else "off", color = Ink.TextMuted, style = MaterialTheme.typography.labelLarge,
                        modifier = Modifier.semantics { contentDescription = "${lensName(kind)}: " + if (enabled) "${cards.size} cards" else "off" },
                    )
                }
            }
            when {
                !enabled -> item(key = "off:$kind") {
                    Text("Off. The server turns a lens on only after it passes its check.", color = Ink.TextMuted, style = MaterialTheme.typography.bodyMedium)
                }
                cards.isEmpty() -> item(key = "none:$kind") {
                    Text(
                        "Nothing to show right now. The lens is on and found no cards; it never fills the gap with guesses.",
                        color = Ink.TextMuted, style = MaterialTheme.typography.bodyMedium,
                    )
                }
                else -> items(cards, key = { it.id }) { card -> InsightCardView(card, onDismiss) }
            }
        }
    }
}

/** One generic card: the server's title and body, a counter line for series, "Why?" and Dismiss. */
@Composable
private fun InsightCardView(card: InsightCard, onDismiss: (InsightCard) -> Unit) {
    var why by remember(card.id) { mutableStateOf(false) }
    Column(
        Modifier.fillMaxWidth().clip(themeShape(16.dp)).background(MaterialTheme.colorScheme.surface).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(card.title, style = MaterialTheme.typography.titleMedium)
        card.subject.artist?.let { Text(it, color = Ink.TextMuted, style = MaterialTheme.typography.bodyMedium) }
        if (card.body.isNotEmpty()) Text(card.body, style = MaterialTheme.typography.bodyMedium)
        for (run in card.missingRuns) {
            val span = if (run.firstPosition == run.lastPosition) "${run.firstPosition}" else "${run.firstPosition} to ${run.lastPosition}"
            Text(
                "Missing $span" + if (run.labels.isEmpty()) "" else ": " + run.labels.joinToString(", "),
                color = Ink.TextMuted, style = MaterialTheme.typography.labelMedium,
            )
        }
        if (why) Text(InsightNarrative.why(card), color = Ink.TextMuted, style = MaterialTheme.typography.bodyMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TextButton(onClick = { why = !why }, Modifier.heightIn(min = Target)) { Text(if (why) "Hide why" else "Why?") }
            if (card.dismissible) {
                TextButton(onClick = { onDismiss(card) }, Modifier.heightIn(min = Target)) {
                    Text("Dismiss", modifier = Modifier.semantics { contentDescription = "Dismiss ${card.title}" })
                }
            }
        }
    }
}
