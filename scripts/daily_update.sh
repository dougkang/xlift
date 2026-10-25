#!/usr/bin/env bash
# Daily data refresh: capture the league from Yahoo, then load NBA stats, rosters and matchups.
#
#   scripts/daily_update.sh                 # everything
#   scripts/daily_update.sh --skip-capture  # load the CSVs already on disk
#   scripts/daily_update.sh --skip-nba      # skip the NBA stats refresh
#   scripts/daily_update.sh --dry-run       # print the commands without running them
#
# The capture drives Chrome: open the league's Yahoo page first, and enable
# View → Developer → Allow JavaScript from Apple Events (once per machine).
#
# Environment overrides:
#   CCSV_DIR     the capture project (default ~/dev/ccsv-rumble-page)
#   LEAGUE_KEY   the league to load into (default ccsv-2026)
#   FFMODEL_DB_URL  the database, as for any ffm command
#
# A running `ffm serve` picks up the new data on its next request; no restart needed.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CCSV_DIR="${CCSV_DIR:-$HOME/dev/ccsv-rumble-page}"
LEAGUE_KEY="${LEAGUE_KEY:-ccsv-2026}"

capture=1 nba=1 dry=0
for arg in "$@"; do
  case "$arg" in
    --skip-capture) capture=0 ;;
    --skip-nba) nba=0 ;;
    --dry-run) dry=1 ;;
    -h | --help)
      sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "unknown option: $arg (try --help)" >&2
      exit 2
      ;;
  esac
done

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
run() {
  printf '  $ %s\n' "$*"
  [[ $dry == 1 ]] || "$@"
}

ROSTERS="$CCSV_DIR/data/rosters.csv"
MATCHUPS="$CCSV_DIR/data/matchups.csv"

if [[ $capture == 1 ]]; then
  step "Capture rosters and matchups from Yahoo (Chrome)"
  (cd "$CCSV_DIR" && run uv run python tools/chrome_capture.py dailies)
fi

cd "$REPO/backend"

if [[ $nba == 1 ]]; then
  step "NBA stats (incremental)"
  run uv run ffm load nba
fi

for f in "$ROSTERS" "$MATCHUPS"; do
  if [[ $dry == 0 && ! -f $f ]]; then
    echo "missing $f — run the capture first" >&2
    exit 1
  fi
done

# The as-of date defaults to each file's modified date (before noon: the day before).
step "Rosters → $LEAGUE_KEY"
run uv run ffm load roster "$ROSTERS" --league-key "$LEAGUE_KEY"

step "Matchups → $LEAGUE_KEY"
run uv run ffm load matchups "$MATCHUPS" --league-key "$LEAGUE_KEY"

step "Done"
run uv run ffm runs
