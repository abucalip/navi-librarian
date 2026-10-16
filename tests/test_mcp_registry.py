"""Regression tests for separating MCP registration from the shared service module."""
import subprocess
import sys
import unittest
from types import SimpleNamespace

from mcp_registry import TOOL_NAMES, create_mcp_server


class FakeMCPServer:
    def __init__(self, name):
        self.name = name
        self.registered = []

    def tool(self):
        def register(function):
            self.registered.append(function)
            return function
        return register


class MCPRegistryTests(unittest.TestCase):
    def test_tool_registry_is_unique_and_registers_all_legacy_tools(self):
        self.assertEqual(len(TOOL_NAMES), 25)
        self.assertEqual(len(TOOL_NAMES), len(set(TOOL_NAMES)))
        self.assertNotIn("restart_server", TOOL_NAMES)
        self.assertNotIn("apply_server_patch", TOOL_NAMES)

        functions = {
            name: (lambda name=name: name)
            for name in TOOL_NAMES
        }
        librarian = SimpleNamespace(**functions)
        server = create_mcp_server(librarian, server_class=FakeMCPServer)

        self.assertEqual(server.name, "navidrome-librarian")
        self.assertEqual(server.registered, list(functions.values()))
        for name, function in functions.items():
            self.assertIs(getattr(librarian, name), function)
            self.assertIn(function, server.registered)

    def test_importing_legacy_service_does_not_load_mcp_sdk(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import navidrome_server as service; "
                "from mcp_registry import TOOL_NAMES; "
                "assert all(callable(getattr(service, name)) for name in TOOL_NAMES); "
                "assert 'mcp.server.mcpserver' not in sys.modules",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
