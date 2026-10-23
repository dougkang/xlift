from types import MappingProxyType

import pytest

from ffmodel.core.data.models import LeagueSettings
from ffmodel.core.scenario import (
    Add,
    Drop,
    MoveError,
    RosterSpot,
    Scenario,
    Swap,
    apply,
    apply_all,
)

ME, OTHER, THIRD = 1, 2, 3
FA_1, FA_2 = 90, 91
KNOWN = {10, 11, 12, 13, 20, 21, 22, 30, FA_1, FA_2}


def base(my_active=(10, 11), my_reserve=(13,), other=(20, 21, 22), other_reserve=()):
    settings = LeagueSettings(1, "lg", "League", "2026-27", "9cat_h2h", 3)
    rosters = {
        ME: tuple(RosterSpot(p, "active") for p in my_active)
        + tuple(RosterSpot(p, "reserve") for p in my_reserve),
        OTHER: tuple(RosterSpot(p, "active") for p in other)
        + tuple(RosterSpot(p, "reserve") for p in other_reserve),
        THIRD: (RosterSpot(30, "active"),),
    }
    reserve = frozenset(my_reserve) | frozenset(other_reserve)
    return Scenario(settings, MappingProxyType(rosters), reserve)


def code(fn):
    with pytest.raises(MoveError) as exc:
        fn()
    return exc.value.code


def test_drop():
    s = apply(base(), ME, Drop(10), known=KNOWN)
    assert 10 not in s.owner and s.open_active_slots(ME) == 2
    assert code(lambda: apply(base(), ME, Drop(20), known=KNOWN)) == "NOT_ON_TEAM"


def test_dropping_reserve_frees_no_active_slot():
    s = apply(base(), ME, Drop(13), known=KNOWN)
    assert s.open_active_slots(ME) == 1 and 13 not in s.owner


def test_add():
    s = apply(base(), ME, Add(FA_1), known=KNOWN)
    assert s.owner[FA_1] == ME and RosterSpot(FA_1, "active") in s.rosters[ME]
    full = base(my_active=(10, 11, 12))
    assert code(lambda: apply(full, ME, Add(FA_1), known=KNOWN)) == "NO_ACTIVE_SLOT"
    assert code(lambda: apply(base(), ME, Add(20), known=KNOWN)) == "NOT_FREE_AGENT"


def test_trade_needs_no_open_slot():
    full = base(my_active=(10, 11, 12))
    s = apply(full, ME, Swap(acquire_id=20, give_id=10), known=KNOWN)
    assert s.owner[20] == ME and s.owner[10] == OTHER
    assert RosterSpot(10, "active") in s.rosters[OTHER]
    s.check_invariants()


def test_trade_reserve_player_becomes_active_on_other_team():
    s = apply(base(), ME, Swap(acquire_id=20, give_id=13), known=KNOWN)
    assert RosterSpot(13, "active") in s.rosters[OTHER]
    assert RosterSpot(20, "active") in s.rosters[ME]


def test_swap_with_free_agent():
    s = apply(base(), ME, Swap(acquire_id=20, give_id=FA_1), known=KNOWN)
    assert s.owner[20] == ME and s.owner[FA_1] == OTHER
    full = base(my_active=(10, 11, 12))
    assert code(lambda: apply(full, ME, Swap(20, FA_1), known=KNOWN)) == "NO_ACTIVE_SLOT"


def test_swap_errors():
    assert code(lambda: apply(base(), ME, Swap(10, 11), known=KNOWN)) == "SAME_TEAM"
    assert code(lambda: apply(base(), ME, Swap(FA_1, 10), known=KNOWN)) == "NOT_ON_TEAM"
    assert code(lambda: apply(base(), ME, Swap(20, 30), known=KNOWN)) == "NOT_ON_TEAM"
    assert code(lambda: apply(base(), ME, Add(999), known=KNOWN)) == "UNKNOWN_PLAYER"


def test_apply_all_reports_index_and_never_mutates_base():
    s0 = base()
    with pytest.raises(MoveError) as exc:
        apply_all(s0, ME, [Add(FA_1), Add(FA_2)], known=KNOWN)
    assert (exc.value.move_index, exc.value.code) == (1, "NO_ACTIVE_SLOT")
    assert FA_1 not in s0.owner


def test_moves_never_create_reserve_slots():
    s = apply_all(base(), ME, [Drop(10), Add(FA_1), Swap(20, 13), Swap(21, 11)], known=KNOWN)
    s.check_invariants()
    reserve = {p.player_id for spots in s.rosters.values() for p in spots if p.slot == "reserve"}
    assert reserve <= {13}


def test_moves_stay_with_the_team_they_were_made_for():
    moves = [Drop(10, team_id=ME), Add(FA_1, team_id=ME)]
    # Re-applied while another team is selected, the moves still act on ME.
    s = apply_all(base(), OTHER, moves, known=KNOWN)
    assert 10 not in s.owner and s.owner[FA_1] == ME
    assert code(lambda: apply(base(), OTHER, Drop(10, team_id=99), known=KNOWN)) == "UNKNOWN_TEAM"
