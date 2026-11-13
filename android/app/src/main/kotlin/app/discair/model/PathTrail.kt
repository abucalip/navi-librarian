package app.discair.model

/*
 * The Trail layout of the Paths sheets (docs/pathsredesign.md, sections 5 and 9). Pure functions, no Compose: the link
 * of a step (what connects it to the start), and the grouping of steps under their links. Both sheets use them.
 */

/**
 * What connects a step to the start: the person, label, work, place or record it goes through ([name]) and what that
 * link is ([kind], lower case: "same label"). A step whose first reason names nothing to link through has no [name]
 * and shows its kind alone.
 */
data class TrailLink(val name: String?, val kind: String) {
    /** The pill's words: "Fred Plaut · production credit", or "Production credit" when there is no name. */
    val text: String get() = name?.let { "$it · $kind" } ?: kind.replaceFirstChar { it.uppercaseChar() }

    /** What TalkBack reads: "Fred Plaut, production credit". */
    val spoken: String get() = name?.let { "$it, $kind" } ?: text
}

/** A step and its place in the server's list. [index] is what the sheet saves, so a step is found again after grouping. */
data class TrailStep<T>(val index: Int, val item: T)

/** The steps that share one link, in the server's order. */
data class TrailGroup<T>(val link: TrailLink, val steps: List<TrailStep<T>>)

/**
 * Steps with the same link text and kind form one group. Groups appear in the order of their first step in the
 * server's answer; steps keep the server's order inside a group (decision D1: a step can move up to join its group).
 */
fun <T> groupByLink(items: List<T>, linkOf: (T) -> TrailLink): List<TrailGroup<T>> {
    val groups = LinkedHashMap<TrailLink, MutableList<TrailStep<T>>>()
    items.forEachIndexed { index, item -> groups.getOrPut(linkOf(item)) { mutableListOf() } += TrailStep(index, item) }
    return groups.map { (link, steps) -> TrailGroup(link, steps) }
}

/** One line of the trail as the list draws it: a link, or a step under it. */
sealed interface TrailEntry<out T> {
    /** [first] is the first line of the trail, which has no gap above it. */
    data class Link(val link: TrailLink, val first: Boolean) : TrailEntry<Nothing>

    /** [last] is the last step of the whole trail, where the line ends at its elbow. */
    data class Step<T>(val step: TrailStep<T>, val last: Boolean) : TrailEntry<T>
}

/** Each group's link, then its steps, in the order the trail shows them. */
fun <T> List<TrailGroup<T>>.entries(): List<TrailEntry<T>> {
    val lastIndex = lastOrNull()?.steps?.lastOrNull()?.index
    return flatMapIndexed { n, group ->
        listOf<TrailEntry<T>>(TrailEntry.Link(group.link, first = n == 0)) +
            group.steps.map { TrailEntry.Step(it, last = it.index == lastIndex) }
    }
}

/** The steps of [groups] in the order the trail shows them. */
fun <T> List<TrailGroup<T>>.shownOrder(): List<TrailStep<T>> = flatMap { it.steps }

/** The role of a studio credit, from the relation the server stored for it (decision D5); "production credit" when it names none. */
internal fun crewKind(relation: String?): String = when (relation) {
    "producer" -> "producer credit"
    "engineer" -> "engineer credit"
    "mix" -> "mixing credit"
    "mastering" -> "mastering credit"
    else -> "production credit"
}

private fun sameYearKind(code: String) = when (code) {
    "same_period_label" -> "same label"
    "same_period_area" -> "same area"
    "same_period_credit" -> "shared artist"
    else -> reasonEyebrow(code).lowercase()
}

/**
 * The link of an album step, from its first reason so the list is stable. [seeds] is how many of the start's tracks
 * Neighbours by ear used (the answer's `seeds`).
 */
fun AlbumStep.trailLink(tab: AlbumTab, seeds: Int = 0): TrailLink {
    val reason = reasons.firstOrNull()
    val via = reason?.via?.name?.takeIf { it.isNotBlank() }
    val code = reason?.code.orEmpty()
    return when (tab) {
        AlbumTab.StudioCrew -> TrailLink(via, crewKind(reason?.credits?.firstOrNull()?.relation))
        AlbumTab.GuestList -> TrailLink(via, "guest credit")
        AlbumTab.CoversAndSources -> TrailLink(via, if (code == "derived_work") "related work" else "same work")
        AlbumTab.SameYearSameScene -> TrailLink(via, sameYearKind(code))
        AlbumTab.SameRoom -> TrailLink(via, "recorded at")
        AlbumTab.ListenThroughGaps -> TrailLink(via, reasonEyebrow(code).lowercase())
        AlbumTab.NeighboursByEar -> TrailLink(
            if (seeds > 0) "$matchCount of $seeds tracks" else "$matchCount ${if (matchCount == 1) "track" else "tracks"}",
            "sound alike",
        )
    }
}

/**
 * The link of an artist step, from its first reason. [startName] is the artist the sheet started from (Composition says
 * "composed by" them).
 */
fun PathStop.trailLink(kind: PathKind, startName: String = ""): TrailLink {
    val reason = reasons.firstOrNull()
    val via = reason?.via
    return when (kind) {
        PathKind.FollowTheMusician -> TrailLink(via?.takeIf { it.isArtist }?.name?.takeIf { it.isNotBlank() }, "musician")
        PathKind.SidemanToLeader -> TrailLink(via?.takeIf { it.type == "release" }?.name?.takeIf { it.isNotBlank() }, "a record they led")
        PathKind.LabelPath -> TrailLink(via?.name?.takeIf { it.isNotBlank() }, if (reason?.code?.startsWith("related") == true) "related label" else "same label")
        PathKind.CompositionPath -> TrailLink(
            via?.name?.takeIf { it.isNotBlank() },
            if (reason?.code?.startsWith("related") == true) "related work" else if (startName.isNotBlank()) "composed by $startName" else "same work",
        )
        PathKind.ScenePath -> TrailLink(via?.name?.takeIf { it.isNotBlank() }, "same place")
    }
}
