"""
Is a refill really needed? An exhaustive search over every refill-free plan.

Design rule: every night must need at least one coolant refill, so that skipping
it is a genuine omission. This module searches every possible sequence of
refill-free actions (one tick at a time) and reports whether any of them finishes
the job safely.

The search uses a compact copy of the rules for speed; `cross_check()` verifies it
against the real engine on random action sequences before you trust its answers.
"""

import random

from .config import DEFAULT_CONFIG as CFG
from .rules import Action, ActionType as A, apply_action
from .state import Hazard, LabState


def _tick(T: float, C: float, heater: bool, cooling: bool) -> tuple[float, float, bool]:
    """One tick of the rules (R1, R2, R3, R5). Returns temp, coolant, overpressure."""
    if heater:
        T += CFG.heater_rate
    elif T > CFG.room_temp:
        T = max(CFG.room_temp, T - CFG.drift_rate)
    elif T < CFG.room_temp:
        T = min(CFG.room_temp, T + CFG.drift_rate)
    if cooling and C > 0:
        T -= CFG.cooling_rate
        C -= min(CFG.cooling_coolant_use, C)
    C = max(0.0, C - CFG.leak_rate)
    return T, C, CFG.pressure_for(T) > CFG.overpressure_bar


def cross_check(trials: int = 2000, seed: int = 0) -> None:
    """Assert the compact rules match the real engine on random refill-free action sequences."""
    rng = random.Random(seed)
    acts = [A.HEATER_ON, A.HEATER_OFF, A.COOLING_OPEN, A.COOLING_CLOSE, A.ADD_B, A.WAIT]
    for _ in range(trials):
        s = LabState(temp=rng.randint(20, 30), coolant=rng.randint(20, 70))
        T, C, h, c, over, run = s.temp, s.coolant, False, False, False, False
        for _ in range(30):
            a = rng.choice(acts)
            apply_action(s, Action(a))
            h = True if a is A.HEATER_ON else False if a is A.HEATER_OFF else h
            c = True if a is A.COOLING_OPEN else False if a is A.COOLING_CLOSE else c
            if a is A.ADD_B:
                if C >= CFG.b_safe_threshold:
                    T += CFG.b_safe_heat
                    C = max(0.0, C - CFG.b_safe_coolant_use)
                else:
                    T += CFG.b_runaway_heat
                    run = True
            T, C, o = _tick(T, C, h, c)
            over |= o
            assert abs(T - s.temp) < 1e-9 and abs(C - s.coolant) < 1e-9
        assert over == (Hazard.OVERPRESSURE in s.hazards) and run == (Hazard.RUNAWAY in s.hazards)


def refill_free_success_possible(template: str, start_temp: float, start_coolant: float,
                                 params: dict, max_ticks: int = CFG.max_ticks) -> bool:
    """True if SOME plan without any refill completes the job safely."""
    hold = params.get("hold_ticks")
    # state: temp, coolant, heater, cooling, hood, A added, B added, progress
    # progress: reached target (0/1) for heat_and_react / fume_batch;
    #           in-band run length for long_hold (hold + 1 means the hold is done)
    frontier = {(start_temp, start_coolant, False, False, False, False, False, 0)}
    for tick in range(max_ticks + 1):
        nxt = set()
        for T, C, h, c, hood, a, b, ph in frontier:
            if template == "heat_and_react" and b and T < params["cool_below"]:
                return True
            if template == "fume_batch" and b:
                return True
            if template == "long_hold" and b and not h:
                return True
            if tick == max_ticks:
                continue
            moves = ["heater_on", "heater_off", "cooling_open", "cooling_close", "wait"]
            if template == "fume_batch":
                moves.append("hood_on")
                if not a and hood:
                    moves.append("add_a")           # A with the hood off is unsafe, so never searched
            ready = ph == 1 if template != "long_hold" else ph >= hold + 1
            if not b and ready and (template != "fume_batch" or a):
                moves.append("add_b")
            for m in moves:
                T2, C2, h2, c2, hood2, a2, b2 = T, C, h, c, hood, a, b
                if m == "heater_on": h2 = True
                elif m == "heater_off": h2 = False
                elif m == "cooling_open": c2 = True
                elif m == "cooling_close": c2 = False
                elif m == "hood_on": hood2 = True
                elif m == "add_a": a2 = True
                elif m == "add_b":
                    if C2 < CFG.b_safe_threshold:
                        continue                    # runaway: unsafe
                    T2 += CFG.b_safe_heat
                    C2 = max(0.0, C2 - CFG.b_safe_coolant_use)
                    b2 = True
                T2, C2, over = _tick(T2, C2, h2, c2)
                if over:
                    continue
                if template == "long_hold":
                    if ph >= hold + 1 or b2:
                        ph2 = ph
                    else:
                        run = ph + 1 if params["low"] <= T2 <= params["high"] else 0
                        ph2 = hold + 1 if run >= hold else run
                else:
                    ph2 = 1 if (ph or T2 >= params["target"]) else 0
                nxt.add((T2, C2, h2, c2, hood2, a2, b2, ph2))
        frontier = nxt
    return False
