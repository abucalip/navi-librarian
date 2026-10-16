"""Direct-import regression tests for session-cookie policy."""
import unittest
from http.cookies import SimpleCookie
from types import SimpleNamespace

from starlette.responses import Response

from app.security.auth_cookie import set_auth_cookie


class AuthCookiePolicyTests(unittest.TestCase):
    def make_request(self, scheme="http", forwarded_proto=""):
        return SimpleNamespace(
            url=SimpleNamespace(scheme=scheme),
            headers={"x-forwarded-proto": forwarded_proto},
        )

    def make_response(self, request):
        response = Response()
        set_auth_cookie(
            response,
            request,
            "owner",
            make_session_token=lambda username: f"token-for-{username}",
            cookie_name="navil_session",
            max_age=43200,
        )
        cookie = SimpleCookie()
        cookie.load(response.headers["set-cookie"])
        return response, cookie["navil_session"]

    def test_cookie_preserves_name_value_lifetime_and_security_attributes(self):
        _, cookie = self.make_response(self.make_request())
        self.assertEqual(cookie.value, "token-for-owner")
        self.assertEqual(cookie["max-age"], "43200")
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "strict")
        self.assertEqual(cookie["path"], "/")
        self.assertFalse(cookie["secure"])

    def test_https_request_marks_cookie_secure(self):
        _, cookie = self.make_response(self.make_request(scheme="https"))
        self.assertTrue(cookie["secure"])

    def test_first_forwarded_protocol_controls_secure_attribute(self):
        _, secure_cookie = self.make_response(
            self.make_request(forwarded_proto=" HTTPS , http")
        )
        _, insecure_cookie = self.make_response(
            self.make_request(forwarded_proto="http, https")
        )
        self.assertTrue(secure_cookie["secure"])
        self.assertFalse(insecure_cookie["secure"])


if __name__ == "__main__":
    unittest.main()
