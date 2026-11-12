package app.discair.ui

import app.discair.ui.theme.Layout

/**
 * Pure rules for where the four destinations (Home, Discover, Library, Search) and the now-playing button sit in each layout
 * (docs/design/redesign section 7.1), apart from the drawing so they are unit-tested.
 */
object NavRules {
    /** The four destinations, in the order every layout draws them. Search opens a sheet; the other three are pages. */
    val destinations: List<String> = listOf("Home", "Discover", "Library", "Search")

    /** Width class: from this many dp the bottom navigation becomes a navigation rail. */
    const val RAIL_MIN_DP = 600

    fun railShown(widthDp: Int): Boolean = widthDp >= RAIL_MIN_DP

    /** The Cassette Deck's ruled bar and the Cover Stack's outlined bar carry all four destinations. Every other layout keeps Discover in the top bar. */
    fun discoverInBar(layout: Layout): Boolean = layout == Layout.TapeDeck || layout == Layout.CoverStack

    /** Discover sits in the top bar where the bar and the rail do not already carry it. */
    fun discoverInTopBar(layout: Layout, rail: Boolean): Boolean = !rail && !discoverInBar(layout)

    /**
     * The now-playing button stays in the navigation where the layout has no mini player. The Cassette Deck has its mini
     * player above the bar instead, so its bar has no player cell; so has the Cover Stack.
     */
    fun playerButtonShown(layout: Layout): Boolean = layout != Layout.TapeDeck && layout != Layout.CoverStack
}
