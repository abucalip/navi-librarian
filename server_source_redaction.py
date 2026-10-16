"""Redaction of sensitive assignment lines in bounded source previews."""

import re

_SECRET_NAME = re.compile(
    r"(password|passwd|secret|api[_-]?key|access[_-]?token|client[_-]?secret)",
    re.IGNORECASE,
)
_ASSIGNMENT = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")


def redact_assignment(line):
    """Redact assignments whose variable names indicate secret material."""
    match = _ASSIGNMENT.match(line)
    if match and _SECRET_NAME.search(match.group(1)):
        return match.group(1) + " = '[REDACTED]'"
    return line
