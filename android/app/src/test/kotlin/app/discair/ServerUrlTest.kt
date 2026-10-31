package app.discair

import app.discair.net.UrlProblem
import app.discair.net.UrlResult
import app.discair.net.normalizeBaseUrl
import org.junit.Assert.assertEquals
import org.junit.Test

class ServerUrlTest {
    private fun ok(input: String) = (normalizeBaseUrl(input) as UrlResult.Ok).url
    private fun bad(input: String) = (normalizeBaseUrl(input) as UrlResult.Bad).problem

    @Test fun keepsHttpsAddress() = assertEquals("https://librarian.tail1234.ts.net", ok("https://librarian.tail1234.ts.net"))
    @Test fun addsHttpsToBareName() = assertEquals("https://librarian.tail1234.ts.net", ok("  Librarian.tail1234.ts.net/ "))
    @Test fun keepsPortAndPath() = assertEquals("https://host.ts.net:8443/navi", ok("https://host.ts.net:8443/navi/"))
    @Test fun dropsQueryAndFragment() = assertEquals("https://host.ts.net", ok("https://host.ts.net/?a=1#x"))
    @Test fun refusesCleartext() = assertEquals(UrlProblem.NotHttps, bad("http://host.ts.net"))
    @Test fun refusesOtherSchemes() = assertEquals(UrlProblem.NotHttps, bad("ftp://host.ts.net"))
    @Test fun refusesEmpty() = assertEquals(UrlProblem.Empty, bad("   "))
    @Test fun refusesCredentialsInAddress() = assertEquals(UrlProblem.Invalid, bad("https://user:pw@host.ts.net"))
    @Test fun refusesSpaces() = assertEquals(UrlProblem.Invalid, bad("https://host name.ts.net"))
}
