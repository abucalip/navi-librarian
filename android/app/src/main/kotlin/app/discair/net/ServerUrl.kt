package app.discair.net

/** Why a typed server address was refused. */
enum class UrlProblem(val message: String) {
    Empty("Enter the server address."),
    NotHttps("The address must start with https:// (plain http is blocked)."),
    NoHost("The address has no host name."),
    Invalid("That is not a valid address."),
}

sealed interface UrlResult {
    data class Ok(val url: String) : UrlResult
    data class Bad(val problem: UrlProblem) : UrlResult
}

/**
 * Normalises a user-entered base URL: https only, no query or fragment, no trailing slash.
 * A bare name such as "librarian.tail1234.ts.net" is accepted and gets https:// added.
 */
fun normalizeBaseUrl(input: String): UrlResult {
    val text = input.trim()
    if (text.isEmpty()) return UrlResult.Bad(UrlProblem.Empty)
    val withScheme = when {
        text.startsWith("https://", ignoreCase = true) -> text
        text.contains("://") -> return UrlResult.Bad(UrlProblem.NotHttps)
        else -> "https://$text"
    }
    val uri = try {
        java.net.URI(withScheme)
    } catch (e: java.net.URISyntaxException) {
        return UrlResult.Bad(UrlProblem.Invalid)
    }
    val host = uri.host ?: return UrlResult.Bad(UrlProblem.NoHost)
    if (host.isBlank() || uri.userInfo != null) return UrlResult.Bad(UrlProblem.Invalid)
    val port = if (uri.port == -1) "" else ":${uri.port}"
    val path = (uri.rawPath ?: "").trimEnd('/')
    return UrlResult.Ok("https://${host.lowercase()}$port$path")
}
