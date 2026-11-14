#!/bin/bash
# Cold-launch timing for S1 (macOS). Quits Discair, starts it with `open`, and
# polls System Events until the app has a window; prints the elapsed seconds.
# Needs Accessibility permission for the terminal. Home content is not detected:
# the figure is time to first window, a lower bound on "Home shows content".
#
# Usage: scripts/perf/macos_launch.sh [launches] [pause_seconds]   (default 5, 30)
set -euo pipefail
n="${1:-5}"; pause="${2:-30}"
for i in $(seq 1 "$n"); do
  osascript -e 'tell application "Discair" to quit' >/dev/null 2>&1 || true
  while pgrep -x Discair >/dev/null; do sleep 0.2; done
  sleep "$pause"
  start=$(python3 -c 'import time;print(time.time())')
  open -a Discair
  while :; do
    w=$(osascript -e 'tell application "System Events" to if exists process "Discair" then return count of windows of process "Discair"' 2>/dev/null || echo 0)
    [[ "${w:-0}" =~ ^[0-9]+$ && "${w:-0}" -ge 1 ]] && break
    sleep 0.05
  done
  end=$(python3 -c 'import time;print(time.time())')
  python3 -c "print('launch $i: %.2f s' % ($end-$start))"
done
