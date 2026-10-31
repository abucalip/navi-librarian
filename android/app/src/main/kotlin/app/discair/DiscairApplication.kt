package app.discair

import android.app.Application

class DiscairApplication : Application() {
    val container: AppContainer by lazy { AppContainer(this) }
}
