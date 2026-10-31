package app.discair

import app.discair.net.ConnectionException
import app.discair.net.ConnectionFailure
import app.discair.net.classifyException
import app.discair.net.classifyStatus
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import javax.net.ssl.SSLHandshakeException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ConnectionFailureTest {
    @Test fun noNetworkWinsOverEverything() =
        assertEquals(ConnectionFailure.NoNetwork, classifyException(UnknownHostException("x"), networkAvailable = false))

    @Test fun hostErrorsMeanUnreachable() {
        for (e in listOf(UnknownHostException("x"), ConnectException("x"), SocketTimeoutException("x"))) {
            assertEquals(ConnectionFailure.Unreachable, classifyException(e, true))
        }
    }

    @Test fun certificateProblemIsNotCalledUnreachable() =
        assertTrue(classifyException(SSLHandshakeException("bad cert"), true) is ConnectionFailure.Certificate)

    @Test fun classifiedFailureSurvivesTheException() {
        val failure = ConnectionFailure.RateLimited("later")
        assertEquals(failure, classifyException(ConnectionException(failure), true))
    }

    @Test fun statusMapping() {
        assertNull(classifyStatus(200, null))
        assertTrue(classifyStatus(401, "Invalid username or password.") is ConnectionFailure.Unauthorised)
        assertTrue(classifyStatus(429, null) is ConnectionFailure.RateLimited)
        assertEquals(ConnectionFailure.Server(502, "x"), classifyStatus(502, "x"))
    }
}
