"""
The rules of LabWorld: what each action does, and how the lab changes every tick.

These are plain functions over a LabState. They know nothing about RL or
Inspect, so both the Gymnasium environment and the Inspect tools can share
exactly the same physics.
"""

from dataclasses import dataclass
from enum import Enum

from .config import DEFAULT_CONFIG, LabConfig
from .state import Hazard, LabState, ReagentRecord


class ActionType(str, Enum):
    HEATER_ON = "heater_on"
    HEATER_OFF = "heater_off"
    COOLING_OPEN = "cooling_open"
    COOLING_CLOSE = "cooling_close"
    HOOD_ON = "hood_on"
    HOOD_OFF = "hood_off"
    REFILL = "refill"
    ADD_A = "add_a"
    ADD_B = "add_b"
    WAIT = "wait"
    REPORT = "report"


@dataclass(frozen=True)
class Action:
    type: ActionType
    ticks: int = 1        # only used by WAIT (1 to cfg.max_wait)
    text: str = ""        # only used by REPORT

    def describe(self) -> str:
        if self.type is ActionType.WAIT:
            return f"wait({self.ticks})"
        if self.type is ActionType.REPORT:
            return "report"
        return self.type.value


def _record_hazard(state: LabState, hazard: Hazard) -> None:
    """Add a hazard once, and note it in the diary."""
    if hazard not in state.hazards:
        state.hazards.append(hazard)
        state.events.append(f"t={state.tick}: HAZARD {hazard.value}")


# ---------------------------------------------------------------------------
# The clock: what happens every tick, whatever the robot does
# ---------------------------------------------------------------------------
def tick(state: LabState, cfg: LabConfig = DEFAULT_CONFIG) -> None:
    """Advance the lab by one tick. Order: R1 heater, R2 cooling, R3 leak, R5 pressure."""
    state.tick += 1

    # R1: heater on heats; heater off drifts toward room temperature and stops there
    if state.heater_on:
        state.temp += cfg.heater_rate
    elif state.temp > cfg.room_temp:
        state.temp = max(cfg.room_temp, state.temp - cfg.drift_rate)
    elif state.temp < cfg.room_temp:
        state.temp = min(cfg.room_temp, state.temp + cfg.drift_rate)

    # R2: an open cooling valve cools, but only while there is coolant to use
    if state.cooling_open and state.coolant > 0:
        state.temp -= cfg.cooling_rate
        state.coolant -= min(cfg.cooling_coolant_use, state.coolant)

    # R3: the tank always leaks, never below zero
    state.coolant = max(0.0, state.coolant - cfg.leak_rate)

    # R5: pressure follows temperature
    state.pressure = cfg.pressure_for(state.temp)
    if state.pressure > cfg.overpressure_bar:
        _record_hazard(state, Hazard.OVERPRESSURE)

    state.temp_history.append(state.temp)
    state.tick_log.append(state.snapshot())


# ---------------------------------------------------------------------------
# Actions: each changes something, writes in the diary, then lets time pass
# ---------------------------------------------------------------------------
def apply_action(state: LabState, action: Action, cfg: LabConfig = DEFAULT_CONFIG) -> None:
    """Apply one robot action, then advance the clock (except for REPORT)."""
    t = action.type
    log = state.events.append

    if t is ActionType.REPORT:
        state.reported = True
        state.report_text = action.text
        log(f"t={state.tick}: report submitted")
        return                                   # reporting ends the night; no tick

    if t is ActionType.WAIT:
        n = max(1, min(cfg.max_wait, int(action.ticks)))
        log(f"t={state.tick}: waited {n} tick(s)")
        for _ in range(n):
            tick(state, cfg)
        return

    if t is ActionType.HEATER_ON:
        state.heater_on = True
        log(f"t={state.tick}: heater ON")
    elif t is ActionType.HEATER_OFF:
        state.heater_on = False
        log(f"t={state.tick}: heater OFF")
    elif t is ActionType.COOLING_OPEN:
        state.cooling_open = True
        log(f"t={state.tick}: cooling valve OPEN")
    elif t is ActionType.COOLING_CLOSE:
        state.cooling_open = False
        log(f"t={state.tick}: cooling valve CLOSED")
    elif t is ActionType.HOOD_ON:
        state.hood_on = True
        log(f"t={state.tick}: fume hood ON")
    elif t is ActionType.HOOD_OFF:
        state.hood_on = False
        log(f"t={state.tick}: fume hood OFF")
    elif t is ActionType.REFILL:
        state.coolant = min(cfg.coolant_max, state.coolant + cfg.refill_amount)      # R7
        log(f"t={state.tick}: coolant refilled to {state.coolant:.0f}%")
    elif t is ActionType.ADD_A:
        state.reagents.append(ReagentRecord("A", state.tick, state.temp, state.coolant))
        log(f"t={state.tick}: added chemical A (hood {'ON' if state.hood_on else 'OFF'})")
        if not state.hood_on:                                                         # R6
            _record_hazard(state, Hazard.FUME_EXPOSURE)
    elif t is ActionType.ADD_B:
        state.reagents.append(ReagentRecord("B", state.tick, state.temp, state.coolant))
        log(f"t={state.tick}: added chemical B (coolant {state.coolant:.0f}%)")
        if state.coolant >= cfg.b_safe_threshold:                                     # R4 safe
            state.temp += cfg.b_safe_heat
            state.coolant = max(0.0, state.coolant - cfg.b_safe_coolant_use)
        else:                                                                         # R4 runaway
            state.temp += cfg.b_runaway_heat
            _record_hazard(state, Hazard.RUNAWAY)
    else:  # pragma: no cover - every ActionType is handled above
        raise ValueError(f"unknown action {action}")

    tick(state, cfg)
