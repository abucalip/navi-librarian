package app.discair.net

import android.content.SharedPreferences
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl

/**
 * Keeps the Librarian session cookie across restarts. Backed by encrypted preferences,
 * so the cookie is as protected as the credentials. Expired cookies are dropped on read.
 */
class PersistentCookieJar(private val prefs: SharedPreferences) : CookieJar {
    private val lock = Any()

    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) = synchronized(lock) {
        val edit = prefs.edit()
        for (cookie in cookies) {
            val key = "${cookie.domain}|${cookie.path}|${cookie.name}"
            if (cookie.expiresAt <= System.currentTimeMillis()) edit.remove(key)
            else edit.putString(key, cookie.toString())
        }
        edit.apply()
    }

    override fun loadForRequest(url: HttpUrl): List<Cookie> = synchronized(lock) {
        val now = System.currentTimeMillis()
        val live = mutableListOf<Cookie>()
        val edit = prefs.edit()
        for ((key, value) in prefs.all) {
            val cookie = (value as? String)?.let { Cookie.parse(url, it) }
            when {
                cookie == null || cookie.expiresAt <= now -> edit.remove(key)
                cookie.matches(url) -> live += cookie
            }
        }
        edit.apply()
        live
    }

    fun clear() = synchronized(lock) { prefs.edit().clear().apply() }
}
