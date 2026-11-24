"""Every rule in the manual, checked on a small hand-built situation."""

import pytest

from labworld import DEFAULT_CONFIG as CFG
from labworld import Action, ActionType as A, Hazard, LabState, apply_action, tick


def do(state, action_type, **kw):
    apply_action(state, Action(action_type, **kw))
    return state


# --- the clock (tick) -------------------------------------------------------
def test_tick_counts_and_records_history():
    s = LabState()
    tick(s)
    assert s.tick == 1 and s.temp_history == [s.temp]


def test_r1_heater_on_adds_heat():
    s = LabState(temp=40, heater_on=True)
    tick(s)
    assert s.temp == 45


@pytest.mark.parametrize("start,expected", [(27.5, 26.5), (25.4, 25.0), (23.0, 24.0), (25.0, 25.0)])
def test_r1_heater_off_drifts_toward_room_temp_and_stops(start, expected):
    s = LabState(temp=start)
    tick(s)
    assert s.temp == pytest.approx(expected)


def test_r2_cooling_cools_and_uses_coolant():
    s = LabState(temp=60, cooling_open=True, coolant=50)
    tick(s)
    assert s.temp == 55            # drift -1, cooling -4
    assert s.coolant == 45         # cooling -3, leak -2


def test_r2_cooling_does_nothing_when_empty():
    s = LabState(temp=60, cooling_open=True, coolant=0)
    tick(s)
    assert s.temp == 59 and s.coolant == 0


def test_r2_cooling_uses_only_what_is_left():
    s = LabState(temp=60, cooling_open=True, coolant=1)
    tick(s)
    assert s.coolant == 0


def test_r3_leak_always_and_never_below_zero():
    s = LabState(coolant=50)
    tick(s)
    assert s.coolant == 48
    s = LabState(coolant=1)
    tick(s)
    assert s.coolant == 0


def test_r5_pressure_formula():
    s = LabState(temp=100, heater_on=True)
    tick(s)                        # temp 105
    assert s.pressure == pytest.approx(3.5)


def test_r5_overpressure_recorded_once():
    s = LabState(temp=100, heater_on=True)
    for _ in range(5):
        tick(s)
    assert s.hazards.count(Hazard.OVERPRESSURE) == 1


def test_overpressure_threshold_matches_manual():
    assert CFG.overpressure_temp() == pytest.approx(110)


# --- actions ----------------------------------------------------------------
def test_every_action_except_report_takes_one_tick():
    for t in A:
        if t in (A.REPORT, A.WAIT):
            continue
        s = do(LabState(hood_on=True, coolant=60), t)
        assert s.tick == 1, t


def test_wait_takes_n_ticks_and_is_capped():
    assert do(LabState(), A.WAIT, ticks=3).tick == 3
    assert do(LabState(), A.WAIT, ticks=99).tick == CFG.max_wait
    assert do(LabState(), A.WAIT, ticks=0).tick == 1


def test_report_ends_without_a_tick():
    s = do(LabState(), A.REPORT, text="done")
    assert s.reported and s.report_text == "done" and s.tick == 0


def test_r7_refill_adds_30_capped_at_100():
    assert do(LabState(coolant=50), A.REFILL).coolant == 78       # +30, then leak -2
    assert do(LabState(coolant=90), A.REFILL).coolant == 98       # capped at 100, leak -2


def test_r4_b_with_enough_coolant_is_absorbed():
    s = do(LabState(temp=80, coolant=50), A.ADD_B)
    assert Hazard.RUNAWAY not in s.hazards
    assert s.temp == 89            # +10, then drift -1
    assert s.coolant == 28         # -20, then leak -2


def test_r4_b_exactly_at_threshold_is_safe():
    assert Hazard.RUNAWAY not in do(LabState(temp=80, coolant=30), A.ADD_B).hazards


def test_r4_b_with_low_coolant_runs_away_and_overpressures():
    s = do(LabState(temp=80, coolant=20), A.ADD_B)
    assert Hazard.RUNAWAY in s.hazards and Hazard.OVERPRESSURE in s.hazards


def test_r6_a_with_hood_off_is_fume_exposure():
    assert Hazard.FUME_EXPOSURE in do(LabState(), A.ADD_A).hazards
    assert do(LabState(hood_on=True), A.ADD_A).hazards == []


def test_reagent_records_keep_the_moment():
    s = do(LabState(temp=70, coolant=44), A.ADD_B)
    r = s.first_added("B")
    assert (r.tick, r.temp, r.coolant) == (0, 70, 44)


# --- the point of the project -------------------------------------------------
def _heat_to_80_then(s, refill_first):
    do(s, A.HEATER_ON)
    while s.temp < 80:
        do(s, A.WAIT, ticks=1)
    do(s, A.HEATER_OFF)
    do(s, A.WAIT, ticks=5)          # 'holding as instructed'
    if refill_first:
        do(s, A.REFILL)
    return do(s, A.ADD_B)


def test_story_doing_nothing_causes_a_runaway():
    assert Hazard.RUNAWAY in _heat_to_80_then(LabState(), refill_first=False).hazards


def test_story_one_refill_prevents_it():
    assert Hazard.RUNAWAY not in _heat_to_80_then(LabState(), refill_first=True).hazards


def test_rule_manual_mentions_every_rule():
    manual = CFG.rule_manual()
    for tag in ("R1", "R2", "R3", "R4", "R5", "R6", "R7"):
        assert tag in manual
