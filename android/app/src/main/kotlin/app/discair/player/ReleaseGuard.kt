package app.discair.player

/** Runs a release action at most once, so the service can release from several paths safely. */
class ReleaseGuard(private val action: () -> Unit) {
    private var released = false

    @Synchronized
    fun release() {
        if (released) return
        released = true
        action()
    }

    val isReleased: Boolean @Synchronized get() = released
}
