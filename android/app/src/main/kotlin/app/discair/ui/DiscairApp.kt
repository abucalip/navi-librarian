package app.discair.ui

import app.discair.R
import androidx.compose.foundation.layout.height
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import android.content.Intent
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.selection.toggleable
import androidx.compose.ui.semantics.Role
import app.discair.AppContainer
import app.discair.DiscairApplication
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.autofill.ContentType
import androidx.compose.ui.focus.FocusDirection
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.contentType
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import app.discair.AppViewModel
import app.discair.Check
import app.discair.Screen
import app.discair.UiState
import app.discair.net.UrlProblem
import app.discair.ui.theme.Ink

private val MaxFormWidth = 480.dp
private val Target = 48.dp

@Composable
fun DiscairApp(state: UiState, model: AppViewModel, container: app.discair.AppContainer) {
    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        when (state.screen) {
            Screen.Checking -> CheckingScreen(state)
            Screen.Setup -> SetupScreen(state, model)
            Screen.Unavailable -> UnavailableScreen(state, model)
            Screen.Home -> MainShell(state, model, container)
        }
    }
}

/** Centres a column no wider than a phone form, so tablets and landscape stay readable. */
@Composable
private fun Page(scroll: Boolean = false, content: @Composable ColumnScope.() -> Unit) {
    Box(Modifier.fillMaxSize().safeDrawingPadding(), contentAlignment = Alignment.TopCenter) {
        Column(
            Modifier
                .widthIn(max = MaxFormWidth)
                .fillMaxSize()
                .then(if (scroll) Modifier.verticalScroll(rememberScrollState()) else Modifier)
                .padding(horizontal = 16.dp, vertical = 24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            content = content,
        )
    }
}

@Composable
private fun Title(text: String) {
    if (text == "Discair") {
        Icon(
            painterResource(R.drawable.ic_wordmark), contentDescription = text, tint = Color.Unspecified,
            modifier = Modifier.height(40.dp).semantics { heading() },
        )
        return
    }
    Text(
        text,
        style = MaterialTheme.typography.headlineLarge,
        modifier = Modifier.semantics { heading() },
    )
}

@Composable
private fun CheckingScreen(state: UiState) = Page {
    Title("Discair")
    Text(
        "Checking your servers…",
        style = MaterialTheme.typography.bodyLarge,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    CheckLine("Librarian", state.librarian)
    CheckLine("Navidrome", state.navidrome)
}

@Composable
private fun SetupScreen(state: UiState, model: AppViewModel) {
    BackHandler(enabled = state.canCancelEdit) { model.cancelEdit() }
    val busy = state.librarian is Check.Pending || state.navidrome is Check.Pending
    val form = state.form
    Page(scroll = true) {
        Title("Discair")
        Text(
            "Connect to your servers over Tailscale. Both addresses must start with https://.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        state.notice?.let {
            Text(
                it, style = MaterialTheme.typography.bodyMedium, color = Ink.ChartRedText,
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
            )
        }

        Section("Librarian")
        Field("Address", form.librarianUrl, KeyboardType.Uri, state.showMissing, state.librarianUrlProblem) { v ->
            model.edit { it.copy(librarianUrl = v) }
        }
        Field("User name", form.librarianUser, KeyboardType.Text, state.showMissing, contentType = ContentType.Username) { v ->
            model.edit { it.copy(librarianUser = v) }
        }
        Field("Password", form.librarianPassword, KeyboardType.Password, state.showMissing, secret = true) { v ->
            model.edit { it.copy(librarianPassword = v) }
        }
        CheckLine("Librarian", state.librarian)

        Section("Navidrome")
        Field("Address", form.navidromeUrl, KeyboardType.Uri, state.showMissing, state.navidromeUrlProblem) { v ->
            model.edit { it.copy(navidromeUrl = v) }
        }
        Field("User name", form.navidromeUser, KeyboardType.Text, state.showMissing, contentType = ContentType.Username) { v ->
            model.edit { it.copy(navidromeUser = v) }
        }
        Field("Password", form.navidromePassword, KeyboardType.Password, state.showMissing, secret = true, last = true, onDone = model::connect) { v ->
            model.edit { it.copy(navidromePassword = v) }
        }
        CheckLine("Navidrome", state.navidrome)

        // Stays enabled so a missing field is explained on the field, not by a dead button.
        Button(
            onClick = model::connect,
            enabled = !busy,
            modifier = Modifier.fillMaxWidth().heightIn(min = Target),
        ) { Text(if (busy) "Connecting…" else "Connect") }
        if (state.canCancelEdit) {
            OutlinedButton(
                onClick = model::cancelEdit,
                enabled = !busy,
                modifier = Modifier.fillMaxWidth().heightIn(min = Target),
            ) { Text("Cancel") }
        }
    }
}

@Composable
private fun UnavailableScreen(state: UiState, model: AppViewModel) {
    val context = LocalContext.current
    val tailscale = remember { context.packageManager.getLaunchIntentForPackage(TAILSCALE) }
    Page {
        Title("Can't connect")
        Text(
            "Your saved servers did not answer. Nothing was changed.",
            style = MaterialTheme.typography.bodyLarge,
        )
        CheckLine("Librarian", state.librarian)
        CheckLine("Navidrome", state.navidrome)
        Spacer(Modifier.weight(1f))
        Button(onClick = model::recheck, modifier = Modifier.fillMaxWidth().heightIn(min = Target)) {
            Text("Try again")
        }
        if (tailscale != null) {
            OutlinedButton(
                onClick = { context.startActivity(Intent(tailscale).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) },
                modifier = Modifier.fillMaxWidth().heightIn(min = Target),
            ) { Text("Open Tailscale") }
        }
        OutlinedButton(onClick = model::editServers, modifier = Modifier.fillMaxWidth().heightIn(min = Target)) {
            Text("Edit servers")
        }
    }
}

@Composable
fun SettingsScreen(state: UiState, model: AppViewModel, onBack: () -> Unit, onEqualizer: () -> Unit = {}) {
    var confirmSignOut by remember { mutableStateOf(false) }
    val container = (androidx.compose.ui.platform.LocalContext.current.applicationContext as DiscairApplication).container
    // The page scrolls because the playback choices make it taller than a phone in landscape or at large text.
    Page(scroll = true) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            androidx.compose.material3.IconButton(onClick = onBack, Modifier.size(Target)) {
                Icon(androidx.compose.material.icons.Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
            }
            Text("Settings", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.semantics { heading() })
        }
        Text("Connected to your servers.", style = MaterialTheme.typography.bodyLarge)
        CheckLine("Librarian", state.librarian)
        CheckLine("Navidrome", state.navidrome)
        PlaybackSettings(container, onEqualizer)
        Spacer(Modifier.size(24.dp))
        OutlinedButton(onClick = model::recheck, modifier = Modifier.fillMaxWidth().heightIn(min = Target)) {
            Text("Check again")
        }
        OutlinedButton(onClick = model::editServers, modifier = Modifier.fillMaxWidth().heightIn(min = Target)) {
            Text("Edit servers")
        }
        // Destructive and rare: set apart from the routine actions and always confirmed.
        Spacer(Modifier.size(32.dp))
        TextButton(
            onClick = { confirmSignOut = true },
            modifier = Modifier.fillMaxWidth().heightIn(min = Target),
        ) { Text("Sign out…", color = MaterialTheme.colorScheme.error) }
    }
    if (confirmSignOut) {
        AlertDialog(
            onDismissRequest = { confirmSignOut = false },
            title = { Text("Sign out of Discair?") },
            text = {
                Text(
                    "This removes both server addresses, user names and passwords from this phone. " +
                        "You will have to enter them again.",
                )
            },
            dismissButton = {
                TextButton(
                    onClick = { confirmSignOut = false },
                    modifier = Modifier.defaultMinSize(minHeight = Target),
                ) { Text("Keep me signed in") }
            },
            confirmButton = {
                TextButton(
                    onClick = { confirmSignOut = false; model.signOut() },
                    modifier = Modifier.defaultMinSize(minHeight = Target),
                ) { Text("Sign out", color = MaterialTheme.colorScheme.error) }
            },
        )
    }
}

/** Streaming quality and scrobbling. Both are per device and apply to songs started afterwards. */
@Composable
private fun PlaybackSettings(container: AppContainer, onEqualizer: () -> Unit) {
    val settings = container.playerSettings
    var rate by remember { mutableStateOf(settings.maxBitRate) }
    var scrobble by remember { mutableStateOf(settings.scrobbling) }
    Section("Playback")
    Text("Streaming quality", style = MaterialTheme.typography.titleMedium)
    Column(Modifier.selectableGroup()) {
        app.discair.player.QUALITY_CHOICES.forEach { choice ->
            Row(
                Modifier.fillMaxWidth().heightIn(min = Target)
                    .selectable(selected = rate == choice, role = Role.RadioButton, onClick = { rate = choice; settings.maxBitRate = choice }),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                androidx.compose.material3.RadioButton(selected = rate == choice, onClick = null)
                Text(app.discair.player.qualityLabel(choice), Modifier.padding(start = 12.dp), style = MaterialTheme.typography.bodyLarge)
            }
        }
    }
    Text(
        "Original plays the file as it is and keeps songs gapless. A lower rate converts on the server and saves data, but the converted stream can leave a short gap between songs. It applies to songs you start after changing it.",
        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    Row(
        Modifier.fillMaxWidth().heightIn(min = Target)
            .toggleable(value = scrobble, role = Role.Switch, onValueChange = { scrobble = it; container.setScrobbling(it) }),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f).padding(end = 12.dp)) {
            Text("Record plays", style = MaterialTheme.typography.titleMedium)
            Text(
                if (scrobble) "On. Songs you play here are added to your listening history, which also shapes your recommendations."
                else "Off. Plays are not sent, so they will not change your history or recommendations.",
                style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        androidx.compose.material3.Switch(checked = scrobble, onCheckedChange = null)
    }
    // The summary says on or off in words, so the state is not left to colour or to opening the page.
    val eq = remember { container.eqSettings.load() }
    var eqNow by remember { mutableStateOf(eq) }
    androidx.compose.runtime.DisposableEffect(Unit) {
        val remove = container.eqSettings.addListener { eqNow = container.eqSettings.load() }
        onDispose { remove() }
    }
    Row(
        Modifier.fillMaxWidth().heightIn(min = Target).clickable(role = Role.Button, onClick = onEqualizer),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f).padding(end = 12.dp)) {
            Text("Equalizer", style = MaterialTheme.typography.titleMedium)
            Text(
                app.discair.player.eq.eqSummary(eqNow).removePrefix("Equalizer: ").replaceFirstChar { it.uppercase() },
                style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Icon(androidx.compose.material.icons.Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null)
    }
}

@Composable
private fun Section(title: String) {
    Text(
        title,
        style = MaterialTheme.typography.titleLarge,
        modifier = Modifier.padding(top = 12.dp).semantics { heading() },
    )
}

@OptIn(ExperimentalComposeUiApi::class)
@Composable
private fun Field(
    label: String,
    value: String,
    keyboard: KeyboardType,
    showMissing: Boolean,
    problem: UrlProblem? = null,
    secret: Boolean = false,
    last: Boolean = false,
    contentType: ContentType? = null,
    onDone: () -> Unit = {},
    onChange: (String) -> Unit,
) {
    val focus = LocalFocusManager.current
    var revealed by remember { mutableStateOf(false) }
    val missing = showMissing && value.isBlank()
    val message = problem?.message ?: if (missing) "Required." else null
    val kind = contentType ?: if (secret) ContentType.Password else null
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        singleLine = true,
        isError = message != null,
        supportingText = message?.let { { Text(it) } },
        visualTransformation = if (secret && !revealed) PasswordVisualTransformation() else VisualTransformation.None,
        trailingIcon = if (secret) {
            {
                TextButton(
                    onClick = { revealed = !revealed },
                    modifier = Modifier
                        .defaultMinSize(minWidth = Target, minHeight = Target)
                        .semantics { contentDescription = if (revealed) "Hide password" else "Show password" },
                ) { Text(if (revealed) "Hide" else "Show") }
            }
        } else null,
        keyboardOptions = KeyboardOptions(
            keyboardType = keyboard,
            autoCorrectEnabled = false,
            imeAction = if (last) ImeAction.Done else ImeAction.Next,
        ),
        keyboardActions = KeyboardActions(
            onNext = { focus.moveFocus(FocusDirection.Down) },
            onDone = { focus.clearFocus(); onDone() },
        ),
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 56.dp)
            .then(if (kind != null) Modifier.semantics { this.contentType = kind } else Modifier),
    )
}

/** One server's state as icon plus words, never colour alone. Announced to TalkBack on change. */
@Composable
private fun CheckLine(name: String, check: Check) {
    if (check == Check.Idle) return
    val (text, tint) = when (check) {
        Check.Idle -> "" to MaterialTheme.colorScheme.onSurfaceVariant
        Check.Pending -> "$name: checking…" to MaterialTheme.colorScheme.onSurfaceVariant
        Check.Ok -> "$name: connected" to Ink.Ok
        is Check.Failed -> "$name: failed. ${check.failure.message}" to Ink.ChartRedText
    }
    Row(
        Modifier.fillMaxWidth().heightIn(min = 32.dp).semantics { liveRegion = LiveRegionMode.Polite },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        when (check) {
            Check.Pending -> CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
            Check.Ok -> Icon(Icons.Default.Check, contentDescription = null, tint = tint)
            is Check.Failed -> Icon(Icons.Default.Warning, contentDescription = null, tint = tint)
            Check.Idle -> Icon(Icons.Default.Info, contentDescription = null, tint = tint)
        }
        Spacer(Modifier.width(8.dp))
        Text(text, style = MaterialTheme.typography.bodyMedium, color = tint)
    }
}

private const val TAILSCALE = "com.tailscale.ipn"
