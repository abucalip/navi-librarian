import unittest

from server_source_redaction import redact_assignment


class ServerSourceRedactionTests(unittest.TestCase):
    def test_redacts_sensitive_assignment_names_case_insensitively(self):
        for line in (
            "api_key = 'private'",
            "API_KEY = 'private'",
            "access_token = 'private'",
            "client_secret = 'private'",
            "password = 'private'",
            "passwd = 'private'",
        ):
            with self.subTest(line=line):
                self.assertEqual(redact_assignment(line), line.split(" = ")[0] + " = '[REDACTED]'")

    def test_preserves_non_sensitive_assignments_and_non_assignments(self):
        self.assertEqual(redact_assignment("music_dir = '/music'"), "music_dir = '/music'")
        self.assertEqual(redact_assignment("# api_key = 'comment'"), "# api_key = 'comment'")
        self.assertEqual(redact_assignment("print(api_key)"), "print(api_key)")

    def test_preserves_legacy_indented_assignment_redaction_shape(self):
        self.assertEqual(redact_assignment("    api_key = 'private'"), "api_key = '[REDACTED]'")


if __name__ == "__main__":
    unittest.main()
