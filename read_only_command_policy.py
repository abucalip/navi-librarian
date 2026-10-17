"""Strict allowlist for read-only Proxmox diagnostic commands.

Commands are passed to SSH as a remote shell command, so validation must reject
anything except the small set of diagnostic command forms approved below.
"""
import re


_CONTAINER_ID = r"(?:[1-9][0-9]{0,5})"
_DEVICE = r"(?:/dev/sd[a-z]+|/dev/nvme[0-9]+n[0-9]+)"

_ALLOWED_COMMANDS = (
    re.compile(r"pveversion -v"),
    re.compile(r"pvenode status"),
    re.compile(r"pct list"),
    re.compile(r"qm list"),
    re.compile(rf"pct config {_CONTAINER_ID}"),
    re.compile(rf"pct status {_CONTAINER_ID}"),
    re.compile(rf"qm config {_CONTAINER_ID}"),
    re.compile(rf"pct exec {_CONTAINER_ID} -- docker ps"),
    re.compile(rf"smartctl -A {_DEVICE}"),
)


def is_allowed_read_only_command(command: str) -> bool:
    """Return whether command exactly matches an approved diagnostic form."""
    if not isinstance(command, str) or not command or "\n" in command or "\r" in command:
        return False
    return any(pattern.fullmatch(command) is not None for pattern in _ALLOWED_COMMANDS)
