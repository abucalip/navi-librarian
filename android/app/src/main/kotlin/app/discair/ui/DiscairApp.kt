package app.discair.ui

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
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
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
fun DiscairApp(state: UiState, model: AppViewModel) {
    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        when (state.screen) {
            Screen.Checking -> CheckingScreen(state)
            Screen.Setup -> SetupScreen(state, model)
            Screen.Unavailable -> UnavailableScreen(state, model)
            Screen.Home -> HomeScreen(state, model)
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
private fun HomeScreen(state: UiState, model: AppViewModel) {
    var confirmSignOut by remember { mutableStateOf(false) }
    Page {
        Title("Discair")
        Text("Connected. The dashboard arrives in the next phase.", style = MaterialTheme.typography.bodyLarge)
        CheckLine("Librarian", state.librarian)
        CheckLine("Navidrome", state.navidrome)
        Spacer(Modifier.weight(1f))
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
