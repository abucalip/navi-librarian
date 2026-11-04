#!/usr/bin/env bash
# Reads changed file paths (repo-relative, one per line) on stdin and prints what the macOS CI job should run:
#   tests=all | none | <regex of test targets for `swift test --filter`>
#   bundle=true | false      (whether to build and verify the app bundle)
# Anything it does not recognise selects the full suite, so a missing rule can only cost time, never skip a test.
# The dependency map mirrors macos/Package.swift; update both together.
set -euo pipefail

all=false; bundle=false
picked=" "     # bash 3.2 (macOS) has no associative arrays
add() { for t in "$@"; do case "$picked" in *" $t "*) ;; *) picked="$picked$t " ;; esac; done; }

while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in
    macos/Sources/DiscairCore/*)       add Core Navidrome Librarian Audio UI ;;
    macos/Sources/DiscairNavidrome/*)  add Navidrome Audio UI ;;
    macos/Sources/DiscairLibrarian/*)  add Librarian UI ;;
    macos/Sources/DiscairAudio/*)      add Audio UI ;;
    macos/Sources/DiscairUI/*)         add UI ;;
    macos/Sources/DiscairApp/*)        bundle=true ;;                 # no tests; the build step compiles it
    macos/Sources/DiscairChecks/*|macos/Sources/AudioSpike/*) ;;     # tools; the build step compiles them
    macos/Tests/DiscairCoreTests/*)       add Core ;;
    macos/Tests/DiscairNavidromeTests/*)  add Navidrome ;;
    macos/Tests/DiscairLibrarianTests/*)  add Librarian ;;
    macos/Tests/DiscairAudioTests/*)      add Audio ;;
    macos/Tests/DiscairUITests/*)         add UI ;;
    macos/DESIGN.md|macos/README.md) ;;                               # documentation
    macos/Packaging/*|macos/scripts/bundle.sh|macos/scripts/appcast.sh|macos/scripts/make-signing-identity.sh) bundle=true ;;
    *) all=true ;;   # Package.swift, Package.resolved, the workflow, contract fixtures, this script, anything new
  esac
done

if $all; then echo "tests=all"; echo "bundle=true"; exit 0; fi
if [ "$picked" = " " ]; then echo "tests=none"; else
  regex=""
  for t in Core Navidrome Librarian Audio UI; do
    case "$picked" in *" $t "*) regex="$regex${regex:+|}Discair${t}Tests" ;; esac
  done
  echo "tests=$regex"
fi
echo "bundle=$bundle"
