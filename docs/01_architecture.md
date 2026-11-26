# 1. Architecture: how the code is layered

LabWorld is one small Python package, `labworld`, in [`src/labworld/`](../src/labworld/). It uses the **src layout**: the package lives in `src/` rather than at the top of the repo, so tests can only import it the way a user would (after installing it, or via the `pythonpath = ["src"]` setting for pytest in [`pyproject.toml`](../pyproject.toml)).

## The idea in one sentence

There is **one engine** that knows the lab's physics and what a night is, and **two thin front ends** that let different kinds of robots drive it: a Gymnasium environment for RL agents, and an Inspect task for LLM robots. Scripted robots drive the engine directly.

## The diagram

```
                        THE ENGINE (pure Python, knows nothing about RL or LLMs)
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │                                                                              │
   │  config.py    LabConfig: every number in the physics, + the rule manual text │
   │      │                                                                       │
   │      ▼                                                                       │
   │  state.py     LabState: the dashboard at one moment. Hazard: the 3 accidents │
   │      │                                                                       │
   │      ▼                                                                       │
   │  rules.py     Action, tick(), apply_action(): the physics, rules R1-R7       │
   │      │                                                                       │
   │      ▼                                                                       │
   │  tasks.py     3 job templates: sample a night, the instruction, "job done?"  │
   │      │                                                                       │
   │      ▼                                                                       │
   │  episode.py   LabEpisode: one night = task + state + action list.            │
   │               step(action), outcome(), save/load as plain data               │
   └──────────────┬──────────────────────────┬──────────────────────┬─────────────┘
                  │                          │                      │
                  ▼                          ▼                      ▼
   gym_env.py                     inspect_task.py            policies.py
   LabWorldEnv, "LabWorld-v0"     8 @tools, lab_robot        scripted robots:
   for RL agents:                 solver, referee scorer     honest, lazy,
   reset() / step(int)            for LLM robots             omission_saboteur,
   13-number observation,           │                        commission_saboteur
   reward_fn                        │ uses                     │ used by
                                    ▼                          ▼
                                  prompts.py                 demo.py, tests,
                                  system prompts:            test_inspect_task
                                  honest, lazy, saboteur     (mock LLM replays them)

   refill_check.py   a fast, separate copy of R1-R5 used to search every refill-free plan
                     (cross-checked against rules.py); run by scripts/check_refill_needed.py
```

The arrows inside the engine mean "is used by". Each layer only imports the layers above it. For example `rules.py` imports `config.py` and `state.py`, but never `tasks.py` or `episode.py`. The package docstring in [`__init__.py`](../src/labworld/__init__.py) says the same thing.

## What each layer is responsible for

| Layer | File | Responsible for | Does **not** know about |
|---|---|---|---|
| Numbers | [`config.py`](../src/labworld/config.py) | Every constant (heater +5 C, leak 2%, the 30% line for B, 40-tick night, ...) and the plain-English rule manual built from them | Anything else |
| Dashboard | [`state.py`](../src/labworld/state.py) | What the lab looks like at one moment (`LabState`), plus a diary of events and a history of every tick | How the state changes |
| Physics | [`rules.py`](../src/labworld/rules.py) | What each action does, and what happens every tick (`tick`, `apply_action`) | Jobs, success, RL, LLMs |
| Jobs | [`tasks.py`](../src/labworld/tasks.py) | The three nightly jobs: how to sample one, the instruction text, and "was the job done?" | Safety (judged separately), RL, LLMs |
| One night | [`episode.py`](../src/labworld/episode.py) | Ties a job and a state together; steps the night; enforces the time limit; gives the referee's verdict (`Outcome`); saves and loads the whole night | RL, LLMs |
| RL front end | [`gym_env.py`](../src/labworld/gym_env.py) | Turns a `LabEpisode` into a Gymnasium environment: integer actions, a number vector as observation, a reward | LLMs |
| LLM front end | [`inspect_task.py`](../src/labworld/inspect_task.py) | Turns a `LabEpisode` into an Inspect task: tools, a solver, a scorer, a dataset of nights | RL |
| Scripted robots | [`policies.py`](../src/labworld/policies.py) | Hand-written robots that test the environment | - |
| LLM instructions | [`prompts.py`](../src/labworld/prompts.py) | The system prompt for each LLM robot type | - |
| Refill proof | [`refill_check.py`](../src/labworld/refill_check.py) | An exhaustive search showing no plan can finish safely without a refill | - |
| Demo | [`demo.py`](../src/labworld/demo.py) | Prints one scripted night tick by tick | - |

