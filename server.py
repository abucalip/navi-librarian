import subprocess
from mcp.server.mcpserver import MCPServer

from read_only_command_policy import is_allowed_read_only_command

mcp = MCPServer("prox-ro")


@mcp.tool()
def run(command: str) -> str:
    """Run an explicitly allowlisted read-only diagnostic command on Proxmox.

    Accepted forms are intentionally narrow; arbitrary shell commands are refused.
    """
    if not is_allowed_read_only_command(command):
        return "Rejected: command is not on the read-only allowlist."

    r = subprocess.run(
        ["ssh", "-i", "/Users/hamdibaala/.ssh/claude_ro", "-o", "IdentitiesOnly=yes",
         "-o", "BatchMode=yes", "claude-ro@prox", command],
        capture_output=True, text=True, timeout=60)
    return (r.stdout + r.stderr)[:20000]

if __name__ == "__main__":
    mcp.run()
