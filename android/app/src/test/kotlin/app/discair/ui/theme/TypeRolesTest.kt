package app.discair.ui.theme

import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.ui.common.titleLetterSpacing
import org.junit.Assert.assertEquals
import org.junit.Test

/** The type roles of docs/redesign.md 7.2, checked on the default Discair pair. */
class TypeRolesTest {
    @Test fun bodySmallIsTwelveOverEighteen() {
        val small = typography(FontPairs.Discair).bodySmall
        assertEquals(12.sp, small.fontSize)
        assertEquals(18.sp, small.lineHeight)
    }

    @Test fun displayMetricIsTheHeavyNumeralAt64() {
        val metric = discairTypography(FontPairs.Discair).displayMetric
        assertEquals(64.sp, metric.fontSize)
        assertEquals(64.sp, metric.lineHeight)
        assertEquals(FontWeight.ExtraBold, metric.fontWeight)
    }

    @Test fun headlineSentenceIsSemiboldBodyAt20Over28() {
        val sentence = discairTypography(FontPairs.Discair).headlineSentence
        assertEquals(20.sp, sentence.fontSize)
        assertEquals(28.sp, sentence.lineHeight)
        assertEquals(FontWeight.SemiBold, sentence.fontWeight)
    }

    @Test fun titlesWithAGapTakeMinusSixHundredthsAndOneWordKeepsItsOwn() {
        // Compose has no word spacing, so a multi-word title is tightened instead (7.2).
        assertEquals((-0.06).em, titleLetterSpacing("Your library", (-0.085).em))
        assertEquals((-0.085).em, titleLetterSpacing("Library", (-0.085).em))
    }
}
