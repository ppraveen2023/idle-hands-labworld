"""
See a night as a page you can step through.

Writes one self-contained HTML file: the job, a step-by-step replay of what the
robot did and what happened, the dashboard at that moment, and two small charts
(temperature and coolant) over the whole night.

    python -m labworld.visualise                                  # honest vs omission_saboteur
    python -m labworld.visualise --robots honest lazy --template long_hold --seed 3
    python -m labworld.visualise --log logs/smoke/some-run.eval   # nights from an Inspect log
    python -m labworld.visualise -o night.html --open

Every night is replayed from its starting conditions and its list of actions,
through the same engine as everything else, so the page shows exactly what the
referee judged.
"""

import argparse
import json
import webbrowser
from pathlib import Path

from .config import DEFAULT_CONFIG, LabConfig
from .episode import LabEpisode
from .policies import POLICIES
from .rules import Action, ActionType
from .tasks import TaskSpec


# ---------------------------------------------------------------------------
# What each action does, in one line (built from the same numbers as the rules)
# ---------------------------------------------------------------------------
def action_help(cfg: LabConfig = DEFAULT_CONFIG) -> dict[str, str]:
    return {
        "heater_on": f"Temperature now rises {cfg.heater_rate:g} C every tick.",
        "heater_off": f"Temperature now drifts {cfg.drift_rate:g} C per tick back toward {cfg.room_temp:g} C.",
        "cooling_open": (f"Cools {cfg.cooling_rate:g} C per tick, but uses "
                         f"{cfg.cooling_coolant_use:g}% coolant per tick."),
        "cooling_close": "Cooling stops; coolant stops being used (the leak continues).",
        "hood_on": "Fumes are extracted, so chemical A is safe to add.",
        "hood_off": "Adding chemical A now would expose people to fumes.",
        "refill": f"Adds {cfg.refill_amount:g}% coolant.",
        "add_a": "Safe only with the fume hood on.",
        "add_b": (f"Safe only with at least {cfg.b_safe_threshold:g}% coolant; "
                  f"otherwise the reaction runs away (+{cfg.b_runaway_heat:g} C)."),
        "wait": f"Time passes. The tank still leaks {cfg.leak_rate:g}% per tick.",
        "report": "The robot says it is done. The night ends here.",
    }


# ---------------------------------------------------------------------------
# Turning a night into plain data for the page
# ---------------------------------------------------------------------------
def _reading(ep: LabEpisode) -> dict:
    s = ep.state
    return {"tick": s.tick, "temp": round(s.temp, 1), "pressure": round(s.pressure, 2),
            "coolant": round(s.coolant, 1), "heater_on": s.heater_on,
            "cooling_open": s.cooling_open, "hood_on": s.hood_on}


def record_night(spec: TaskSpec, actions: list[Action], label: str,
                 cfg: LabConfig = DEFAULT_CONFIG) -> dict:
    """Replay `actions` from the start of the night and record every step."""
    ep = LabEpisode(spec, cfg)
    steps = [{"action": None, "events": ["Start of the night."], "hazards": [], **_reading(ep)}]
    for action in actions:
        if ep.done:
            break
        result = ep.step(action)
        steps.append({
            "action": action.describe(),
            "kind": action.type.value,
            "report": action.text if action.type is ActionType.REPORT else "",
            "events": [e.split(": ", 1)[-1] for e in result.new_events
                       if "HAZARD" not in e],            # hazards get their own red badges
            "hazards": [h.value for h in result.new_hazards],
            **_reading(ep),
        })
    start = steps[0]
    series = [{k: start[k] for k in ("tick", "temp", "coolant", "pressure")}]
    series += [{k: r[k] for k in ("tick", "temp", "coolant", "pressure")} for r in ep.state.tick_log]
    out = ep.outcome()
    return {
        "label": label,
        "template": spec.template,
        "instruction": spec.instruction,
        "params": spec.params,
        "steps": steps,
        "series": series,
        "outcome": {"completed": out.completed, "safe": out.safe, "hazards": out.hazards},
    }


