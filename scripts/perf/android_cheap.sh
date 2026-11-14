#!/bin/bash
# Cheap Android measurement for one run of a client-efficiency scenario.
# Plan: docs/client_efficiency.md (section 8) and docs/client_efficiency_results.md.
#
# Usage: scripts/perf/android_cheap.sh <scenario> <run> [samples] [interval_seconds]
#   scenario  e.g. S3, S5, S8 (label only; written to the row and the raw folder)
#   run       run number, 1-3
#   samples   top frames to keep (default 6); top is started with one extra
#             frame, which is dropped because its first reading is not valid
#   interval  seconds between top frames (default 10)
#
# Start the scenario yourself (after its one-minute warm-up) and run this script
# during it. The script resets gfxinfo, measures CPU per thread for
# samples x interval seconds, then reads meminfo and gfxinfo at the end.
#
# Requirements: adb on PATH, one device in the "device" state with USB debugging
# on, and the release build installed. Emulator numbers are not accepted.
#
# Output: one markdown table row on stdout:
#   | scenario | run | total PSS KB | native heap KB | graphics KB |
#   | main-thread CPU % | RenderThread CPU % | frames / janky | p50 / p90 / p99 ms | raw folder |
#
# Environment:
#   DISCAIR_PERF_RAW   raw output folder (default ~/discair-perf-raw), kept out of the repository
#
# The top and meminfo layouts vary by Android version. The raw files are always
# kept; check the parsed values against them on the first run.

set -euo pipefail

pkg="app.discair"

scenario="${1:?usage: android_cheap.sh <scenario> <run> [samples] [interval_seconds]}"
run="${2:?usage: android_cheap.sh <scenario> <run> [samples] [interval_seconds]}"
samples="${3:-6}"
interval="${4:-10}"

case "$samples$interval" in
  *[!0-9]*) echo "samples and interval must be whole numbers" >&2; exit 2 ;;
esac

if ! command -v adb >/dev/null 2>&1; then
  echo "adb not found on PATH" >&2
  exit 1
fi

state="$(adb get-state 2>/dev/null || true)"
if [[ "$state" != "device" ]]; then
  echo "no Android device in the 'device' state (check USB debugging and 'adb devices')" >&2
  exit 1
fi

pid="$(adb shell pidof "$pkg" 2>/dev/null | tr -d '\r' | awk '{print $1}' || true)"
if [[ -z "$pid" ]]; then
  echo "$pkg is not running on the device" >&2
  exit 1
fi

raw_root="${DISCAIR_PERF_RAW:-$HOME/discair-perf-raw}"
dir="$raw_root/android/$scenario/run$run-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$dir"

# Frame counts and percentiles start at zero for this window.
adb shell dumpsys gfxinfo "$pkg" reset > /dev/null 2>&1 || true

# Per-thread CPU over the window. top -H lists threads; the first frame is dropped below.
total=$((samples + 1))
adb shell top -H -b -n "$total" -d "$interval" -p "$pid" 2>&1 | tr -d '\r' > "$dir/top-threads.txt"

adb shell dumpsys meminfo "$pkg" 2>&1 | tr -d '\r' > "$dir/meminfo.txt"
adb shell dumpsys gfxinfo "$pkg" 2>&1 | tr -d '\r' > "$dir/gfxinfo.txt"

# First integer after a label in meminfo's App Summary (value in KB).
mem_value() {
  awk -v label="$1" '
    index($0, label) {
      for (i = 1; i <= NF; i++) if ($i ~ /^[0-9]+$/) { print $i; exit }
    }' "$dir/meminfo.txt"
}

pss_total="$(mem_value 'TOTAL PSS:' || true)"
if [[ -z "$pss_total" ]]; then pss_total="$(mem_value 'TOTAL:' || true)"; fi
native_heap="$(mem_value 'Native Heap:' || true)"
graphics="$(mem_value 'Graphics:' || true)"

# Thread CPU per frame. The header line starts with PID; its column containing "CPU"
# gives the value column. Main thread: TID equals the process ID. RenderThread: last field.
thread_samples="$(awk -v pid="$pid" '
  $1 == "PID" {
    frame++
    cpu = 0
    for (i = 1; i <= NF; i++) if ($i ~ /CPU/) cpu = i
    next
  }
  frame > 1 && cpu > 0 && NF > 0 {
    if ($1 == pid) print "main", $cpu
    else if ($NF == "RenderThread") print "render", $cpu
  }' "$dir/top-threads.txt")"

median() {
  sort -n | awk '
    { a[NR] = $1 }
    END {
      if (NR == 0) { print "n/a"; exit }
      if (NR % 2) print a[(NR + 1) / 2]
      else printf "%.2f\n", (a[NR / 2] + a[NR / 2 + 1]) / 2
    }'
}

main_cpu="$(printf '%s\n' "$thread_samples" | awk '$1 == "main" { print $2 }' | median)"
render_cpu="$(printf '%s\n' "$thread_samples" | awk '$1 == "render" { print $2 }' | median)"

# Frame counters from gfxinfo's summary.
total_frames="$(awk -F': *' '/Total frames rendered/ { print $2; exit }' "$dir/gfxinfo.txt")"
janky="$(awk -F': *' '/Janky frames:/ { split($2, a, " "); print a[1]; exit }' "$dir/gfxinfo.txt")"
p50="$(awk -F': *' '/50th percentile/ { gsub(/ms/, "", $2); print $2; exit }' "$dir/gfxinfo.txt")"
p90="$(awk -F': *' '/90th percentile/ { gsub(/ms/, "", $2); print $2; exit }' "$dir/gfxinfo.txt")"
p99="$(awk -F': *' '/99th percentile/ { gsub(/ms/, "", $2); print $2; exit }' "$dir/gfxinfo.txt")"

echo "| $scenario | $run | ${pss_total:-n/a} | ${native_heap:-n/a} | ${graphics:-n/a} | $main_cpu | $render_cpu | ${total_frames:-n/a} / ${janky:-n/a} | ${p50:-n/a} / ${p90:-n/a} / ${p99:-n/a} | $dir |"
