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


# --- the live page (--serve) -------------------------------------------------
import threading
import urllib.error
import urllib.request

from labworld.visualise import night_from_llm, run_request, serve


def test_run_request_rejects_bad_input():
    for bad in [{"kind": "scripted", "robot": "nobody", "template": "heat_and_react"},
                {"kind": "scripted", "robot": "honest", "template": "no_such_job"},
                {"kind": "llm", "robot": "honest", "template": "heat_and_react", "model": "x",
                 "message_limit": 5000},
                {"kind": "shell", "robot": "honest", "template": "heat_and_react"}]:
        with pytest.raises(ValueError):
            run_request(bad)


def test_llm_night_through_inspect(tmp_path):
    """An LLM night runs through the real Inspect task (mock model: no API calls)."""
    nights = night_from_llm("mockllm/model", "honest", "fume_batch", 0, 20, str(tmp_path))
    assert len(nights) == 1 and nights[0]["template"] == "fume_batch"
    assert "mockllm/model" in nights[0]["label"]


@pytest.fixture
def live_server():
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    t = threading.Thread(target=serve, args=([night_from_policy("honest")], port), daemon=True)
    t.start()
    import time
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://localhost:{port}/", timeout=1)
            break
        except OSError:
            time.sleep(0.05)
    return port


def _post(port, body, ctype="application/json", host=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/run", data=json.dumps(body).encode(),
                                 headers={"Content-Type": ctype, **({"Host": host} if host else {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def test_live_page_runs_a_scripted_night(live_server):
    html = urllib.request.urlopen(f"http://localhost:{live_server}/").read().decode()
    assert '"live": true' in html
    status, body = _post(live_server, {"kind": "scripted", "robot": "omission_saboteur",
                                       "template": "heat_and_react", "seed": 0})
    assert status == 200 and body["nights"][0]["outcome"]["safe"] is False
    # the new night is kept, so a reload shows it too
    assert "omission_saboteur robot" in urllib.request.urlopen(f"http://localhost:{live_server}/").read().decode()


def test_live_page_refuses_requests_other_sites_could_make(live_server):
    ok = {"kind": "scripted", "robot": "honest", "template": "heat_and_react"}
    assert _post(live_server, ok, ctype="text/plain")[0] == 403          # a plain cross-site form post
    assert _post(live_server, ok, host="evil.example:80")[0] == 403      # DNS rebinding
    assert _post(live_server, {"kind": "scripted", "robot": "x", "template": "heat_and_react"})[0] == 400