def night_from_policy(robot: str, template: str = "heat_and_react", seed: int = 0) -> dict:
    """Run one of the scripted robots for a night and record it."""
    ep = LabEpisode.sample(template, seed)
    policy = POLICIES[robot]
    actions = []
    while not ep.done:
        action = policy(ep)
        ep.step(action)
        actions.append(ep.actions[-1])          # the action as recorded (waits are clamped)
    return record_night(ep.spec, actions, f"{robot} robot", ep.cfg)


def nights_from_log(path: str | Path) -> list[dict]:
    """Every night saved in an Inspect log (needs the `inspect` extra)."""
    from inspect_ai.log import read_eval_log

    from .inspect_task import STORE_KEY

    log = read_eval_log(str(path))
    nights = []
    for sample in log.samples or []:
        data = (sample.store or {}).get(STORE_KEY)
        if not data:
            continue
        saved = LabEpisode.from_dict(data)
        label = f"{log.eval.model} · {sample.id}"
        if sample.error:
            label += " (stopped by an error)"
        nights.append(record_night(saved.spec, saved.actions, label, saved.cfg))
    return nights


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------
def render(nights: list[dict], cfg: LabConfig = DEFAULT_CONFIG) -> str:
    if not nights:
        raise ValueError("nothing to show: no nights given")
    data = {
        "nights": nights,
        "help": action_help(cfg),
        "limits": {"b_safe": cfg.b_safe_threshold, "overpressure_bar": cfg.overpressure_bar,
                   "overpressure_temp": cfg.overpressure_temp(), "max_ticks": cfg.max_ticks},
    }
    payload = json.dumps(data).replace("</", "<\\/")
    return _PAGE.replace("/*DATA*/null", payload)


def main(argv: list[str] | None = None) -> Path:
    p = argparse.ArgumentParser(description="Write a step-through page for LabWorld nights.")
    p.add_argument("--robots", nargs="+", default=["honest", "omission_saboteur"],
                   choices=sorted(POLICIES), help="scripted robots to compare")
    p.add_argument("--template", default="heat_and_react")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--log", help="an Inspect .eval log; shows its nights instead of scripted robots")
    p.add_argument("-o", "--out", default="labworld_night.html")
    p.add_argument("--open", action="store_true", help="open the page in your browser")
    args = p.parse_args(argv)

    if args.log:
        nights = nights_from_log(args.log)
    else:
        nights = [night_from_policy(r, args.template, args.seed) for r in args.robots]
    out = Path(args.out)
    out.write_text(render(nights), encoding="utf-8")
    print(f"Wrote {out} ({len(nights)} night{'s' if len(nights) != 1 else ''})")
    if args.open:
        webbrowser.open(out.resolve().as_uri())
    return out


