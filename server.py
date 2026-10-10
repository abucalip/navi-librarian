import subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("prox-ro")

@mcp.tool()
def run(command: str) -> str:
    """Run one allowlisted read-only command on the Proxmox host (e.g. 'pveversion -v',
    'pct config 121', 'pct exec 121 -- docker ps', 'smartctl -A /dev/sda')."""
    r = subprocess.run(
        ["ssh", "-i", "/Users/hamdibaala/.ssh/claude_ro", "-o", "IdentitiesOnly=yes",
         "-o", "BatchMode=yes", "claude-ro@prox", command],
        capture_output=True, text=True, timeout=60)
    return (r.stdout + r.stderr)[:20000]

mcp.run()
