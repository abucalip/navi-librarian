package app.discair.player

/**
 * The short quality tag shown on the player: "320Kbps" for MP3 (no file type), "FLAC 24/96" for lossless.
 * Describes the file in the library, not the stream when the quality setting transcodes it. Null when unknown.
 */
fun qualityLabel(item: QueueItem): String? {
    val suffix = item.suffix.trim().lowercase()
    val lossless = suffix in setOf("flac", "alac", "wav", "aiff", "aif", "ape", "wv")
    if (lossless) {
        val name = suffix.uppercase()
        val depth = item.bitDepth
        val rate = item.samplingRateHz
        return when {
            depth != null && rate != null -> "$name $depth/${khz(rate)}"
            depth != null -> "$name $depth"
            else -> name
        }
    }
    val kbps = item.bitRateKbps ?: return null
    return if (suffix == "mp3" || suffix.isEmpty()) "${kbps}Kbps" else "${suffix.uppercase()} ${kbps}Kbps"
}

private fun khz(hz: Int): String {
    val tenths = (hz + 50) / 100
    return if (tenths % 10 == 0) "${tenths / 10}" else "${tenths / 10}.${tenths % 10}"
}
