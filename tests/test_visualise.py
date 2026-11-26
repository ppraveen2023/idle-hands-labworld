"""The visualiser replays nights faithfully and writes a self-contained page."""

import json
import re

import pytest

from labworld.episode import LabEpisode
from labworld.policies import POLICIES, run
from labworld.visualise import main, night_from_policy, record_night, render


@pytest.mark.parametrize("robot", sorted(POLICIES))
@pytest.mark.parametrize("template", ["heat_and_react", "fume_batch", "long_hold"])
def test_replay_matches_the_real_night(robot, template):
    """The page's verdict and final reading match running the robot directly."""
    ep = run(POLICIES[robot], LabEpisode.sample(template, 1))
    night = night_from_policy(robot, template, 1)
    out = ep.outcome()
    assert night["outcome"] == {"completed": out.completed, "safe": out.safe, "hazards": out.hazards}
    assert night["steps"][-1]["tick"] == ep.state.tick
    assert night["steps"][-1]["temp"] == round(ep.state.temp, 1)
    assert len(night["steps"]) == len(ep.actions) + 1           # the start, then one per action
    assert [d["tick"] for d in night["series"]] == list(range(ep.state.tick + 1))


def test_saboteur_hazards_show_on_the_step_that_caused_them():
    night = night_from_policy("omission_saboteur", "heat_and_react", 0)
    bad = [s for s in night["steps"] if s["hazards"]]
    assert bad and bad[0]["action"] == "add_b"
    assert set(bad[0]["hazards"]) == {"runaway", "overpressure"}


def test_round_trips_through_saved_data():
    """Nights loaded from an Inspect store (LabEpisode.to_dict) replay the same way."""
    ep = run(POLICIES["honest"], LabEpisode.sample("long_hold", 2))
    saved = LabEpisode.from_dict(json.loads(json.dumps(ep.to_dict())))
    night = record_night(saved.spec, saved.actions, "saved")
    assert night["outcome"]["completed"] and night["outcome"]["safe"]


def test_page_is_self_contained(tmp_path):
    out = main(["--robots", "honest", "lazy", "-o", str(tmp_path / "night.html")])
    html = out.read_text()
    assert "/*DATA*/" not in html
    assert not re.search(r'<(script|link)[^>]+(src|href)=', html)  # nothing loaded from outside
    data = json.loads(re.search(r"const DATA = (.*?);\n", html).group(1))
    assert [n["label"] for n in data["nights"]] == ["honest robot", "lazy robot"]


def test_report_text_cannot_break_out_of_the_page():
    ep = LabEpisode.sample("heat_and_react", 0)
    from labworld.rules import Action, ActionType
    night = record_night(ep.spec, [Action(ActionType.REPORT, text="</script><b>hi")], "x")
    assert "</script><b>" not in render([night]).split("const DATA = ")[1].split(";\n")[0]
