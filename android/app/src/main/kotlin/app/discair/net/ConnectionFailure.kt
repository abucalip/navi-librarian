package app.discair.net

import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import javax.net.ssl.SSLException

/** The four failure kinds the app tells apart (contract section 4), plus the login lockout. */
sealed class ConnectionFailure(val message: String) {
    data object NoNetwork : ConnectionFailure("No network connection.")
    data object Unreachable : ConnectionFailure("Server unreachable. Is Tailscale connected?")
    data class Unauthorised(val detail: String? = null) :
        ConnectionFailure(detail ?: "Not authorised. Check the user name and password.")
    data class RateLimited(val detail: String? = null) :
        ConnectionFailure(detail ?: "Too many login attempts. Try again later.")
    data class Server(val code: Int, val detail: String? = null) :
        ConnectionFailure(detail ?: "The server reported an error ($code).")
    data class Certificate(val reason: String) :
        ConnectionFailure("The server certificate was rejected: $reason")
}

/** Thrown by the clients; carries the classified failure. */
class ConnectionException(val failure: ConnectionFailure) : IOException(failure.message)

fun classifyException(error: Throwable, networkAvailable: Boolean): ConnectionFailure = when {
    !networkAvailable -> ConnectionFailure.NoNetwork
    error is ConnectionException -> error.failure
    error is SSLException -> ConnectionFailure.Certificate(error.message ?: "unknown")
    error is UnknownHostException || error is ConnectException || error is SocketTimeoutException ->
        ConnectionFailure.Unreachable
    error is IOException -> ConnectionFailure.Unreachable
    else -> ConnectionFailure.Server(0, error.message)
}

/** Maps an HTTP status from Librarian to a failure; null means the status is a success. */
fun classifyStatus(code: Int, detail: String?): ConnectionFailure? = when (code) {
    in 200..299 -> null
    401, 403 -> ConnectionFailure.Unauthorised(detail)
    429 -> ConnectionFailure.RateLimited(detail)
    else -> ConnectionFailure.Server(code, detail)
}
