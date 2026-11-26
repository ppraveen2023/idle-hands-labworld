"""
Honest-robot baselines for the non-Claude pilot models (3 nights each, seed 0).

    ..\.venv\Scripts\python.exe scripts/run_honest_baselines.py

Keys are loaded from ../.env and ~/.nodecode/auth.json into the child process
environment only; they are never printed.
"""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSPECT = ROOT.parent / ".venv" / "Scripts" / "inspect.exe"
LOG_DIR = ROOT / "logs" / "honest_baselines"

RUNS = [
    ("openai-api/nodecode/nodecode-cyber-v1", []),
    ("openrouter/nousresearch/hermes-4-405b", ["-M", "emulate_tools=true"]),
    ("openrouter/cognitivecomputations/dolphin-mistral-24b-venice-edition", ["-M", "emulate_tools=true"]),
]


def load_env() -> dict:
    env = dict(os.environ)
    for line in (ROOT.parent / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    nodecode = json.loads(Path("~/.nodecode/auth.json").expanduser().read_text())["api_keys"]["nodecode"]
    env["NODECODE_API_KEY"] = nodecode["key"]
    env["NODECODE_BASE_URL"] = "https://api.nodecode.ai/v1"
    return env


def main() -> None:
    env = load_env()
    for model, extra in RUNS:
        cmd = [str(INSPECT), "eval", "src/labworld/inspect_task.py@labworld", "--model", model,
               "-T", "robot=honest", "-T", "n_seeds=1", "-T", "seed_offset=0", "-T", "message_limit=80",
               "--log-dir", str(LOG_DIR), "--display", "plain", *extra]
        print("running", model, flush=True)
        r = subprocess.run(cmd, cwd=ROOT, env=env)
        print("exit", r.returncode, model, flush=True)


if __name__ == "__main__":
    main()
