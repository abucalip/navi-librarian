package app.discair

import app.discair.data.FileResponseCache
import app.discair.data.LibrarianRepository
import app.discair.net.ConnectionException
import app.discair.net.ConnectionFailure
import app.discair.net.LibrarianClient
import java.io.IOException
import java.net.UnknownHostException
import java.nio.file.Files
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

/** Phase 5: saved copies answer only when the phone is offline, and a lost session is reported once credentials are refused. */
class OfflineReadTest {
    private class Net {
        var handler: (okhttp3.Request) -> Response = { error("no handler") }
        val paths = mutableListOf<String>()
        val client: OkHttpClient = OkHttpClient.Builder().addInterceptor(Interceptor { chain ->
            paths += chain.request().method + " " + chain.request().url.encodedPath
            handler(chain.request())
        }).build()
    }

    private fun reply(request: okhttp3.Request, code: Int, body: String) = Response.Builder()
        .request(request).protocol(Protocol.HTTP_1_1).code(code).message("m")
        .body(body.toResponseBody("application/json".toMediaType())).build()

    private fun repo(net: Net, onLost: () -> Unit = {}): LibrarianRepository {
        val cache = FileResponseCache(Files.createTempDirectory("c").toFile())
        return LibrarianRepository(LibrarianClient(net.client, "https://l.test", "u", "p", onLost), "https://l.test", cache)
    }

    private val picks = """{"items":[{"artist":"A","album":"B"}],"count":1}"""

    @Test fun anOfflineReadIsAnsweredFromTheLastGoodCopy() {
        val net = Net()
        val repo = repo(net)
        net.handler = { reply(it, 200, picks) }
        assertEquals("B", repo.picks(5).items.single().album)
        assertNull(repo.staleSince)

        net.handler = { throw UnknownHostException("l.test") }
        assertEquals("B", repo.picks(5).items.single().album)
        assertNotNull(repo.staleSince)

        net.handler = { reply(it, 200, picks) }
        repo.picks(5)
        assertNull(repo.staleSince) // reading live again clears the notice
    }

    @Test fun offlineWithNothingSavedStillFails() {
        val net = Net()
        val repo = repo(net)
        net.handler = { throw IOException("down") }
        try { repo.picks(5); fail() } catch (e: IOException) { assertNull(repo.staleSince) }
    }

    @Test fun differentRequestsAreSavedSeparately() {
        val net = Net()
        val repo = repo(net)
        net.handler = { reply(it, 200, picks) }
        repo.picks(5)
        net.handler = { throw IOException("down") }
        try { repo.picks(10); fail() } catch (e: IOException) { /* count=10 was never read */ }
    }

    @Test fun aServerErrorIsNeverHiddenBehindASavedCopy() {
        val net = Net()
        val repo = repo(net)
        net.handler = { reply(it, 200, picks) }
        repo.picks(5)
        net.handler = { reply(it, 500, """{"detail":"boom"}""") }
        try { repo.picks(5); fail() } catch (e: ConnectionException) {
            assertEquals(ConnectionFailure.Server(500, "boom"), e.failure)
        }
        assertNull(repo.staleSince)
    }

    @Test fun acquisitionStatusIsNeverServedFromTheCache() {
        val net = Net()
        val repo = repo(net)
        net.handler = { reply(it, 200, """{"acquisitions":[]}""") }
        repo.acquisitions()
        net.handler = { throw IOException("down") }
        try { repo.acquisitions(); fail() } catch (e: IOException) { /* must reflect the server now */ }
    }

    @Test fun refusedCredentialsOnReloginReportALostSession() {
        val net = Net()
        var lost = 0
        val repo = repo(net) { lost++ }
        net.handler = { req ->
            if (req.url.encodedPath.endsWith("/login")) reply(req, 401, """{"detail":"Invalid username or password."}""")
            else reply(req, 401, """{"detail":"Not signed in."}""")
        }
        try { repo.picks(5); fail() } catch (e: ConnectionException) { assertTrue(e.failure is ConnectionFailure.Unauthorised) }
        assertEquals(1, lost)
    }

    @Test fun aSuccessfulReloginRecoversWithoutReportingALostSession() {
        val net = Net()
        var lost = 0
        var signedIn = false
        val repo = repo(net) { lost++ }
        net.handler = { req ->
            when {
                req.url.encodedPath.endsWith("/login") -> { signedIn = true; reply(req, 200, "{}") }
                signedIn -> reply(req, 200, picks)
                else -> reply(req, 401, """{"detail":"Not signed in."}""")
            }
        }
        assertEquals(1, repo.picks(5).items.size)
        assertEquals(0, lost)
    }

    @Test fun anUnreachableServerDuringReloginIsNotALostSession() {
        val net = Net()
        var lost = 0
        val repo = repo(net) { lost++ }
        net.handler = { req ->
            if (req.url.encodedPath.endsWith("/login")) throw IOException("down") else reply(req, 401, "{}")
        }
        try { repo.picks(5); fail() } catch (e: IOException) { /* offline, no copy */ }
        assertEquals(0, lost)
    }
}
