"""Regression tests for the supported MCP-free web application architecture."""
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MCPRetirementTests(unittest.TestCase):
    def test_web_app_import_does_not_initialize_mcp_runtime(self):
        script = (
            "import sys; from app.main import app; "
            "assert app.title == 'Discair'; "
            "assert not any(name == 'mcp' or name.startswith('mcp.') "
            "for name in sys.modules); "
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mcp_registry_dependency_and_standalone_transport_are_absent(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        service = (ROOT / "navidrome_server.py").read_text(encoding="utf-8")
        self.assertFalse((ROOT / "mcp_registry.py").exists())
        self.assertNotIn("mcp==", requirements)
        self.assertNotIn("mcp_registry.py", dockerfile)
        self.assertNotIn("create_mcp_server", service)
        self.assertNotIn('transport="streamable-http"', service)
        self.assertNotIn("port=8000", service)

    def test_web_entry_point_keeps_scheduler_startup(self):
        app_source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
        service_source = (ROOT / "navidrome_server.py").read_text(encoding="utf-8")
        self.assertIn('@app.on_event("startup")', app_source)
        self.assertIn("threading.Timer(\n        10,", app_source)
        self.assertIn("def _start_discovery_background()", app_source)
        self.assertIn("librarian._start_discovery_scheduler()", app_source)
        self.assertIn("lens_service.start_daily_refresh(librarian)", app_source)
        self.assertIn("def _start_discovery_scheduler()", service_source)


if __name__ == "__main__":
    unittest.main()
