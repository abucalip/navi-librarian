"""Regression tests for the legacy server size ratchet."""
import unittest

from scripts.check_server_size import check_source


class ServerSizeGuardTests(unittest.TestCase):
    def test_accepts_source_at_line_and_function_limits(self):
        source = "def small():\n    return 1\n"
        self.assertEqual(
            check_source(
                source,
                server_line_limit=2,
                top_level_function_line_limit=2,
                function_exceptions={},
            ),
            [],
        )

    def test_rejects_server_line_growth(self):
        source = "value = 1\nvalue = 2\nvalue = 3\n"
        errors = check_source(
            source,
            server_line_limit=2,
            top_level_function_line_limit=10,
            function_exceptions={},
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("navidrome_server.py is 3 lines (limit 2)", errors[0])

    def test_rejects_oversized_function_with_name_and_measurement(self):
        source = "def too_large():\n    pass\n    pass\n"
        errors = check_source(
            source,
            server_line_limit=10,
            top_level_function_line_limit=2,
            function_exceptions={},
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("top-level function too_large is 3 lines (limit 2)", errors[0])

    def test_named_temporary_exception_has_its_own_ceiling(self):
        source = "def recommend_new_music():\n" + "    pass\n" * 3
        exception = {
            "recommend_new_music": {
                "max_lines": 4,
                "reason": "temporary test exception",
                "follow_up": "reduce after extraction",
            }
        }
        self.assertEqual(
            check_source(
                source,
                server_line_limit=10,
                top_level_function_line_limit=2,
                function_exceptions=exception,
            ),
            [],
        )
        errors = check_source(
            source + "    pass\n",
            server_line_limit=10,
            top_level_function_line_limit=2,
            function_exceptions=exception,
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("recommend_new_music is 5 lines (limit 4)", errors[0])
        self.assertIn("temporary test exception", errors[0])
        self.assertIn("reduce after extraction", errors[0])

    def test_reports_invalid_python_source(self):
        errors = check_source(
            "def broken(:\n",
            server_line_limit=10,
            top_level_function_line_limit=10,
            function_exceptions={},
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("cannot be parsed", errors[0])


if __name__ == "__main__":
    unittest.main()