_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LabWorld · night replay</title>
<style>
  :root {
    --bg: #fafaf9; --panel: #ffffff; --ink: #1c1917; --muted: #78716c; --line: #e7e5e4;
    --temp: #c2410c; --cool: #0369a1; --good: #15803d; --bad: #b91c1c; --bad-bg: #fef2f2;
    --accent: #1c1917;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #1c1917; --panel: #262321; --ink: #f5f5f4; --muted: #a8a29e; --line: #3a3532;
      --temp: #fb923c; --cool: #38bdf8; --good: #4ade80; --bad: #f87171; --bad-bg: #3b1d1d;
      --accent: #f5f5f4;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink);
         font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; }
  main { max-width: 920px; margin: 0 auto; padding: 28px 20px 48px; }
  h1 { font-size: 20px; margin: 0 0 4px; letter-spacing: -0.01em; }
  .job { color: var(--muted); margin: 0 0 20px; max-width: 70ch; }
  .tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
  .tab { border: 1px solid var(--line); background: var(--panel); color: var(--ink); border-radius: 8px;
         padding: 6px 12px; font: inherit; cursor: pointer; display: flex; gap: 8px; align-items: center; }
  .tab[aria-pressed="true"] { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
  .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
  .card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px; }
  .verdict { display: flex; gap: 18px; flex-wrap: wrap; margin-bottom: 14px; font-size: 14px; }
  .verdict b { font-weight: 600; }
  .ok { color: var(--good); } .no { color: var(--bad); }
  .step { display: grid; grid-template-columns: 1fr auto; gap: 10px 16px; align-items: start; }
  .step-count { color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; }
  .what { font-size: 18px; font-weight: 600; margin: 2px 0 6px; }
  .what code { font: 600 16px ui-monospace, SFMono-Regular, Menlo, monospace; }
  .events { margin: 0; padding: 0; list-style: none; }
  .events li { margin: 2px 0; }
  .hazard { background: var(--bad-bg); color: var(--bad); border-radius: 6px; padding: 4px 8px;
            font-weight: 600; display: inline-block; margin-top: 6px; }
  .why { color: var(--muted); font-size: 13px; margin-top: 6px; }
  .controls { display: flex; gap: 6px; align-items: center; }
  .controls button { border: 1px solid var(--line); background: var(--bg); color: var(--ink);
                     border-radius: 8px; width: 38px; height: 34px; font-size: 14px; cursor: pointer; }
  .controls button.wide { width: 64px; }
  .controls button:hover { border-color: var(--muted); }
  input[type=range] { width: 100%; grid-column: 1 / -1; accent-color: var(--accent); margin: 4px 0 0; }
  .tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 14px 0; }
  .tile { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; }
  .tile .k { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }
  .tile .v { font-size: 26px; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.2; }
  .tile .s { color: var(--muted); font-size: 12px; }
  .tile.alarm { border-color: var(--bad); } .tile.alarm .v { color: var(--bad); }
  .pills { display: flex; flex-direction: column; gap: 4px; margin-top: 4px; font-size: 13px; }
  .pill { display: flex; justify-content: space-between; }
  .pill span:last-child { font-weight: 600; }
  .on { color: var(--good); } .off { color: var(--muted); }
  .chart { margin-top: 10px; }
  .chart h2 { font-size: 13px; font-weight: 600; margin: 0 0 2px; color: var(--muted); }
  svg { width: 100%; height: auto; display: block; overflow: visible; }
  svg text { font: 11px -apple-system, system-ui, sans-serif; fill: var(--muted); }
  .foot { color: var(--muted); font-size: 12px; margin-top: 16px; }
  @media (max-width: 640px) { .tiles { grid-template-columns: repeat(2, 1fr); } }
</style>
</head>
<body>
<main>
  <h1>LabWorld · night replay</h1>
  <p class="job" id="job"></p>
  <div class="tabs" id="tabs"></div>

  <div class="card">
    <div class="verdict" id="verdict"></div>
    <div class="step">
      <div>
        <div class="step-count" id="count"></div>
        <div class="what" id="what"></div>
        <ul class="events" id="events"></ul>
        <div class="why" id="why"></div>
      </div>
      <div class="controls">
        <button id="first" title="Start (Home)">⏮</button>
        <button id="prev" title="Previous step (←)">◀</button>
        <button id="play" class="wide" title="Play / pause (space)">Play</button>
        <button id="next" title="Next step (→)">▶</button>
      </div>
      <input type="range" id="slider" min="0" value="0" aria-label="Step">
    </div>
  </div>

  <div class="tiles" id="tiles"></div>

  <div class="card">
    <div class="chart"><h2>Temperature (C)</h2><svg id="tempChart" viewBox="0 0 880 190"></svg></div>
    <div class="chart"><h2>Coolant (%)</h2><svg id="coolChart" viewBox="0 0 880 150"></svg></div>
  </div>
  <p class="foot">Keys: ← → step, space play, Home start. Faded lines are what hasn't happened yet.</p>
</main>

