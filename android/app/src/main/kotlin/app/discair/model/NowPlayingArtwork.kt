package app.discair.model

/**
 * Now Playing artwork (docs/artwork.md, ideas 3 and 4): which Medium image is the disc, which images drift behind the lyrics, and the
 * timing rules for both. Chosen by type, comment and disc number only; never by taste or play data. Mirrors the macOS rules.
 */

private val DISC_NAME = Regex("""\b(?:disc|disk|cd)\s*(?:no\.?\s*)?0*(\d{1,2})\b""", RegexOption.IGNORE_CASE)

/** The disc number a comment or edition names ("Disc 2", "CD2", "disk 02"), or null. Plain string matching. */
fun namedDisc(text: String): Int? = DISC_NAME.find(text)?.groupValues?.get(1)?.toIntOrNull()

/**
 * The record Now Playing shows for the playing song's [disc]. The Medium image whose comment or edition names that disc wins;
 * otherwise the album's Medium slot, else the first Medium image, but never one that names a different disc. Null when the album
 * has no Medium image (or only PDFs).
 */
fun discImage(index: ArtworkIndex?, disc: Int?): ArtworkImage? {
    index ?: return null
    val media = index.images.filter { "Medium" in it.types && !it.isPdf }
    if (media.isEmpty()) return null
    fun named(p: ArtworkImage) = namedDisc(p.comment) ?: namedDisc(p.edition)
    if (disc != null && disc > 0) media.firstOrNull { named(it) == disc }?.let { return it }
    val usable = media.filter { p -> val other = named(p); disc == null || disc <= 0 || other == null || other == disc }
    val slot = index.slotImage("Medium")
    return if (slot != null && usable.any { it.imageId == slot.imageId }) slot else usable.firstOrNull()
}

const val SLIDESHOW_LIMIT = 12
private const val SLIDESHOW_MIN_SIDE = 400

/**
 * The images that drift behind the lyrics: booklet pages, then Other, Liner and Poster images, each once, never a PDF, nothing known
 * to be under 400 px, at most 12. Fewer than two is not a slideshow, so the list is empty and the blurred cover stays.
 */
fun slideshowImages(index: ArtworkIndex?): List<ArtworkImage> {
    index ?: return emptyList()
    val extras = index.images.filter { p -> p.types.any { it == "Other" || it == "Liner" || it == "Poster" } }
    val seen = HashSet<Long>()
    val found = (index.bookletImages() + extras).filter { p ->
        if (p.isPdf || !seen.add(p.imageId)) return@filter false
        val w = p.width
        val h = p.height
        !(w != null && h != null && maxOf(w, h) < SLIDESHOW_MIN_SIDE)
    }
    return if (found.size >= 2) found.take(SLIDESHOW_LIMIT) else emptyList()
}

/** Slide [index] is shown, cross-fading into [next] over the last `fade` seconds of its `hold`; [progress] (0..1) drives the slow drift. */
data class SlideshowFrame(val index: Int, val next: Int, val mix: Float, val progress: Float)

fun slideshowFrame(elapsedSeconds: Double, count: Int, hold: Double = 14.0, fade: Double = 3.0): SlideshowFrame? {
    if (count <= 0 || hold <= 0) return null
    val t = maxOf(0.0, elapsedSeconds)
    val slot = (t / hold).toInt()
    val within = t - slot * hold
    val fadeStart = maxOf(0.0, hold - fade)
    val mix = if (fade > 0 && within > fadeStart) minOf(1.0, (within - fadeStart) / fade) else 0.0
    return SlideshowFrame(slot % count, (slot + 1) % count, mix.toFloat(), (within / hold).toFloat())
}
