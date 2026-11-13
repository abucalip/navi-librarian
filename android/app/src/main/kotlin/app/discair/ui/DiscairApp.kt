package app.discair.ui

import app.discair.ui.common.ArtIcons
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
import app.discair.player.crossfade
import app.discair.DiscairApplication
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import app.discair.ui.common.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import kotlinx.coroutines.launch
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
import androidx.compose.ui.semantics.role
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
                .padding(start = 16.dp, top = 24.dp, end = 16.dp, bottom = 24.dp + app.discair.ui.LocalBottomClearance.current),
            verticalArrangement = Arrangement.spacedBy(16.dp),
            content = content,
        )
    }
}

@Composable
private fun Title(text: String) {
    if (text == "Discair") {
        app.discair.ui.common.Wordmark(40.dp)
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
fun SettingsScreen(state: UiState, model: AppViewModel, onBack: () -> Unit, onEqualizer: () -> Unit = {}, onCrossfade: () -> Unit = {}, onAppearance: () -> Unit = {}, onServer: () -> Unit = {}) {
    var confirmSignOut by remember { mutableStateOf(false) }
    val container = (androidx.compose.ui.platform.LocalContext.current.applicationContext as DiscairApplication).container
    // The page scrolls because the playback choices make it taller than a phone in landscape or at large text.
    // Soft Brut draws its own grouped page (settings/CoverStackSettings.kt); the sign-out sheet below is shared.
    // Flow draws its own grouped page (settings/FlowSettings.kt), also with the same sign-out sheet.
    if (app.discair.ui.common.isFlow()) app.discair.ui.settings.FlowSettingsPage(
        state, model, container, onBack, onEqualizer, onCrossfade, onAppearance, onServer, onSignOut = { confirmSignOut = true },
    ) else if (app.discair.ui.common.isCoverStack()) app.discair.ui.settings.CoverStackSettingsPage(
        state, model, container, onBack, onEqualizer, onCrossfade, onAppearance, onServer, onSignOut = { confirmSignOut = true },
    ) else Page(scroll = true) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            androidx.compose.material3.IconButton(onClick = onBack, Modifier.size(Target)) {
                Icon(app.discair.ui.player.PlayerIcons.Left, contentDescription = "Back")
            }
            Text("Settings", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.semantics { heading() })
        }
        Text("Connected to your servers.", style = MaterialTheme.typography.bodyLarge)
        CheckLine("Librarian", state.librarian)
        CheckLine("Navidrome", state.navidrome)
        // A grouped row with its state in words, first in the list (docs/redesign.md 8.2).
        val serverLine = app.discair.ui.downloads.SettingsRules.serverLine(state.librarian, state.navidrome)
        app.discair.ui.settings.SettingsRow(
            app.discair.ui.player.PlayerIcons.Server, "Server and services", serverLine.text, onClick = onServer,
            stateColor = when (serverLine.tone) {
                app.discair.ui.downloads.SettingsRules.Tone.Success -> Ink.Ok
                app.discair.ui.downloads.SettingsRules.Tone.Danger -> Ink.ChartRedText
                else -> MaterialTheme.colorScheme.onSurfaceVariant
            },
        )
        app.discair.ui.settings.AppearanceRow(container.appearance, onAppearance)
        PlaybackSettings(container, onEqualizer, onCrossfade)
        LibrarySettings()
        app.discair.ui.settings.ListenBrainzSettings()
        app.discair.ui.settings.RadioSettings()
        Spacer(Modifier.size(24.dp))
        // One joined group on one line, like the web's action groups.
        app.discair.ui.common.ActionGroup(Modifier.fillMaxWidth()) {
            app.discair.ui.common.ActionGroupButton(model::recheck, Modifier.weight(1f)) {
                app.discair.ui.common.GroupLabel("Check connection")
            }
            app.discair.ui.common.GroupDivider()
            app.discair.ui.common.ActionGroupButton(model::editServers, Modifier.weight(1f)) {
                app.discair.ui.common.GroupLabel("Edit servers")
            }
        }
        // Destructive and rare: set apart from the routine actions and always confirmed.
        Spacer(Modifier.size(32.dp))
        OutlinedButton(
            onClick = { confirmSignOut = true },
            modifier = Modifier.fillMaxWidth().heightIn(min = Target),
        ) { Text("Sign out…", color = Ink.ChartRedText) }
    }
    if (confirmSignOut) {
        // Nothing is signed out until the destructive button of the sheet is tapped.
        app.discair.ui.common.ConfirmSheet(
            spec = app.discair.ui.common.ConfirmSpecs.signOut(),
            onKeep = { confirmSignOut = false },
            onConfirm = { confirmSignOut = false; model.signOut() },
        )
    }
}

