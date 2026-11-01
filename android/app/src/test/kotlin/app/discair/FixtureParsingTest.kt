package app.discair

import app.discair.net.ConnectionFailure
import app.discair.net.Subsonic
import app.discair.net.errorDetail
import app.discair.net.parseSetupRequired
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Parses the recorded Phase 0 payloads (android/contract-fixtures). */
class FixtureParsingTest {
    private fun fixtureBody(path: String): String {
        val text = javaClass.classLoader!!.getResource(path)!!.readText()
        return Json.parseToJsonElement(text).jsonObject["response"]!!.jsonObject["body"].toString()
    }

    @Test fun authStatusFixture() = assertEquals(false, parseSetupRequired(fixtureBody("librarian/auth_status.json")))

    @Test fun badLoginFixtureCarriesTheServerDetail() =
        assertEquals("Invalid username or password.", errorDetail(fixtureBody("librarian/auth_login_bad_credentials.json")))

    @Test fun navidromePingFixtureIsSuccess() = assertNull(Subsonic.pingFailure(fixtureBody("navidrome/ping.json")))

    @Test fun subsonicWrongPasswordIsUnauthorised() {
        val body = """{"subsonic-response":{"status":"failed","version":"1.16.1","error":{"code":40,"message":"Wrong username or password"}}}"""
        assertTrue(Subsonic.pingFailure(body) is ConnectionFailure.Unauthorised)
    }

    @Test fun nonSubsonicAnswerIsAServerProblem() =
        assertTrue(Subsonic.pingFailure("<html>hello</html>") is ConnectionFailure.Server)

    @Test fun tokenIsMd5OfPasswordPlusSalt() =
        // Example from the Subsonic API documentation: password "sesame", salt "c19b2d".
        assertEquals("26719a1196d2a940705a59634eb18eab", Subsonic.token("sesame", "c19b2d"))
}
