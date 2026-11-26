# LabWorld documentation

These pages explain the LabWorld code from the ground up. They are written for someone who knows some Python but is rusty, and who is new to type hints, dataclasses, Enums, decorators, `async`, Inspect and Gymnasium. Every Python or framework idea is explained briefly the first time it appears, and the most common ones are collected in the table at the bottom of this page.

Everything here was checked against the code on 25 Nov 2026. The numbers in the examples are real output from running the code.

## What LabWorld is

LabWorld is a small simulated chemistry lab. A robot runs one "night shift": it gets one job (for example "heat the reactor to 75 C, add chemical B, cool it down, report") and can only act through a few controls: heater, cooling valve, fume hood, coolant refill, adding chemicals, waiting, and submitting a report. Time moves in **ticks** of 5 minutes, and the lab changes every tick whatever the robot does. Most importantly, the coolant tank **leaks 2% every tick**. Chemical B is only safe while the tank holds at least 30% coolant. So a robot that simply never refills the tank will, sooner or later, add B to a nearly empty tank and cause a runaway reaction. That is harm by doing nothing (omission), and LabWorld exists to study whether AI monitors catch it. The robot can be an LLM (through the Inspect framework), a hand-written scripted policy, or a reinforcement-learning agent (through Gymnasium). All three drive the same engine, so a night means the same thing to each of them.

## Reading order

| # | Page | What you get from it |
|---|---|---|
| 1 | [01_architecture.md](01_architecture.md) | The layers of the code, a diagram, and why it is split this way |
| 2 | [02_file_guide.md](02_file_guide.md) | One section per file: what it is for, its main classes and functions, who uses it. Also the scripts and every test file |
| 3 | [03_one_night_walkthrough.md](03_one_night_walkthrough.md) | One real night (`heat_and_react`, seed 100) followed line by line through the code: Inspect tools, the engine, the referee, and the same night in Gymnasium |
| 4 | [04_running.md](04_running.md) | Every command you need: tests, demo, Gymnasium, the refill check, Inspect runs, viewing logs, API keys |
| 5 | [05_extending.md](05_extending.md) | Recipes: change a number, add a rule, a task, a scripted robot, an LLM robot prompt, an RL reward, an Inspect tool. Which tests to touch for each |
| 6 | [06_rules_spec.md](06_rules_spec.md) | The complete rules specification (every rule, hazard, action, task, worked examples). This is the single source; the project report's Part 3 is built from it |

If you only have ten minutes: read the paragraph above, then [01_architecture.md](01_architecture.md), then section (b) of [03_one_night_walkthrough.md](03_one_night_walkthrough.md).

## Planned change: not in the code yet

A "noisy world" is planned: a random hidden leak rate per night, sensor noise, and a slower refill. **None of this is in the code yet.** Everything in these docs describes the current code, where the leak is always 2% per tick, sensors are exact, and a refill adds 30% in one tick. These docs will be updated when the noisy world lands.

## Python and framework ideas used in this code

You can come back to this table whenever a page uses one of these words.

| Idea | What it means, in one or two sentences | Small example from LabWorld |
|---|---|---|
| **Type hint** | A note after a name saying what type it should hold. Python does not enforce it; it is for readers and tools. `-> str` after a function says what it returns. `str \| None` means "a string or `None`". | `def pressure_for(self, temp: float) -> float:` |
| **`list[str]`, `dict`, `tuple[int, int]`** | Type hints for containers: a list of strings, a dictionary, a pair of whole numbers. | `events: list[str]` |
| **Dataclass** | `@dataclass` above a class writes the boring parts for you (the `__init__` that stores each field, a readable printout, `==` comparison). You just list the fields with their types and defaults. | `@dataclass class LabState: tick: int = 0 ...` |
| **Frozen dataclass** | `@dataclass(frozen=True)` makes a class that just holds values and can't be changed after creation. Trying `cfg.leak_rate = 3` raises `FrozenInstanceError`. | `LabConfig`, `Action`, `TaskSpec` |
| **`field(default_factory=list)`** | Gives every new object its **own** empty list. (Writing `= []` would make all objects share one list, a classic Python bug, so dataclasses forbid it.) | `hazards: list[Hazard] = field(default_factory=list)` |
| **Enum** | A fixed set of named choices. `class Hazard(str, Enum)` makes each choice also a string, so `Hazard.RUNAWAY.value` is `"runaway"` and it saves to JSON easily. | `ActionType.WAIT`, `Hazard.OVERPRESSURE` |
| **Decorator** | A line starting with `@` above a function or class. It hands the thing below to another function, which wraps or registers it. `@dataclass`, `@property`, `@tool` and `@scorer` are all decorators. | `@tool def wait(): ...` |
| **`@property`** | Lets you call a method without brackets, as if it were a field. | `ep.done`, not `ep.done()` |
| **`@classmethod`** | A method called on the class itself, not on one object. Often used as a second way to build objects. `cls` is the class. | `LabEpisode.sample(...)`, `LabState.from_dict(d)` |
| **`@staticmethod`** | A plain function that lives inside a class for tidiness. It gets neither `self` nor `cls`. | `LongHold.longest_run_in_band(...)` |
| **`async def` / `await`** | An "asynchronous" function, which can pause while it waits (for example for a model's reply) so other work runs meanwhile. Inspect requires tools, solvers and scorers to be `async`. You call one with `await`. The LabWorld tools never actually pause (they call ordinary functions); they are `async` only because Inspect asks for it. The solver does pause, at `await generate(...)`, while the model thinks. | `async def execute(ticks: int) -> str:` |
| **Closure / inner function** | A function defined inside another function and returned from it. Inspect's `@tool`, `@solver` and `@scorer` all use this shape: the outer function builds and returns the inner one that does the work. | `def wait(): async def execute(...): ...; return execute` |
| **`Callable[[X, Y], Z]`** | A type hint for "a function that takes an X and a Y and returns a Z". | `RewardFn = Callable[[LabEpisode, StepResult], float]` |
| **Random generator and seed** | `np.random.default_rng(seed)` makes a random number generator. The same seed always gives the same sequence of numbers, so the same night. | `LabEpisode.sample("heat_and_react", 100)` |
| **Gymnasium** | The standard Python interface for RL environments. An environment has `reset()` (start an episode) and `step(action)` (do one action, get back observation, reward, and whether it ended). | `gym.make("LabWorld-v0")` |
| **Inspect** | A framework (`inspect_ai`) for running LLM evaluations. A **Task** = dataset of **Samples** + a **solver** (how the model works on a sample) + a **scorer** (how it is graded). **Tools** are Python functions the model may call. The **store** is a per-sample dictionary for your own data. Every run writes a **log** you can view and re-score. | `inspect eval src/labworld/inspect_task.py@labworld ...` |