<script>
const DATA = /*DATA*/null;
const L = DATA.limits;
let night = 0, step = 0, timer = null;
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function tabs() {
  $("tabs").innerHTML = DATA.nights.map((n, i) => {
    const good = n.outcome.completed && n.outcome.safe;
    return `<button class="tab" aria-pressed="${i === night}" data-i="${i}">
      <span class="dot" style="background:var(${good ? "--good" : "--bad"})"></span>${esc(n.label)}</button>`;
  }).join("");
  $("tabs").style.display = DATA.nights.length > 1 ? "" : "none";
  $("tabs").querySelectorAll(".tab").forEach(b => b.onclick = () => { night = +b.dataset.i; step = 0; stop(); draw(); });
}

function verdict(n) {
  const o = n.outcome;
  const yes = (v, a, b) => `<span class="${v ? "ok" : "no"}">${v ? a : b}</span>`;
  return `<span><b>Job done:</b> ${yes(o.completed, "yes", "no")}</span>
          <span><b>Safe:</b> ${yes(o.safe, "yes", "no — " + o.hazards.join(", "))}</span>
          <span><b>Steps:</b> ${n.steps.length - 1}</span>`;
}

function tile(k, v, s, alarm) {
  return `<div class="tile${alarm ? " alarm" : ""}"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`;
}

function draw() {
  const n = DATA.nights[night], s = n.steps[step], p = n.params;
  $("job").textContent = n.instruction;
  tabs();
  $("verdict").innerHTML = verdict(n);
  $("slider").max = n.steps.length - 1; $("slider").value = step;
  $("count").textContent = `Step ${step} of ${n.steps.length - 1} · tick ${s.tick} of ${L.max_ticks}`;
  $("what").innerHTML = s.action ? `Robot: <code>${esc(s.action)}</code>` : "Before the robot does anything";
  const ev = s.events.map(e => `<li>${esc(e)}</li>`);
  if (s.report) ev.push(`<li>Report: “${esc(s.report)}”</li>`);
  if (s.hazards.length) ev.push(`<li>${s.hazards.map(h => `<span class="hazard">⚠ ${esc(h.replace("_", " ").toUpperCase())}</span>`).join(" ")}</li>`);
  $("events").innerHTML = ev.join("");
  $("why").textContent = s.kind ? DATA.help[s.kind] || "" : "";

  const target = p.target != null ? `goal ≥ ${p.target} C` : p.low != null ? `keep ${p.low}–${p.high} C` : "";
  $("tiles").innerHTML =
    tile("Temperature", `${Math.round(s.temp)} C`, target, s.temp > L.overpressure_temp) +
    tile("Coolant", `${Math.round(s.coolant)}%`, `chemical B needs ≥ ${L.b_safe}%`, s.coolant < L.b_safe) +
    tile("Pressure", `${s.pressure.toFixed(1)} bar`, `limit ${L.overpressure_bar} bar`, s.pressure > L.overpressure_bar) +
    `<div class="tile"><div class="k">Switches</div><div class="pills">
      ${[["Heater", s.heater_on], ["Cooling valve", s.cooling_open], ["Fume hood", s.hood_on]].map(([k, v]) =>
        `<div class="pill"><span>${k}</span><span class="${v ? "on" : "off"}">${v ? "ON" : "off"}</span></div>`).join("")}
    </div></div>`;

  const refsT = [{y: L.overpressure_temp, label: "overpressure", color: "--bad"}];
  if (p.target != null) refsT.push({y: p.target, label: "goal", color: "--muted"});
  if (p.cool_below != null) refsT.push({y: p.cool_below, label: "cool below", color: "--muted"});
  if (p.low != null) refsT.push({y: p.low, label: "band", color: "--muted"}, {y: p.high, label: "", color: "--muted"});
  chart($("tempChart"), n, "temp", "--temp", refsT, s.tick, 190);
  chart($("coolChart"), n, "coolant", "--cool", [{y: L.b_safe, label: "B needs", color: "--bad"}], s.tick, 150, 100);
}

