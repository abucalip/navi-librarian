package app.discair.data

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/** Everything the user typed on the setup screen. */
data class ServerSettings(
    val librarianUrl: String = "",
    val librarianUser: String = "",
    val librarianPassword: String = "",
    val navidromeUrl: String = "",
    val navidromeUser: String = "",
    val navidromePassword: String = "",
) {
    val isComplete: Boolean
        get() = listOf(
            librarianUrl, librarianUser, librarianPassword,
            navidromeUrl, navidromeUser, navidromePassword,
        ).all { it.isNotBlank() }
}

interface SettingsStore {
    fun load(): ServerSettings
    fun save(settings: ServerSettings)
    fun clear()
}

/** Settings and the session cookie live only in Keystore-backed encrypted preferences. */
object EncryptedPrefs {
    fun open(context: Context, name: String): SharedPreferences {
        val key = MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
        return EncryptedSharedPreferences.create(
            context, name, key,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }
}

class CredentialStore(private val prefs: SharedPreferences) : SettingsStore {
    override fun load() = ServerSettings(
        librarianUrl = prefs.getString(LIBRARIAN_URL, "").orEmpty(),
        librarianUser = prefs.getString(LIBRARIAN_USER, "").orEmpty(),
        librarianPassword = prefs.getString(LIBRARIAN_PASSWORD, "").orEmpty(),
        navidromeUrl = prefs.getString(NAVIDROME_URL, "").orEmpty(),
        navidromeUser = prefs.getString(NAVIDROME_USER, "").orEmpty(),
        navidromePassword = prefs.getString(NAVIDROME_PASSWORD, "").orEmpty(),
    )

    override fun save(settings: ServerSettings) {
        prefs.edit()
            .putString(LIBRARIAN_URL, settings.librarianUrl)
            .putString(LIBRARIAN_USER, settings.librarianUser)
            .putString(LIBRARIAN_PASSWORD, settings.librarianPassword)
            .putString(NAVIDROME_URL, settings.navidromeUrl)
            .putString(NAVIDROME_USER, settings.navidromeUser)
            .putString(NAVIDROME_PASSWORD, settings.navidromePassword)
            .apply()
    }

    override fun clear() {
        prefs.edit().clear().apply()
    }

    private companion object {
        const val LIBRARIAN_URL = "librarian_url"
        const val LIBRARIAN_USER = "librarian_user"
        const val LIBRARIAN_PASSWORD = "librarian_password"
        const val NAVIDROME_URL = "navidrome_url"
        const val NAVIDROME_USER = "navidrome_user"
        const val NAVIDROME_PASSWORD = "navidrome_password"
    }
}
