package app.discair.player.crossfade

/**
 * The words and small rules of the Crossfade page (ANDROID_CROSSFADE_CONTRACT.md 7), with no Android types so they
 * are tested in plain Kotlin. The page never shows state by colour alone: every state has words here.
 */
object CrossfadeText {
    /** "1 second", "5 seconds". */
    fun length(seconds: Int): String {
        val s = CrossfadeSettings.sanitizeSeconds(seconds)
        return if (s == 1) "1 second" else "$s seconds"
    }

    /** What TalkBack reads for the length control. */
    fun lengthSpoken(seconds: Int): String = "Crossfade length, ${length(seconds)}"

    /** The Settings row's second line. */
    fun summary(s: CrossfadeSettings): String = if (!s.enabled) "Off" else length(CrossfadeSettings.sanitizeSeconds(s.seconds))

    /** The Now Playing link: shown only while crossfade is on, so the state can be read without opening the page. */
    fun nowPlayingLink(s: CrossfadeSettings): String? =
        if (s.enabled) "Crossfade: ${CrossfadeSettings.sanitizeSeconds(s.seconds)} s" else null

    /** The switch row's help text. */
    fun switchHelp(enabled: Boolean): String =
        if (enabled) "On. The end of one song fades into the start of the next. Skipping a song yourself is not faded."
        else "Off. Songs follow each other as they do now. Turn it on to choose a length."

    fun keepAlbumsHelp(keep: Boolean): String =
        if (keep) "On. Songs that follow each other on one album play without a fade, so live and continuous albums stay seamless."
        else "Off. Songs on one album fade into each other too."

    /** Shown only when the stream is converted: such a stream can still be faded, but only if the server tells the song's length. */
    fun qualityLine(maxBitRate: Int?): String? =
        if (maxBitRate == null) null
        else "Streaming quality is below Original. A converted song can be crossfaded, but a song whose length the server cannot tell is played without a fade."

    /** One press of minus or plus; stops at the ends. */
    fun nudge(seconds: Int, delta: Int): Int = CrossfadeSettings.sanitizeSeconds(CrossfadeSettings.sanitizeSeconds(seconds) + delta)

    fun canLower(seconds: Int) = CrossfadeSettings.sanitizeSeconds(seconds) > CrossfadeSettings.MIN_SECONDS
    fun canRaise(seconds: Int) = CrossfadeSettings.sanitizeSeconds(seconds) < CrossfadeSettings.MAX_SECONDS

    /** A slider position (any float) as a whole number of seconds in range. */
    fun fromSlider(value: Float): Int =
        CrossfadeSettings.sanitizeSeconds(if (value.isNaN()) null else Math.round(value))
}
