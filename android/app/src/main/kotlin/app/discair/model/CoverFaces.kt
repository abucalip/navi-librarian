package app.discair.model

/**
 * The faces behind an album cover that can be flipped to (docs/artwork.md, idea 1): the best Back, then Tray, then Spine.
 * The front is the cover the page already shows. Each is the server's slot image, so the choice is by explicit rule (type and
 * approval, never taste or play data). An album with no Back image has no faces: the cover does not flip, even with a Tray
 * or Spine, because those are extras on a flipped cover, not a cover of their own.
 */
fun coverBackFaces(index: ArtworkIndex?): List<ArtworkImage> {
    index ?: return emptyList()
    val back = index.slotImage("Back") ?: return emptyList()
    return listOfNotNull(back, index.slotImage("Tray"), index.slotImage("Spine")).distinctBy { it.imageId }
}

/** Which face shows after [steps] flips on a card with [backs] back faces: 0 is the front. Negative steps (the other swipe direction) wrap. */
fun faceAfter(steps: Int, backs: Int): Int = if (backs <= 0) 0 else Math.floorMod(steps, backs + 1)
