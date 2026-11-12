package app.discair.ui.common

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** The confirmation sheet's actions (docs/redesign.md 7.2, step A5): safe first and outlined, destructive named, nothing before confirm. */
class ConfirmSheetTest {
    @Test fun theSafeActionIsDrawnFirstForEveryConfirmation() {
        listOf(
            ConfirmSpecs.dismissJob("Kind of Blue"),
            ConfirmSpecs.dismissImports(3),
            ConfirmSpecs.signOut(),
        ).forEach { spec ->
            val actions = ConfirmRules.actions(spec)
            assertEquals(2, actions.size)
            assertTrue("first action must be the safe one: $actions", actions[0] is ConfirmAction.Keep)
            assertTrue("second action must be the destructive one: $actions", actions[1] is ConfirmAction.Delete)
        }
    }

    @Test fun dismissingOneRecordNamesTheAlbumInTheDestructiveLabel() {
        val spec = ConfirmSpecs.dismissJob("Kind of Blue")
        assertEquals("Dismiss Kind of Blue?", spec.title)
        assertEquals("Remove Kind of Blue and its files", spec.destructiveLabel)
        assertEquals("Keep it", spec.safeLabel)
    }

    @Test fun dismissingImportsCountsThemInWords() {
        assertEquals("Dismiss 1 import?", ConfirmSpecs.dismissImports(1).title)
        val many = ConfirmSpecs.dismissImports(3)
        assertEquals("Dismiss 3 imports?", many.title)
        assertEquals("Remove 3 imports and their files", many.destructiveLabel)
    }

    @Test fun signOutNamesWhatIsErased() {
        val spec = ConfirmSpecs.signOut()
        assertTrue(spec.destructiveLabel.contains("server details"))
        assertTrue(spec.message.contains("passwords"))
        assertEquals("Keep me signed in", spec.safeLabel)
    }

    @Test fun theDestructiveLabelIsNeverEmptyOrGeneric() {
        listOf(ConfirmSpecs.dismissJob("X"), ConfirmSpecs.dismissImports(2), ConfirmSpecs.signOut()).forEach { spec ->
            assertTrue(spec.destructiveLabel.length > "Dismiss".length)
        }
    }

    @Test fun resettingTheEqualizerKeepsTheCurveFirstAndNamesWhatIsErased() {
        val spec = ConfirmSpecs.resetEqualizer()
        val actions = ConfirmRules.actions(spec)
        assertTrue(actions.first() is ConfirmAction.Keep)
        assertTrue(spec.destructiveLabel.contains("Custom curve"))
    }
}
