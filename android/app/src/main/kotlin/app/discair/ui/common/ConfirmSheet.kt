package app.discair.ui.common

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/*
 * The confirmation bottom sheet (docs/redesign.md 7.2, step A5). It replaces the centred dialogs for the two
 * destructive confirmations: Dismiss on Downloads and Sign out. The rules are pure so they are unit-tested
 * without a device: [ConfirmSpecs] writes the words and [ConfirmRules] fixes the order the actions are drawn in.
 */

/** Everything one confirmation says: the question, the sentence under it, the safe label and the destructive label. */
data class ConfirmSpec(val title: String, val message: String, val safeLabel: String, val destructiveLabel: String)

/** One button on the sheet. [Keep] is the safe action (outlined); [Delete] is the destructive one (danger-labelled). */
sealed interface ConfirmAction {
    val label: String

    data class Keep(override val label: String) : ConfirmAction
    data class Delete(override val label: String) : ConfirmAction
}

object ConfirmRules {
    /** The safe action comes first and is outlined; the destructive one sits below it, so a stray tap lands on Keep. */
    fun actions(spec: ConfirmSpec): List<ConfirmAction> = listOf(
        ConfirmAction.Keep(spec.safeLabel),
        ConfirmAction.Delete(spec.destructiveLabel),
    )
}

object ConfirmSpecs {
    private const val DISMISS_SENTENCE =
        "This removes the record and deletes the downloaded files the server identifies for it. " +
            "The server refuses if it cannot do that safely."

    /** Dismiss one acquisition record. The destructive label names the album or song whose files go. */
    fun dismissJob(title: String) = ConfirmSpec(
        title = "Dismiss $title?",
        message = DISMISS_SENTENCE,
        safeLabel = "Keep it",
        destructiveLabel = "Remove $title and its files",
    )

    /** Dismiss every successful import at once. */
    fun dismissImports(count: Int) = ConfirmSpec(
        title = "Dismiss ${plural(count, "import")}?",
        message = DISMISS_SENTENCE,
        safeLabel = "Keep them",
        destructiveLabel = "Remove ${plural(count, "import")} and their files",
    )

    /** Reset the equalizer to flat; the destructive label says what is erased. */
    fun resetEqualizer() = ConfirmSpec(
        title = "Reset the equalizer?",
        message = "All bands go back to 0 dB and your Custom curve is erased. The presets are not changed.",
        safeLabel = "Keep my curve",
        destructiveLabel = "Reset and erase my Custom curve",
    )

    /** Sign out forgets the server logins on this phone; the destructive label says exactly that. */
    fun signOut() = ConfirmSpec(
        title = "Sign out of Discair?",
        message = "This removes both server addresses, user names and passwords from this phone. You will have to enter them again.",
        safeLabel = "Keep me signed in",
        destructiveLabel = "Sign out and delete server details",
    )
}

/**
 * The confirmation sheet. Nothing is sent by it until [onConfirm] runs, which only the destructive button and
 * nothing else calls. Swiping the sheet away or tapping the scrim is the same as Keep.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConfirmSheet(spec: ConfirmSpec, onKeep: () -> Unit, onConfirm: () -> Unit) {
    ModalBottomSheet(
        onDismissRequest = onKeep,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
    ) {
        Column(
            Modifier.fillMaxWidth().padding(start = 24.dp, end = 24.dp, bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text(spec.title, style = MaterialTheme.typography.titleLarge)
            Text(spec.message, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            ConfirmRules.actions(spec).forEach { action ->
                when (action) {
                    is ConfirmAction.Keep -> OutlinedButton(onClick = onKeep, modifier = Modifier.fillMaxWidth().heightIn(min = Target)) {
                        Text(action.label)
                    }
                    is ConfirmAction.Delete -> TextButton(onClick = onConfirm, modifier = Modifier.fillMaxWidth().heightIn(min = Target)) {
                        Text(action.label, color = MaterialTheme.colorScheme.error)
                    }
                }
            }
        }
    }
}