/**
 * The server's "resync the library after an import" option. It lives on the server, so this row reads
 * it live and writes it back; if the server cannot be reached the row says so instead of guessing.
 */
@Composable
internal fun LibrarySettings() {
    val repo = app.discair.ui.common.LocalRepository.current
    var value by remember { mutableStateOf<Boolean?>(null) }
    var problem by remember { mutableStateOf<String?>(null) }
    val scope = androidx.compose.runtime.rememberCoroutineScope()
    androidx.compose.runtime.LaunchedEffect(repo) {
        try {
            value = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) { repo.libraryResync() }
        } catch (e: Exception) {
            problem = "Could not read this option from the server."
        }
    }
    val softBrut = app.discair.ui.common.isCoverStack() || app.discair.ui.common.isFlow() // both group it as a row with a switch
    if (!softBrut) Section("Library", bold = true)
    val current = value
    val toggle: (Boolean) -> Unit = { on ->
        value = on
        problem = null
        scope.launch {
            try {
                kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) { repo.setLibraryResync(on) }
            } catch (e: Exception) {
                value = !on
                problem = "The server did not save this. Try again."
            }
        }
    }
    if (softBrut) {
        // A grouped row with an icon tile and a switch (CoverStackSettings.kt); the words are the same.
        app.discair.ui.settings.SettingsRow(
            app.discair.ui.player.PlayerIcons.Retry, "Resync after import",
            when {
                current == null && problem == null -> "Checking the server."
                current == null -> problem.orEmpty()
                problem != null -> problem.orEmpty()
                current -> "On. A few seconds after a successful import, the server reloads your library."
                else -> "Off. A new album can take up to ten minutes to show up."
            },
            modifier = if (current == null) Modifier else Modifier.toggleable(value = current, role = Role.Switch, onValueChange = toggle),
            trailing = { if (current != null) app.discair.ui.common.DiscairSwitch(checked = current) },
        )
        return
    }
    Row(
        Modifier.fillMaxWidth().heightIn(min = Target).then(
            if (current == null) Modifier else Modifier.toggleable(value = current, role = Role.Switch) { on ->
                value = on
                problem = null
                scope.launch {
                    try {
                        kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) { repo.setLibraryResync(on) }
                    } catch (e: Exception) {
                        value = !on
                        problem = "The server did not save this. Try again."
                    }
                }
            },
        ),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f).padding(end = 16.dp)) {
            Text("Resync after import", style = MaterialTheme.typography.titleMedium)
            Text(
                when {
                    current == null && problem == null -> "Checking the server."
                    current == null -> problem.orEmpty()
                    current -> "On. A few seconds after a successful import, the server reloads your library from Navidrome so the new album shows up here."
                    else -> "Off. A new album can take up to ten minutes to show up here after an import."
                },
                style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (current != null && problem != null) {
                Text(problem.orEmpty(), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
            }
        }
        if (current != null) app.discair.ui.common.DiscairSwitch(checked = current)
    }
}

internal enum class PlaybackShow { All, LookAndSound, Rest }

/**
 * Streaming quality and scrobbling. Both are per device and apply to songs started afterwards. Soft Brut lists the Equalizer and Crossfade rows under Look and sound and the rest under Playback; every other theme shows [PlaybackShow.All]. */
