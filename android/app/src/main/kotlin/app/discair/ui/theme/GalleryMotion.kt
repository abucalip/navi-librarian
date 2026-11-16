package app.discair.ui.theme

/*
 * Gallery's motion values (docs/GALLERY_THEME.md section 8, docs/design/gallery/tokens.json → motion). Pure, so they are unit-tested and pinned to the
 * tokens without a device. Every duration still goes through [MotionRules.duration] at the call site, so it becomes 0 when the phone removes animations.
 */
object GalleryMotion {
    /** cubic-bezier(0.3, 0, 0.1, 1): the shared print and the player's rise and fall. */
    val TRAVEL = Bezier(0.3f, 0f, 0.1f, 1f)

    /** cubic-bezier(0.2, 0.8, 0.2, 1): the rise of a page's blocks, the bar marker, the sheet and the snackbar. */
    val SETTLE = Bezier(0.2f, 0.8f, 0.2f, 1f)

    const val SHARED_COVER_MS = 420
    const val PLAYER_RISE_MS = 440
    const val PLAYER_FALL_MS = 360

    const val PAGE_FADE_OUT_MS = 180
    const val PAGE_FADE_IN_MS = 260
    const val PAGE_FADE_IN_DELAY_MS = 80

    /** The first [RISE_MAX_ITEMS] blocks of an arriving page rise [RISE_DP] over [RISE_MS], [RISE_STAGGER_MS] apart, after [RISE_START_MS]. */
    const val RISE_MS = 420
    const val RISE_DP = 10
    const val RISE_STAGGER_MS = 40
    const val RISE_MAX_ITEMS = 6

    /** The prototype starts the first block 120ms in (pages/motion), once the leaving page is mostly gone. */
    const val RISE_START_MS = 120

    const val NAV_MARKER_MS = 450

    /** Home's hero is a slideshow: a swipe settles, and the chevrons slide, to the next or previous album over [HERO_SLIDE_MS] on [TRAVEL]. */
    const val HERO_SLIDE_MS = 380

    const val SNACK_IN_MS = 280
    const val SNACK_DP = 14
    const val SNACK_HOLD_MS = 4000L

    /** The shared print's tween: 420ms on [TRAVEL]; 0ms when the phone removes animations. */
    fun sharedCover(reduced: Boolean): Timing = Timing(MotionRules.duration(SHARED_COVER_MS, MotionFamily.Standard, reduced), Curve.Curved(TRAVEL))

    /** The hero's slide: 380ms on [TRAVEL]; 0ms when the phone removes animations (the chevrons then change the album in place). */
    fun heroSlide(reduced: Boolean): Timing = Timing(MotionRules.duration(HERO_SLIDE_MS, MotionFamily.Standard, reduced), Curve.Curved(TRAVEL))

    /** How long the whole arrival runs: the last staggered block's start plus its rise. 0 when reduced. */
    fun arrivalMs(reduced: Boolean): Int = if (reduced) 0 else RISE_START_MS + RISE_STAGGER_MS * (RISE_MAX_ITEMS - 1) + RISE_MS

    /**
     * The linear progress (0 to 1) of block [index] when the page arrived [elapsedMs] ago. Blocks from [RISE_MAX_ITEMS] on do not rise (they arrive with the
     * page's fade), so they are always 1. The caller eases it with [SETTLE].
     */
    fun riseFraction(index: Int, elapsedMs: Float): Float {
        if (index < 0 || index >= RISE_MAX_ITEMS) return 1f
        val start = RISE_START_MS + RISE_STAGGER_MS * index
        return ((elapsedMs - start) / RISE_MS).coerceIn(0f, 1f)
    }
}
