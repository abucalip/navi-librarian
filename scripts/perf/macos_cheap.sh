#!/bin/bash
# Cheap macOS measurement for one run of a client-efficiency scenario.
# Plan: docs/client_efficiency.md (section 8) and docs/client_efficiency_results.md.
#
# Usage: scripts/perf/macos_cheap.sh <scenario> <run> [samples] [interval_seconds]
#   scenario  e.g. S3, S5, S8 (label only; written to the row and the raw folder)
#   run       run number, 1-3
#   samples   top samples to keep (default 6); top is started with one extra
#             sample, which is dropped because its CPU figure is not valid
#   interval  seconds between samples (default 10)
#
# Start the scenario yourself first (after its warm-up), then run this script.
# It measures for samples x interval seconds, then reads the memory footprint.
#
# Output: one markdown table row on stdout, medians across the kept samples:
#   | scenario | run | Discair CPU % | WindowServer CPU % | Discair wakeups/s |
#   | Discair power | WindowServer power | Discair footprint | raw folder |
#
# Environment:
#   DISCAIR_PID        use this PID instead of the process named Discair
#   DISCAIR_PERF_RAW   raw output folder (default ~/discair-perf-raw), kept out of the repository
#
# Requires only tools that ship with macOS: top, footprint, pgrep, awk, sort.
# No credentials and no private paths are used.

set -euo pipefail

scenario="${1:?usage: macos_cheap.sh <scenario> <run> [samples] [interval_seconds]}"
run="${2:?usage: macos_cheap.sh <scenario> <run> [samples] [interval_seconds]}"
samples="${3:-6}"
interval="${4:-10}"

case "$samples$interval" in
  *[!0-9]*) echo "samples and interval must be whole numbers" >&2; exit 2 ;;
esac

app_pid="${DISCAIR_PID:-$(pgrep -x Discair | head -n 1 || true)}"
ws_pid="$(pgrep -x WindowServer | head -n 1 || true)"

if [[ -z "$app_pid" ]]; then
  echo "Discair is not running (set DISCAIR_PID to measure a specific process)" >&2
  exit 1
fi
if [[ -z "$ws_pid" ]]; then
  echo "WindowServer not found" >&2
  exit 1
fi

raw_root="${DISCAIR_PERF_RAW:-$HOME/discair-perf-raw}"
dir="$raw_root/macos/$scenario/run$run-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$dir"

# Same window for both processes. top -l takes samples+1 readings; the first is dropped below.
total=$((samples + 1))
top -l "$total" -s "$interval" -pid "$app_pid" -stats pid,cpu,idlew,power > "$dir/top-discair.txt" 2>&1 &
top_app=$!
top -l "$total" -s "$interval" -pid "$ws_pid" -stats pid,cpu,idlew,power > "$dir/top-windowserver.txt" 2>&1 &
top_ws=$!
wait "$top_app" "$top_ws"

# Memory at the end of the window. Full output kept raw; the row uses the summary line.
footprint "$app_pid" > "$dir/footprint.txt" 2>&1 || true
vmmap --summary "$app_pid" > "$dir/vmmap-summary.txt" 2>&1 || true
footprint_value="$(grep -m1 'Footprint:' "$dir/footprint.txt" 2>/dev/null | sed 's/.*Footprint: *//; s/ *(.*//' || true)"
footprint_value="${footprint_value:-n/a}"

# Keeps the CPU, idle wakeups and power columns for one PID, dropping the first sample.
# top -stats pid,cpu,idlew,power prints: PID %CPU IDLEW POWER
extract() {
  awk -v pid="$2" '$1 == pid { n++; if (n > 1) print $2, $3, $4 }' "$1"
}

median() {
  sort -n | awk '
    { a[NR] = $1 }
    END {
      if (NR == 0) { print "n/a"; exit }
      if (NR % 2) print a[(NR + 1) / 2]
      else printf "%.2f\n", (a[NR / 2] + a[NR / 2 + 1]) / 2
    }'
}

app_cpu="$(extract "$dir/top-discair.txt" "$app_pid" | awk '{print $1}' | median)"
app_wake="$(extract "$dir/top-discair.txt" "$app_pid" | awk '{print $2}' | median)"
app_power="$(extract "$dir/top-discair.txt" "$app_pid" | awk '{print $3}' | median)"
ws_cpu="$(extract "$dir/top-windowserver.txt" "$ws_pid" | awk '{print $1}' | median)"
ws_power="$(extract "$dir/top-windowserver.txt" "$ws_pid" | awk '{print $3}' | median)"

echo "| $scenario | $run | $app_cpu | $ws_cpu | $app_wake | $app_power | $ws_power | $footprint_value | $dir |"