@Composable
internal fun PlaybackSettings(container: AppContainer, onEqualizer: () -> Unit, onCrossfade: () -> Unit, show: PlaybackShow = PlaybackShow.All) {
    val settings = container.playerSettings
    var rate by remember { mutableStateOf(settings.maxBitRate) }
    var scrobble by remember { mutableStateOf(settings.scrobbling) }
    if (show != PlaybackShow.LookAndSound) {
    if (show == PlaybackShow.All) Section("Playback", bold = true)
    var qualityOpen by remember { mutableStateOf(false) }
    val qualityName = app.discair.player.qualityLabel(rate)
    Box {
        app.discair.ui.settings.SettingsRow(
            app.discair.ui.player.PlayerIcons.Wave, "Streaming quality", qualityName,
            modifier = Modifier.semantics { role = Role.DropdownList }, onClick = { qualityOpen = true }, divider = show != PlaybackShow.Rest,
            trailing = { Icon(app.discair.ui.player.PlayerIcons.Down, contentDescription = null) },
        )
        app.discair.ui.common.DropdownMenu(expanded = qualityOpen, onDismissRequest = { qualityOpen = false }) {
            app.discair.player.QUALITY_CHOICES.forEach { choice ->
                val name = app.discair.player.qualityLabel(choice)
                androidx.compose.material3.DropdownMenuItem(
                    text = { Text(if (choice == rate) "$name (selected)" else name) },
                    onClick = { qualityOpen = false; rate = choice; settings.maxBitRate = choice },
                    modifier = Modifier.heightIn(min = Target),
                )
            }
        }
    }
    Text(
        "Original plays the file as it is and keeps songs gapless. A lower rate converts on the server and saves data, but the converted stream can leave a short gap between songs. It applies to songs you start after changing it.",
        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    app.discair.ui.settings.SettingsRow(
        app.discair.ui.player.PlayerIcons.MusicNote, "Scrobble plays",
        if (scrobble) "On. Reports plays to Navidrome" else "Off. Plays are not reported",
        modifier = Modifier.toggleable(value = scrobble, role = Role.Switch, onValueChange = { scrobble = it; container.setScrobbling(it) }),
        trailing = { app.discair.ui.common.DiscairSwitch(checked = scrobble) },
    )
    Text(
        if (scrobble) "Songs you play here are added to your listening history, which also shapes your recommendations."
        else "Plays are not sent, so they will not change your history or recommendations.",
        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    // Songs saved with "Download to device": how many, how much room they take, and one way to clear them.
    val offline = container.offline
    val offlineStatus by offline.status.collectAsState()
    val savedCount = offlineStatus.count { it.value == app.discair.player.OfflineStatus.Done }
    val offlineScope = androidx.compose.runtime.rememberCoroutineScope()
    Row(Modifier.fillMaxWidth().heightIn(min = Target), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f).padding(end = 16.dp)) {
            Text("Downloaded songs", style = MaterialTheme.typography.titleMedium)
            Text(
                if (savedCount == 0) "None. Use a song's menu and choose Download to device to play it without a connection."
                else "$savedCount on this device, ${"%.1f".format(offline.savedBytes() / 1_048_576.0)} MB.",
                style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        if (savedCount > 0) TextButton(
            onClick = { offlineScope.launch { offline.removeAll() } }, modifier = Modifier.heightIn(min = Target),
        ) { Text("Remove all") }
    }
    }
    if (show != PlaybackShow.Rest) {
    // The summary says on or off in words, so the state is not left to colour or to opening the page.
    val eq = remember { container.eqSettings.load() }
    var eqNow by remember { mutableStateOf(eq) }
    androidx.compose.runtime.DisposableEffect(Unit) {
        val remove = container.eqSettings.addListener { eqNow = container.eqSettings.load() }
        onDispose { remove() }
    }
    app.discair.ui.settings.SettingsRow(
        app.discair.ui.player.PlayerIcons.Tune, "Equalizer",
        app.discair.player.eq.eqSummary(eqNow).removePrefix("Equalizer: ").replaceFirstChar { it.uppercase() }, onClick = onEqualizer,
    )
    // Crossfade: the summary says off or the length in words (ANDROID_CROSSFADE_CONTRACT.md 7).
    var xfNow by remember { mutableStateOf(settings.crossfade) }
    androidx.compose.runtime.DisposableEffect(settings) {
        val handle = settings.onChange { xfNow = settings.crossfade }
        onDispose { handle.close() }
    }
    app.discair.ui.settings.SettingsRow(
        app.discair.ui.player.PlayerIcons.Swap, "Crossfade", app.discair.player.crossfade.CrossfadeText.summary(xfNow), onClick = onCrossfade,
    )
    }
}

@Composable
private fun Section(title: String, bold: Boolean = false) {
    // A hairline sets each group apart, as the grouped rows in the mockup do.
    app.discair.ui.common.RowDivider(Modifier.padding(top = 16.dp))
    Text(
        title,
        // Bold in the body face instead of the display face (owner request for Playback).
        style = if (bold) MaterialTheme.typography.titleLarge.copy(
            fontFamily = MaterialTheme.typography.bodyLarge.fontFamily, fontWeight = androidx.compose.ui.text.font.FontWeight.Bold, letterSpacing = androidx.compose.ui.unit.TextUnit.Unspecified,
        ) else MaterialTheme.typography.titleLarge,
        modifier = Modifier.padding(top = 16.dp).semantics { heading() },
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

@Composable
internal fun CheckLines(state: UiState) {
    CheckLine("Librarian", state.librarian)
    CheckLine("Navidrome", state.navidrome)
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
            Check.Ok -> Icon(ArtIcons.Check, contentDescription = null, tint = tint)
            is Check.Failed -> Icon(ArtIcons.Warning, contentDescription = null, tint = tint)
            Check.Idle -> Icon(ArtIcons.Info, contentDescription = null, tint = tint)
        }
        Spacer(Modifier.width(8.dp))
        Text(text, style = MaterialTheme.typography.bodyMedium, color = tint)
    }
}

private const val TAILSCALE = "com.tailscale.ipn"
