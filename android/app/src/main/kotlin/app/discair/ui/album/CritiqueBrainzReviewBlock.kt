package app.discair.ui.album

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import app.discair.model.CritiqueBrainzReview
import app.discair.ui.theme.Ink

@Composable
internal fun CritiqueBrainzReviewBlock(
    reviews: List<CritiqueBrainzReview>,
    hasPressReviews: Boolean,
    modifier: Modifier = Modifier,
) {
    if (reviews.isEmpty()) return
    val uri = LocalUriHandler.current
    var index by rememberSaveable(reviews.size) { mutableIntStateOf(0) }
    val safeIndex = index.coerceIn(0, reviews.lastIndex)
    val review = reviews[safeIndex]
    val paragraphs = review.paragraphs.ifEmpty {
        listOfNotNull(review.fullText.takeIf { it.isNotBlank() } ?: review.quote.takeIf { it.isNotBlank() })
    }
    val isRtl = review.language.equals("ar", ignoreCase = true)

    Column(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                if (review.language.isNotBlank()) {
                    Surface(
                        color = MaterialTheme.colorScheme.surfaceVariant,
                        shape = MaterialTheme.shapes.extraSmall,
                    ) {
                        Text(
                            text = review.language.uppercase(),
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                        )
                    }
                }
                if (!review.origin.isNullOrBlank()) {
                    Text(
                        text = review.origin,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            if (reviews.size > 1) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    modifier = Modifier
                        .heightIn(min = 48.dp)
                        .clickable(role = Role.Button) { index = (safeIndex + 1) % reviews.size }
                        .semantics { contentDescription = "Next review (${safeIndex + 1} of ${reviews.size})" }
                        .padding(horizontal = 4.dp),
                ) {
                    Text(
                        text = "${safeIndex + 1} / ${reviews.size}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        text = "›",
                        style = MaterialTheme.typography.titleMedium,
                        color = Ink.AccentText,
                    )
                }
            }
        }

        Spacer(Modifier.height(8.dp))

        val textDirection = if (isRtl) LayoutDirection.Rtl else LocalLayoutDirection.current
        CompositionLocalProvider(LocalLayoutDirection provides textDirection) {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                paragraphs.forEach { paragraph ->
                    Text(
                        text = paragraph,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
        }

        Spacer(Modifier.height(10.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            val metaParts = buildList {
                if (review.author.isNotBlank()) add(review.author)
                if (review.rating != null) add("${review.rating}/5")
            }
            if (metaParts.isNotEmpty()) {
                Text(
                    text = metaParts.joinToString(" · "),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (review.license.isNotBlank() && review.licenseUrl.isNotBlank()) {
                Text(
                    text = review.license,
                    style = MaterialTheme.typography.bodySmall,
                    color = Ink.AccentText,
                    modifier = Modifier
                        .heightIn(min = 48.dp)
                        .clickable(role = Role.Button) { uri.openUri(review.licenseUrl) }
                        .padding(vertical = 12.dp),
                )
            }
            if (review.url.isNotBlank()) {
                Text(
                    text = "CritiqueBrainz",
                    style = MaterialTheme.typography.bodySmall,
                    color = Ink.AccentText,
                    modifier = Modifier
                        .heightIn(min = 48.dp)
                        .clickable(role = Role.Button) { uri.openUri(review.url) }
                        .padding(vertical = 12.dp),
                )
            }
        }

        if (hasPressReviews) {
            HorizontalDivider(Modifier.padding(vertical = 12.dp))
        }
    }
}
