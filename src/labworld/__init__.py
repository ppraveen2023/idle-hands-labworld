"""LabWorld: a small simulated reactor lab that keeps changing on its own.

Layers (each only depends on the ones above it):
    config   - every number that defines the physics, plus the generated rule manual
    state    - the lab's dashboard (LabState) and the Hazard list
    rules    - actions and the clock (tick, apply_action): the physics
    tasks    - the nightly jobs: sampling, instructions, completion checks
    episode  - one night (LabEpisode): the engine shared by RL and Inspect
    gym_env  - the Gymnasium RL environment ("LabWorld-v0")
    policies - scripted reference robots (honest, lazy, saboteurs)
"""

from gymnasium.envs.registration import register

from .config import DEFAULT_CONFIG, LabConfig
from .episode import LabEpisode, Outcome, StepResult
from .rules import Action, ActionType, apply_action, tick
from .state import Hazard, LabState
from .tasks import TEMPLATES, TaskSpec

register(id="LabWorld-v0", entry_point="labworld.gym_env:LabWorldEnv")

__all__ = ["DEFAULT_CONFIG", "LabConfig", "LabEpisode", "Outcome", "StepResult", "Action",
           "ActionType", "apply_action", "tick", "Hazard", "LabState", "TEMPLATES", "TaskSpec"]
