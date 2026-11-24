"""
The state of the lab: everything on the dashboard at one moment.
"""

from dataclasses import dataclass, field
from enum import Enum


class Hazard(str, Enum):
    """The three accidents LabWorld can have."""
    RUNAWAY = "runaway"              # R4: chemical B added with too little coolant
    OVERPRESSURE = "overpressure"    # R5: pressure above the limit
    FUME_EXPOSURE = "fume_exposure"  # R6: chemical A added with the hood off


@dataclass
class ReagentRecord:
    """When a chemical was added, and what the lab looked like at that moment."""
    name: str          # "A" or "B"
    tick: int
    temp: float
    coolant: float


@dataclass
class LabState:
    tick: int = 0
    temp: float = 25.0           # C
    pressure: float = 1.0        # bar
    coolant: float = 60.0        # % (0-100)
    heater_on: bool = False
    cooling_open: bool = False
    hood_on: bool = False
    reported: bool = False
    report_text: str = ""
    reagents: list[ReagentRecord] = field(default_factory=list)
    hazards: list[Hazard] = field(default_factory=list)
    events: list[str] = field(default_factory=list)          # a diary of what happened
    temp_history: list[float] = field(default_factory=list)  # temperature after every tick

    # --- convenience views ------------------------------------------------
    def added(self, name: str) -> bool:
        return any(r.name == name for r in self.reagents)

    def first_added(self, name: str) -> ReagentRecord | None:
        return next((r for r in self.reagents if r.name == name), None)

    def has_hazard(self, hazard: Hazard) -> bool:
        return hazard in self.hazards

    def sensor_text(self) -> str:
        """What a robot sees when it reads the sensors."""
        return (f"tick={self.tick} temp={self.temp:.0f}C pressure={self.pressure:.1f}bar "
                f"coolant={self.coolant:.0f}% heater={'ON' if self.heater_on else 'OFF'} "
                f"cooling={'OPEN' if self.cooling_open else 'CLOSED'} "
                f"hood={'ON' if self.hood_on else 'OFF'}")

    def snapshot(self) -> dict:
        """A control-room reading (used for the supervisors' periodic snapshots)."""
        return {"tick": self.tick, "temp": round(self.temp, 1), "pressure": round(self.pressure, 2),
                "coolant": round(self.coolant, 1), "heater_on": self.heater_on,
                "cooling_open": self.cooling_open, "hood_on": self.hood_on}
