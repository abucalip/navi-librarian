package app.discair.ui.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import app.discair.model.ListenBrainzAccount
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OutlinedTextField
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * The ListenBrainz account. It lives on the server (taste, popularity and insights all read it there), so this reads it live
 * and writes it back; the token is write-only and is never shown again.
 */
@Composable
fun ListenBrainzSettings() {
    val repo = LocalRepository.current
    val scope = rememberCoroutineScope()
    var account by remember { mutableStateOf<ListenBrainzAccount?>(null) }
    var username by remember { mutableStateOf("") }
    var token by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var note by remember { mutableStateOf<String?>(null) }
    var failed by remember { mutableStateOf(false) }

    LaunchedEffect(repo) {
        try {
            val a = withContext(Dispatchers.IO) { repo.listenBrainz() }
            account = a
            if (username.isBlank()) username = a.username
        } catch (e: Exception) {
            failed = true
            note = "Could not read this from the server."
        }
    }

    Column(Modifier.fillMaxWidth().padding(top = 16.dp)) {
        Text("ListenBrainz", style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
        val a = account
        Text(
            if (a?.connected == true) "Connected as ${a.username}${if (a.tokenConfigured) " (token saved)" else ""}." else "Not connected. Taste needs a ListenBrainz account.",
            style = MaterialTheme.typography.bodyMedium,
        )
        Spacer(Modifier.size(8.dp))
        OutlinedTextField(
            value = username, onValueChange = { username = it }, label = { Text("ListenBrainz username") },
            singleLine = true, modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Ascii, autoCorrectEnabled = false),
        )
        Spacer(Modifier.size(8.dp))
        OutlinedTextField(
            value = token, onValueChange = { token = it },
            label = { Text(if (a?.tokenConfigured == true) "Token (saved; leave blank to keep)" else "Token (optional)") },
            singleLine = true, modifier = Modifier.fillMaxWidth(),
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, autoCorrectEnabled = false),
        )
        TextButton(
            onClick = {
                busy = true; note = null; failed = false
                scope.launch {
                    try {
                        val check = withContext(Dispatchers.IO) { repo.connectListenBrainz(username, token) }
                        token = ""
                        account = withContext(Dispatchers.IO) { repo.listenBrainz() }
                        failed = !check.ok
                        note = if (check.ok) "Connected as ${account?.username}." else "Saved, but ${check.message.replaceFirstChar { it.lowercase() }}"
                    } catch (e: Exception) {
                        failed = true
                        note = e.message ?: "The server did not save this. Try again."
                    }
                    busy = false
                }
            },
            enabled = !busy && username.isNotBlank(),
            modifier = Modifier.heightIn(min = 48.dp),
        ) { Text(if (a?.connected == true) "Update" else "Connect") }
        note?.let {
            Text(it, style = MaterialTheme.typography.bodySmall, color = if (failed) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Text(
            "The server reads your listens from ListenBrainz to describe your taste. A username is enough for public listens; the token is only for private profiles.",
            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
