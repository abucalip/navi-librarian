package app.discair

import app.discair.data.FileResponseCache
import app.discair.data.LibrarianRepository
import app.discair.net.LibrarianClient
import java.nio.file.Files
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

/** The Settings row for the server's resync-after-import option: live reads, a PUT with a boolean body. */
class LibraryResyncSettingTest {
    private val seen = mutableListOf<String>()
    private var reply = """{"library_resync_after_import":true}"""

    private fun repo(): LibrarianRepository {
        val http = OkHttpClient.Builder().addInterceptor(Interceptor { chain ->
            val request = chain.request()
            val body = request.body?.let { b -> okio.Buffer().also { b.writeTo(it) }.readUtf8() }.orEmpty()
            seen += request.method + " " + request.url.encodedPath + " " + body
            Response.Builder().request(request).protocol(Protocol.HTTP_1_1).code(200).message("m")
                .body(reply.toResponseBody("application/json".toMediaType())).build()
        }).build()
        val cache = FileResponseCache(Files.createTempDirectory("c").toFile())
        return LibrarianRepository(LibrarianClient(http, "https://l.test", "u", "p"), "https://l.test", cache)
    }

    @Test fun readsTheServerValue() {
        reply = """{"library_resync_after_import":false}"""
        assertFalse(repo().libraryResync())
        assertEquals("GET /api/settings/library-resync ", seen.last())
    }

    @Test fun anAbsentValueMeansOn() {
        reply = "{}"
        assertTrue(repo().libraryResync())
    }

    @Test fun writesABooleanWithPut() {
        reply = """{"ok":true,"library_resync_after_import":false}"""
        repo().setLibraryResync(false)
        assertEquals("""PUT /api/settings/library-resync {"library_resync_after_import":false}""", seen.last())
    }

    @Test fun aReplyThatIsNotOkIsAFailure() {
        reply = """{"ok":false}"""
        try { repo().setLibraryResync(true); fail() } catch (e: IllegalStateException) { /* the row reverts */ }
    }
}
