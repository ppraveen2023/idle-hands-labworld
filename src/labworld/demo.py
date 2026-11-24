"""
Watch one night, tick by tick.

    python -m labworld.demo                          # honest robot, heat_and_react
    python -m labworld.demo omission_saboteur        # the robot that does nothing
    python -m labworld.demo commission_saboteur long_hold 3
"""

import sys

from .episode import LabEpisode
from .policies import POLICIES


def show(policy_name: str = "honest", template: str = "heat_and_react", seed: int = 0) -> None:
    ep = LabEpisode.sample(template, seed)
    policy = POLICIES[policy_name]
    print(f"Robot: {policy_name}   Task: {template}   Seed: {seed}")
    print(f"Job: {ep.spec.instruction}")
    print(f"Start: {ep.state.sensor_text()}\n")
    print(f"{'action':16} {'tick':>4} {'temp':>6} {'coolant':>8} {'pressure':>9}  notes")
    while not ep.done:
        action = policy(ep)
        result = ep.step(action)
        s = ep.state
        notes = ", ".join(h.value.upper() for h in result.new_hazards)
        print(f"{action.describe():16} {s.tick:>4} {s.temp:>6.0f} {s.coolant:>7.0f}% {s.pressure:>8.1f}  {notes}")
    out = ep.outcome()
    print(f"\nReferee: job done={out.completed}  safe={out.safe}  hazards={out.hazards or 'none'}")


if __name__ == "__main__":
    args = sys.argv[1:]
    show(args[0] if len(args) > 0 else "honest",
         args[1] if len(args) > 1 else "heat_and_react",
         int(args[2]) if len(args) > 2 else 0)
