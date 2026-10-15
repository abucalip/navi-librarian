"""Handler-level regression tests for the Proxmox MCP command guard."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import server


class ProxmoxMCPHandlerTests(unittest.TestCase):
    @patch("server.subprocess.run")
    def test_rejected_command_never_invokes_ssh(self, ssh_run):
        result = server.run("pveversion -v; id")
        self.assertEqual(
            result,
            "Rejected: command is not on the read-only allowlist.",
        )
        ssh_run.assert_not_called()

    @patch(
        "server.subprocess.run",
        return_value=SimpleNamespace(stdout="version output", stderr=""),
    )
    def test_allowed_command_uses_existing_ssh_execution_and_returns_output(self, ssh_run):
        result = server.run("pveversion -v")
        self.assertEqual(result, "version output")
        args, kwargs = ssh_run.call_args
        self.assertEqual(args[0][-1], "pveversion -v")
        self.assertEqual(kwargs, {"capture_output": True, "text": True, "timeout": 60})

    @patch(
        "server.subprocess.run",
        return_value=SimpleNamespace(stdout="x" * 20000, stderr="y" * 1000),
    )
    def test_output_remains_truncated_to_twenty_thousand_characters(self, ssh_run):
        result = server.run("pveversion -v")
        self.assertEqual(len(result), 20000)


if __name__ == "__main__":
    unittest.main()
