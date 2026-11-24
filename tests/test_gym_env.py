"""The Gymnasium environment follows the standard RL API."""

import gymnasium as gym
import numpy as np
from gymnasium.utils.env_checker import check_env

import labworld  # noqa: F401  (registers LabWorld-v0)
from labworld.gym_env import ACTION_NAMES, ACTIONS, LabWorldEnv


def test_passes_gymnasium_env_checker():
    check_env(LabWorldEnv(), skip_render_check=True)


def test_registered_with_gymnasium():
    env = gym.make("LabWorld-v0")
    obs, info = env.reset(seed=0)
    assert env.observation_space.contains(obs)
    assert "instruction" in info


def test_same_seed_same_night():
    a = LabWorldEnv().reset(seed=3)
    b = LabWorldEnv().reset(seed=3)
    assert np.array_equal(a[0], b[0]) and a[1]["instruction"] == b[1]["instruction"]


def test_template_option_picks_the_task():
    _, info = LabWorldEnv().reset(seed=0, options={"template": "long_hold"})
    assert info["template"] == "long_hold"


def test_random_agent_runs_full_nights():
    env = LabWorldEnv()
    rng = np.random.default_rng(0)
    for ep in range(20):
        env.reset(seed=ep)
        done = False
        while not done:
            _, reward, terminated, truncated, info = env.step(int(rng.integers(len(ACTIONS))))
            done = terminated or truncated
        assert "outcome" in info


def test_report_terminates_and_hazard_gives_negative_reward():
    env = LabWorldEnv()
    env.reset(seed=0, options={"template": "fume_batch"})
    _, reward, *_ = env.step(ACTION_NAMES.index("add_a"))     # hood is off: fumes
    assert reward < 0
    _, _, terminated, _, info = env.step(ACTION_NAMES.index("report"))
    assert terminated and info["outcome"]["safe"] is False


def test_end_on_hazard_option():
    env = LabWorldEnv(end_on_hazard=True)
    env.reset(seed=0, options={"template": "fume_batch"})
    _, _, terminated, _, _ = env.step(ACTION_NAMES.index("add_a"))
    assert terminated


def test_custom_reward_function():
    env = LabWorldEnv(reward_fn=lambda ep, result: 10.0 * len(result.new_hazards))
    env.reset(seed=0, options={"template": "fume_batch"})
    _, reward, *_ = env.step(ACTION_NAMES.index("add_a"))
    assert reward == 10.0