function chart(svg, n, key, color, refs, now, H, fixedMax) {
  const W = 880, padL = 36, padR = 70, padT = 8, padB = 22;
  const vals = n.series.map(d => d[key]).concat(refs.map(r => r.y));
  const yMax = fixedMax || Math.ceil(Math.max(...vals) / 20) * 20 + 10;
  const x = t => padL + (t / L.max_ticks) * (W - padL - padR);
  const y = v => padT + (1 - v / yMax) * (H - padT - padB);
  const path = pts => pts.map((d, i) => `${i ? "L" : "M"}${x(d.tick).toFixed(1)},${y(d[key]).toFixed(1)}`).join("");
  const past = n.series.filter(d => d.tick <= now), future = n.series.filter(d => d.tick >= now);
  let g = "";
  for (let v = 0; v <= yMax; v += yMax > 120 ? 40 : 20)
    g += `<line x1="${padL}" x2="${W - padR}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/>
          <text x="${padL - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`;
  for (let t = 0; t <= L.max_ticks; t += 5) g += `<text x="${x(t)}" y="${H - 6}" text-anchor="middle">${t}</text>`;
  for (const r of refs)
    g += `<line x1="${padL}" x2="${W - padR}" y1="${y(r.y)}" y2="${y(r.y)}" stroke="var(${r.color})" stroke-dasharray="4 4" opacity="0.8"/>
          <text x="${W - padR + 6}" y="${y(r.y) + 4}" style="fill:var(${r.color})">${r.label}</text>`;
  // action markers: one small tick on the x-axis per robot action, the current one highlighted
  n.steps.slice(1).forEach((st, i) => {
    const at = n.steps[i].tick;   // the action happened at the tick before this step's reading
    const cur = i + 1 === step;
    g += `<line x1="${x(at)}" x2="${x(at)}" y1="${H - padB}" y2="${H - padB - (cur ? 10 : 5)}"
            stroke="var(${st.hazards.length ? "--bad" : "--muted"})" stroke-width="${cur ? 2.5 : 1.5}"><title>${esc(st.action)} at tick ${at}</title></line>`;
  });
  g += `<path d="${path(future)}" fill="none" stroke="var(${color})" stroke-width="2" opacity="0.22"/>
        <path d="${path(past)}" fill="none" stroke="var(${color})" stroke-width="2.5"/>
        <line x1="${x(now)}" x2="${x(now)}" y1="${padT}" y2="${H - padB}" stroke="var(--ink)" opacity="0.25"/>`;
  const cur = n.series.find(d => d.tick === now);
  if (cur) g += `<circle cx="${x(now)}" cy="${y(cur[key])}" r="4.5" fill="var(${color})" stroke="var(--panel)" stroke-width="2"/>`;
  svg.innerHTML = g;
}

function go(i) { const n = DATA.nights[night]; step = Math.max(0, Math.min(n.steps.length - 1, i)); draw(); }
function stop() { clearInterval(timer); timer = null; $("play").textContent = "Play"; }
function play() {
  if (timer) return stop();
  if (step >= DATA.nights[night].steps.length - 1) step = 0;
  $("play").textContent = "Pause";
  timer = setInterval(() => { if (step >= DATA.nights[night].steps.length - 1) return stop(); go(step + 1); }, 900);
}
$("first").onclick = () => { stop(); go(0); };
$("prev").onclick = () => { stop(); go(step - 1); };
$("next").onclick = () => { stop(); go(step + 1); };
$("play").onclick = play;
$("slider").oninput = e => { stop(); go(+e.target.value); };
document.addEventListener("keydown", e => {
  if (e.key === "ArrowRight") { stop(); go(step + 1); }
  else if (e.key === "ArrowLeft") { stop(); go(step - 1); }
  else if (e.key === "Home") { stop(); go(0); }
  else if (e.key === " ") { e.preventDefault(); play(); }
});
draw();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
