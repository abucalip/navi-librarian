package app.discair.ui.theme

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Motion kit (docs/redesign.md 7.4, step A2): the token table, the per-family scaling and the reduced-motion rules. */
class MotionTest {
    private val standard = MotionFamily.Standard
    private val tape = MotionFamily.Tape
    private val sheet = MotionFamily.Sheet

    @Test fun tokensEqualTheTable() {
        assertEquals(100, MotionTokens.FAST_MS)
        assertEquals(200, MotionTokens.BASE_MS)
        assertEquals(300, MotionTokens.ENTER_MS)
        assertEquals(400, MotionTokens.EMPHASIS_MS)
        assertEquals(350, MotionTokens.SHEET_MS)
        assertEquals(Bezier(0.05f, 0.7f, 0.1f, 1f), MotionTokens.EASE_ENTER)
        assertEquals(Bezier(0.3f, 0f, 0.8f, 0.15f), MotionTokens.EASE_EXIT)
        assertEquals(Bezier(0.2f, 0f, 0f, 1f), MotionTokens.EASE_STANDARD)
        assertEquals(0.8f, MotionTokens.SPRING_DAMPING, 0f)
        assertEquals(380f, MotionTokens.SPRING_STIFFNESS, 0f)
    }

    @Test fun standardTimingsUseTheirTokenAndCurve() {
        assertEquals(Timing(300, Curve.Curved(MotionTokens.EASE_ENTER)), MotionRules.timing(MotionTokens.ENTER_MS, MotionRole.Arrive, standard, false))
        assertEquals(Timing(100, Curve.Curved(MotionTokens.EASE_EXIT)), MotionRules.timing(MotionTokens.FAST_MS, MotionRole.Leave, standard, false))
        assertEquals(Timing(200, Curve.Curved(MotionTokens.EASE_STANDARD)), MotionRules.timing(MotionTokens.BASE_MS, MotionRole.Move, standard, false))
    }

    @Test fun easeExitRunsForTwoThirdsOfTheEnterTime() {
        assertEquals(200, MotionRules.exitDuration(300))
        assertEquals(267, MotionRules.exitDuration(400))
        assertEquals(233, MotionRules.exitDuration(350))
    }

    @Test fun tapeRunsEveryDurationAtSixtyPercentAndIsLinear() {
        assertEquals(60, MotionRules.duration(MotionTokens.FAST_MS, tape, false))
        assertEquals(120, MotionRules.duration(MotionTokens.BASE_MS, tape, false))
        assertEquals(180, MotionRules.duration(MotionTokens.ENTER_MS, tape, false))
        assertEquals(240, MotionRules.duration(MotionTokens.EMPHASIS_MS, tape, false))
        assertEquals(210, MotionRules.duration(MotionTokens.SHEET_MS, tape, false))
        for (role in MotionRole.entries) assertEquals(Curve.Linear, MotionRules.curve(role, tape))
        assertEquals(Timing(120, Curve.Linear), MotionRules.timing(MotionRules.exitDuration(MotionTokens.ENTER_MS), MotionRole.Leave, tape, false))
    }

    @Test fun sheetKeepsTheStandardDurationsAndSpringsMoreOnEntry() {
        assertEquals(300, MotionRules.duration(MotionTokens.ENTER_MS, sheet, false))
        assertEquals(SpringSpec(0.7f, 380f), MotionRules.spring(sheet, entering = true, reduced = false))
        assertEquals(SpringSpec(0.8f, 380f), MotionRules.spring(sheet, entering = false, reduced = false))
        assertEquals(SpringSpec(0.8f, 380f), MotionRules.spring(standard, entering = true, reduced = false))
    }

    @Test fun tapeHasNoOvershoot() {
        assertEquals(SpringSpec(1f, 380f), MotionRules.spring(tape, entering = true, reduced = false))
        assertEquals(SpringSpec(1f, 380f), MotionRules.spring(tape, entering = false, reduced = false))
    }

    @Test fun layoutsMapToTheirFamilyAndTheStickerWallTakesTheStandardOne() {
        assertEquals(MotionFamily.Standard, MotionRules.familyFor(Layout.Standard))
        assertEquals(MotionFamily.Tape, MotionRules.familyFor(Layout.TapeDeck))
        assertEquals(MotionFamily.Sheet, MotionRules.familyFor(Layout.SheetStack))
        assertEquals(MotionFamily.Standard, MotionRules.familyFor(Layout.StickerWall))
    }

