package app.discair.ui.settings

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.ui.player.PlayerIcons
import app.discair.ui.common.Target
import app.discair.ui.theme.Appearance
import app.discair.ui.theme.FontPair
import app.discair.ui.theme.FontPairs
import app.discair.ui.theme.Palette
import app.discair.ui.theme.Palettes
import app.discair.ui.theme.THEME_SYSTEM

/**
 * Settings, Appearance: the colour theme and the font pair. Both apply at once and are kept on this device.
 * "Follow system" uses the day theme when the phone is in light mode and the night theme in dark mode.
 */
@Composable
fun AppearanceSettings(appearance: Appearance) {
    val following = appearance.themeChoice == THEME_SYSTEM
    Text("Theme", style = MaterialTheme.typography.titleMedium)
    ChoiceDropdown(
        title = "Theme",
        current = if (following) "Follow system" else Palettes.byId(appearance.themeChoice)?.label ?: "Follow system",
        options = listOf(Option(THEME_SYSTEM, "Follow system", "Day or night theme, as the phone is set")) +
            Palettes.Light.map { it.option("Light") } + Palettes.Dark.map { it.option("Dark") },
        selectedId = appearance.themeChoice,
        onPick = appearance::chooseTheme,
    )
    if (following) {
        Text("Day theme", style = MaterialTheme.typography.titleMedium)
        ChoiceDropdown(
            title = "Day theme",
            current = Palettes.byId(appearance.dayTheme)?.label ?: "",
            options = Palettes.Light.map { it.option("Light") },
            selectedId = appearance.dayTheme,
            onPick = appearance::chooseDay,
        )
        Text("Night theme", style = MaterialTheme.typography.titleMedium)
        ChoiceDropdown(
            title = "Night theme",
            current = Palettes.byId(appearance.nightTheme)?.label ?: "",
            options = Palettes.Dark.map { it.option("Dark") },
            selectedId = appearance.nightTheme,
            onPick = appearance::chooseNight,
        )
    }
    Text(
        if (following) "Follows your phone's light and dark setting. Dark themes can save battery on OLED screens; High contrast has the strongest text."
        else "Fixed, whatever the phone's light or dark setting is. Choose Follow system to use a day and a night theme.",
        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
    )

    Text("Font", style = MaterialTheme.typography.titleMedium)
    ChoiceDropdown(
        title = "Font",
        current = appearance.fonts.fullName(),
        options = FontPairs.All.map { Option(it.id, it.label, "${it.titleName} and ${it.bodyName}", it) },
        selectedId = appearance.fontPairId,
        onPick = appearance::chooseFont,
    )
    Text(
        "Titles use ${appearance.fonts.titleName}; everything else uses ${appearance.fonts.bodyName}. Numbers stay in JetBrains Mono. All text still follows the phone's font size.",
        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

private fun FontPair.fullName() = "$label · $titleName and $bodyName"

private class Option(val id: String, val label: String, val detail: String, val font: FontPair? = null, val palette: Palette? = null)

private fun Palette.option(kind: String) = Option(id, label, kind, palette = this)

/** The same dropdown the Playback section uses: a full-width button, a menu of rows at least 48dp tall. */
@Composable
private fun ChoiceDropdown(title: String, current: String, options: List<Option>, selectedId: String, onPick: (String) -> Unit) {
    var open by remember { mutableStateOf(false) }
    androidx.compose.foundation.layout.Box {
        OutlinedButton(
            onClick = { open = true },
            modifier = Modifier.fillMaxWidth().heightIn(min = Target)
                .semantics { contentDescription = "$title, $current"; role = Role.DropdownList },
        ) {
            Text(current, Modifier.weight(1f))
            Icon(PlayerIcons.Down, contentDescription = null)
        }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            options.forEach { option ->
                val on = option.id == selectedId
                DropdownMenuItem(
                    text = {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            option.palette?.let { Swatch(it) }
                            Column {
                                if (option.font != null) Text(
                                    option.label, fontFamily = option.font.title, fontWeight = option.font.titleWeight,
                                    style = MaterialTheme.typography.titleMedium,
                                ) else Text(option.label)
                                Text(option.detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Spacer(Modifier.width(4.dp))
                            if (on) Icon(Icons.Default.Check, contentDescription = "Selected", modifier = Modifier.size(18.dp))
                        }
                    },
                    onClick = { open = false; onPick(option.id) },
                    modifier = Modifier.heightIn(min = Target)
                        .semantics { contentDescription = "${option.label}, ${option.detail}${if (on) ", selected" else ""}" },
                )
            }
        }
    }
}

/** Three dots in the theme's own page, surface and accent colours, ringed so a pale one still shows. */
@Composable
private fun Swatch(p: Palette) {
    Row(
        Modifier.background(p.ink, RoundedCornerShape(50)).border(BorderStroke(1.dp, p.edgeStrong), RoundedCornerShape(50))
            .padding(horizontal = 6.dp, vertical = 5.dp),
        horizontalArrangement = Arrangement.spacedBy(3.dp),
    ) {
        listOf(p.surface, p.text, p.accent).forEach { Spacer(Modifier.size(12.dp).background(it, CircleShape).border(BorderStroke(0.5.dp, p.edge), CircleShape)) }
    }
}