## Why it is split this way

**One shared engine, so a night means the same thing to every robot.** The research question compares different robots (an RL attacker, LLM robots with different prompts, scripted reference robots) and different monitors. Those comparisons only make sense if "heater on", "wait 3 ticks", "runaway" and "job done" mean exactly the same thing for all of them. If the Gymnasium version and the Inspect version each had their own copy of the physics, the copies would slowly drift apart and nobody would notice. So the physics lives in one place (`rules.py`), the definition of a night lives in one place (`LabEpisode`), and the two front ends are only translators:

| | RL agent (Gymnasium) | LLM robot (Inspect) | Scripted robot |
|---|---|---|---|
| Chooses an action as | an integer 0-14 | a tool call such as `wait(ticks=3)` | a Python function returning an `Action` |
| Translated into | `ACTIONS[i]`, an `Action` | `Action(ActionType.WAIT, ticks=3)` inside the tool | (already an `Action`) |
| Then calls | `LabEpisode.step(action)` | `LabEpisode.step(action)` | `LabEpisode.step(action)` |
| Judged by | `LabEpisode.outcome()` (inside the reward) | `LabEpisode.outcome()` (inside the `referee` scorer) | `LabEpisode.outcome()` |

You can see this in two places. [`tests/test_inspect_task.py`](../tests/test_inspect_task.py) replays a scripted robot's actions as LLM tool calls inside Inspect and gets the same verdict. And the same seed gives the same night everywhere: `LabEpisode.sample(seed=100)` and `env.reset(seed=100)` both produce the same `long_hold` night (start 29 C, 41% coolant, hold 10 ticks), because both draw from a NumPy generator seeded the same way (see section (e) of [03_one_night_walkthrough.md](03_one_night_walkthrough.md)).

**Every number in one place, so the manual can't lie.** The rule manual that robots and supervisors read is generated by `LabConfig.rule_manual()` from the same numbers the physics uses. Change `leak_rate` and the manual changes with it.

**The physics is plain functions over a plain record.** `tick(state, cfg)` and `apply_action(state, action, cfg)` just change a `LabState` in place. They are easy to test on tiny hand-built situations ([`tests/test_rules.py`](../tests/test_rules.py) does exactly that for every rule) and have no hidden state.

**A night can be saved as plain data.** `LabEpisode.to_dict()` turns a whole night (task, config, state, actions) into dictionaries, lists, numbers and strings. Inspect needs this: its per-sample store can only hold such plain data, and the night must survive between tool calls. It also means a finished Inspect log contains everything needed to judge the night again later (`inspect score`) without re-running the robot.

**Jobs are separate from safety.** `tasks.py` only answers "was the job done?". Safety is simply "no hazard was recorded". `LabEpisode.outcome()` combines them: success = completed and safe. This matters because a saboteur can complete the job *and* cause an accident (the commission saboteur on `long_hold` does exactly that).

## Where a night lives in each front end

- **Scripted robots and the demo:** a normal Python variable, `ep = LabEpisode.sample(...)`, stepped in a `while not ep.done:` loop.
- **Gymnasium:** the environment object keeps it as `self.episode`. `reset()` makes a new one; `step()` steps it.
- **Inspect:** the night is stored as a dictionary in the sample's store under the key `"labworld"`. Every tool call loads it (`LabEpisode.from_dict`), steps it once, and saves it back (`to_dict`). See [03_one_night_walkthrough.md](03_one_night_walkthrough.md) for a full trace.

## What is not built yet

- **Supervisors (AI monitors).** Design decision D6 in [`DECISIONS.md`](../DECISIONS.md) says what they will see. The code already provides the 5-tick snapshots they will use (`LabEpisode.snapshots()`), and the referee attaches them to every Inspect score, but there is no monitor code yet.
- **The RL attacker's training code.** The environment and its replaceable `reward_fn` exist; no training script exists yet.
- **The noisy world** (see [README.md](README.md)).
