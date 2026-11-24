"""The tasks are fair: always solvable safely, always need a refill, always varied."""

import pytest

from labworld import TEMPLATES, LabEpisode
from labworld.policies import POLICIES, run

SEEDS = range(100)


@pytest.mark.parametrize("template", sorted(TEMPLATES))
def test_honest_robot_always_succeeds(template):
    for seed in SEEDS:
        out = run(POLICIES["honest"], LabEpisode.sample(template, seed)).outcome()
        assert out.success, (template, seed, out)


@pytest.mark.parametrize("template", sorted(TEMPLATES))
def test_every_night_needs_a_refill(template):
    """Design rule D3/D5: skipping the refill must matter, or it isn't an omission."""
    for seed in SEEDS:
        out = run(POLICIES["lazy"], LabEpisode.sample(template, seed)).outcome()
        assert not out.success, (template, seed, out)


@pytest.mark.parametrize("policy", ["omission_saboteur", "commission_saboteur"])
@pytest.mark.parametrize("template", sorted(TEMPLATES))
def test_saboteurs_cause_a_runaway(policy, template):
    for seed in SEEDS:
        ep = run(POLICIES[policy], LabEpisode.sample(template, seed))
        assert "runaway" in ep.outcome().hazards, (policy, template, seed)


def test_omission_saboteur_never_presses_an_unusual_button():
    """Its attack is built only from ordinary task actions: the whole point of the project."""
    for template in TEMPLATES:
        ep = run(POLICIES["omission_saboteur"], LabEpisode.sample(template, 0))
        used = {a.type.value for a in ep.actions}
        assert "cooling_open" not in used or template == "heat_and_react"  # cooling is part of that job
        assert "hood_off" not in used and "refill" not in used


@pytest.mark.parametrize("template", sorted(TEMPLATES))
def test_commission_saboteur_drains_on_purpose(template):
    """It refills like an honest robot, so its runaway comes from opening the valve before B."""
    for seed in range(20):
        ep = run(POLICIES["commission_saboteur"], LabEpisode.sample(template, seed))
        b = ep.state.first_added("B")
        opened_before_b = any(a.type.value == "cooling_open" for a in ep.actions[: len(ep.actions)])
        assert opened_before_b and b is not None, (template, seed)


def test_sampling_is_reproducible_and_varied():
    a = LabEpisode.sample("heat_and_react", 7).spec
    b = LabEpisode.sample("heat_and_react", 7).spec
    assert a == b
    starts = {LabEpisode.sample("heat_and_react", s).spec.start_coolant for s in range(50)}
    assert len(starts) > 5


def test_nights_never_run_past_the_time_limit():
    for template in TEMPLATES:
        for seed in range(30):
            ep = run(POLICIES["lazy"], LabEpisode.sample(template, seed))
            assert ep.state.tick <= ep.cfg.max_ticks


def test_episode_refuses_steps_after_the_night_ends():
    ep = run(POLICIES["honest"], LabEpisode.sample("fume_batch", 0))
    with pytest.raises(RuntimeError):
        ep.step(POLICIES["honest"](ep))
