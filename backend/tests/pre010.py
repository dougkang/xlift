"""Compare results with pre-010 fixtures: drop later additions when they're at their default
values (null, or `standings: "matchup"`), so anything else still differs."""

# Keys added since (010, and 011's focus), by where they appear; each must be null by default.
ADDED = {"expected_record", "expected", "expected_wins", "win_pct", "focus", "focus_opponent_id"}


def strip_010(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ADDED and v is None:
                continue
            if k == "standings" and v == "matchup":
                continue
            out[k] = strip_010(v)
        return out
    if isinstance(obj, list):
        return [strip_010(v) for v in obj]
    return obj