    @Test fun staggerWaitsFiftyMillisecondsForTheFirstFourOnly() {
        assertEquals(listOf(0, 50, 100, 150), (0..3).map { MotionRules.staggerDelayMs(it, standard, false) })
        assertEquals(0, MotionRules.staggerDelayMs(4, standard, false))
        assertEquals(0, MotionRules.staggerDelayMs(9, standard, false))
        assertEquals(listOf(0, 30, 60, 90), (0..3).map { MotionRules.staggerDelayMs(it, tape, false) })
        assertEquals(0, MotionRules.staggerDelayMs(-1, standard, false))
    }

    @Test fun fadeThroughFadesOutFirstThenRisesInSixteenDp() {
        val plan = MotionPlans.fadeThrough(standard, reduced = false)
        assertEquals(Timing(100, Curve.Curved(MotionTokens.EASE_EXIT)), plan.leave)
        assertEquals(Timing(200, Curve.Curved(MotionTokens.EASE_ENTER)), plan.arrive)
        assertEquals(100, plan.arriveDelayMs)
        assertEquals(16, plan.riseDp)
    }

    @Test fun fadeThroughOnTapeFollowsTheSixtyPercentTimes() {
        val plan = MotionPlans.fadeThrough(tape, reduced = false)
        assertEquals(60, plan.leave.durationMs)
        assertEquals(120, plan.arrive.durationMs)
        assertEquals(60, plan.arriveDelayMs)
    }

    @Test fun sharedAxisSlidesThirtyDpOnEnterAndLeavesOverTwoThirdsOfTheTime() {
        val plan = MotionPlans.sharedAxisX(standard, reduced = false)
        assertEquals(Timing(300, Curve.Curved(MotionTokens.EASE_ENTER)), plan.arrive)
        assertEquals(Timing(200, Curve.Curved(MotionTokens.EASE_EXIT)), plan.leave)
        assertEquals(30, plan.slideDp)
        val tapePlan = MotionPlans.sharedAxisX(tape, reduced = false)
        assertEquals(180, tapePlan.arrive.durationMs)
        assertEquals(120, tapePlan.leave.durationMs)
    }

    @Test fun reducedMotionStopsEveryPlanInEveryFamily() {
        for (family in MotionFamily.entries) {
            for (role in MotionRole.entries) assertEquals(0, MotionRules.timing(MotionTokens.EMPHASIS_MS, role, family, reduced = true).durationMs)
            assertNull(MotionRules.spring(family, entering = true, reduced = true))
            assertNull(MotionRules.spring(family, entering = false, reduced = true))
            for (index in 0..5) assertEquals(0, MotionRules.staggerDelayMs(index, family, reduced = true))
            assertEquals(0, MotionRules.riseDp(reduced = true))
            assertEquals(0, MotionRules.slideDp(reduced = true))

            val fade = MotionPlans.fadeThrough(family, reduced = true)
            assertEquals(0, fade.leave.durationMs)
            assertEquals(0, fade.arrive.durationMs)
            assertEquals(0, fade.arriveDelayMs)
            assertEquals(0, fade.riseDp)

            val axis = MotionPlans.sharedAxisX(family, reduced = true)
            assertEquals(0, axis.arrive.durationMs)
            assertEquals(0, axis.leave.durationMs)
            assertEquals(0, axis.slideDp)
        }
    }

    @Test fun everyTimingIsPositiveWhenNotReduced() {
        for (family in MotionFamily.entries) for (token in listOf(MotionTokens.FAST_MS, MotionTokens.BASE_MS, MotionTokens.ENTER_MS, MotionTokens.EMPHASIS_MS, MotionTokens.SHEET_MS)) {
            for (role in MotionRole.entries) assertTrue(MotionRules.timing(token, role, family, reduced = false).durationMs > 0)
        }
    }

    @Test fun sharedCoverGrowsOverEnterOnTheStandardCurve() {
        assertEquals(Timing(300, Curve.Curved(MotionTokens.EASE_STANDARD)), MotionPlans.sharedCover(standard, false)?.bounds)
        assertEquals(Timing(300, Curve.Curved(MotionTokens.EASE_STANDARD)), MotionPlans.sharedCover(sheet, false)?.bounds)
        assertEquals(Timing(180, Curve.Linear), MotionPlans.sharedCover(tape, false)?.bounds)
    }

    @Test fun sharedCoverIsOffWhenMotionIsReduced() {
        for (family in MotionFamily.entries) assertNull(MotionPlans.sharedCover(family, true))
    }
}
