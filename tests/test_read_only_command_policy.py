"""Tests for the command allowlist used by the separate Proxmox MCP entry point."""
import unittest

from read_only_command_policy import is_allowed_read_only_command


class ReadOnlyCommandPolicyTests(unittest.TestCase):
    def test_approved_diagnostic_commands_are_accepted(self):
        for command in (
            "pveversion -v",
            "pvenode status",
            "pct list",
            "qm list",
            "pct config 121",
            "pct status 121",
            "qm config 101",
            "pct exec 121 -- docker ps",
            "smartctl -A /dev/sda",
            "smartctl -A /dev/nvme0n1",
        ):
            with self.subTest(command=command):
                self.assertTrue(is_allowed_read_only_command(command))

    def test_arbitrary_commands_and_shell_composition_are_rejected(self):
        for command in (
            "rm -rf /",
            "cat /etc/shadow",
            "pct exec 121 -- sh -c id",
            "pveversion -v; rm -rf /",
            "pveversion -v && id",
            "pveversion -v $(id)",
            "pct config 121; cat /etc/passwd",
            "smartctl -A /dev/sda; touch /tmp/pwned",
            "pct exec 121 -- docker ps\n id",
            "",
        ):
            with self.subTest(command=command):
                self.assertFalse(is_allowed_read_only_command(command))

    def test_container_ids_and_device_paths_are_validated(self):
        for command in (
            "pct config 0",
            "pct config 121;id",
            "pct exec 121 -- docker ps -a",
            "smartctl -A /dev/../../etc/shadow",
            "smartctl -A /dev/nvme0n1;id",
        ):
            with self.subTest(command=command):
                self.assertFalse(is_allowed_read_only_command(command))

    def test_non_string_input_is_rejected(self):
        self.assertFalse(is_allowed_read_only_command(None))
        self.assertFalse(is_allowed_read_only_command(121))


if __name__ == "__main__":
    unittest.main()
