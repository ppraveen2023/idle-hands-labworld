"""
One night shift: a task, a lab state, and the bookkeeping around them.

LabEpisode is the shared engine. The Gymnasium environment (for RL) and the
Inspect tools (for LLM robots) both drive a LabEpisode, so a night means
exactly the same thing to both.
"""

from dataclasses import asdict, dataclass

import numpy as np

from .config import DEFAULT_CONFIG, LabConfig
from .rules import Action, ActionType, apply_action
from .state import Hazard, LabState
from .tasks import TEMPLATES, TaskSpec


@dataclass
class StepResult:
    new_hazards: list[Hazard]
    new_events: list[str]
    terminated: bool      # the robot submitted its report
    truncated: bool       # the night hit the time limit


@dataclass
class Outcome:
    """The referee's verdict on a night, from the true state."""
    completed: bool
    safe: bool
    hazards: list[str]
    ticks: int

    @property
    def success(self) -> bool:
        return self.completed and self.safe


class LabEpisode:
    def __init__(self, spec: TaskSpec, cfg: LabConfig = DEFAULT_CONFIG):
        self.spec = spec
        self.cfg = cfg
        self.state = LabState(temp=spec.start_temp, coolant=spec.start_coolant,
                              pressure=cfg.pressure_for(spec.start_temp))
        self.actions: list[Action] = []

    @classmethod
    def sample(cls, template: str | None = None, seed: int | None = None,
               cfg: LabConfig = DEFAULT_CONFIG) -> "LabEpisode":
        """Start a new night: pick a template (random if None) and sample its conditions."""
        rng = np.random.default_rng(seed)
        name = template or str(rng.choice(sorted(TEMPLATES)))
        return cls(TEMPLATES[name].sample(rng), cfg)

    # --- saving and loading (Inspect keeps the night in its store as plain data)
    def to_dict(self) -> dict:
        return {"spec": asdict(self.spec), "cfg": asdict(self.cfg),
                "state": self.state.to_dict(),
                "actions": [{"type": a.type.value, "ticks": a.ticks, "text": a.text}
                            for a in self.actions]}

    @classmethod
    def from_dict(cls, d: dict) -> "LabEpisode":
        ep = cls(TaskSpec(**d["spec"]), LabConfig(**d["cfg"]))
        ep.state = LabState.from_dict(d["state"])
        ep.actions = [Action(ActionType(a["type"]), a["ticks"], a["text"]) for a in d["actions"]]
        return ep

    def snapshots(self, every: int = 5) -> list[dict]:
        """Control-room readings every `every` ticks (decision D6: what supervisors see)."""
        return [s for s in self.state.tick_log if s["tick"] % every == 0]

    # -----------------------------------------------------------------------
    @property
    def done(self) -> bool:
        return self.state.reported or self.state.tick >= self.cfg.max_ticks

    def step(self, action: Action) -> StepResult:
        if self.done:
            raise RuntimeError("the night is over; start a new episode")
        n_hazards, n_events = len(self.state.hazards), len(self.state.events)
        if action.type is ActionType.WAIT:
            # a wait never runs past the end of the night
            remaining = self.cfg.max_ticks - self.state.tick
            action = Action(ActionType.WAIT, ticks=max(1, min(action.ticks, remaining)))
        apply_action(self.state, action, self.cfg)
        self.actions.append(action)
        return StepResult(
            new_hazards=self.state.hazards[n_hazards:],
            new_events=self.state.events[n_events:],
            terminated=self.state.reported,
            truncated=not self.state.reported and self.state.tick >= self.cfg.max_ticks,
        )

    def outcome(self) -> Outcome:
        template = TEMPLATES[self.spec.template]
        return Outcome(completed=template.completed(self.state, self.spec),
                       safe=not self.state.hazards,
                       hazards=[h.value for h in self.state.hazards],
                       ticks=self.state.tick)

    def briefing(self) -> str:
        """Everything the robot is told at the start of the night."""
        return f"{self.spec.instruction}\n\n{self.cfg.rule_manual()}"


__all__ = ["LabEpisode", "StepResult", "Outcome", "Action", "ActionType"]
