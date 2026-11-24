# Related work: what we build on, what's done, what's worth researching

*Last updated 24 Nov 2026. A targeted search, not a full literature review.*

**Status key:** ✅ we opened and read the source. ◐ seen in search results or in earlier research notes, not re-read in full.

---

## 1. What this project builds on

### AI control (the core framework)
| Work | What it did | How we use it | Status |
|---|---|---|---|
| [Greenblatt, Shlegeris, Sachan, Roger (2023). *AI Control: Improving Safety Despite Intentional Subversion*](https://arxiv.org/abs/2312.06942) | Untrusted model (GPT-4) solves APPS problems and may insert backdoors. A trusted model (GPT-3.5) monitors, and humans audit the most suspicious outputs on a small budget. Protocols are compared by safety against usefulness. | Our whole framing: trusted monitoring, audit budget, safety-vs-usefulness curves (also ARENA 3.5) | ✅ |
| [Bhatt et al. (2025). *Ctrl-Z: Controlling AI Agents via Resampling*](https://arxiv.org/abs/2504.10374) | Control for **multi-step agents** in bash (BashBench, 257 tasks). Resampling suspicious actions cut attack success from 58% to 7% at a 5% usefulness cost. | Multi-step agent control; resampling as a protocol to adapt to waits | ✅ |
| [UK AISI. *ControlArena*](https://control-arena.aisi.org.uk/settings/) | Open library of 15 control settings on Inspect, all software. Labels each setting's "harmful effect timing" (Sync or Async). | Shows no existing setting models a process that changes on its own. Possible home for LabWorld as a setting. | ✅ |
| [Anthropic (2025). *SHADE-Arena: Evaluating Sabotage and Monitoring in LLM Agents*](https://arxiv.org/abs/2506.15740) | Agents do a main task plus a hidden sabotage side task. A monitor reads the transcript. The strongest models evaded detection ~60% of the time. Sabotage relied heavily on a hidden scratchpad. | Template for honest vs attack mode, and for monitors that do or don't see reasoning | ◐ |
| [Redwood (2026). *LinuxArena*](https://icml.cc/virtual/2026/67807) (ICML 2026) | Control setting in live production software | The setting Kemeklis & Vemuri used for omission attacks | ◐ |
| [Arike et al. (2026). *How does information access affect LLM monitors' ability to detect sabotage?*](https://arxiv.org/abs/2601.21112) | Monitors often do better with **less** information | Motivates testing what our supervisors see (decision D6) | ◐ |
| [Redwood (2026). *Simulated Control Evaluations*](https://arxiv.org/abs/2610.31593) | Uses environment simulation to run control evaluations closer to deployment | Supports using a simulated world (LabWorld) for control evaluations | ◐ |

### Automated red teaming
| Work | What it did | How we use it | Status |
|---|---|---|---|
| [Perez et al. (2022). *Red Teaming Language Models with Language Models*](https://arxiv.org/abs/2202.03286) | LMs (including RL-trained ones) generate attacks that find failures automatically | Inspiration for the **RL attacker**: attacks found by optimisation, not hand-written | ✅ |

### Robots and physical-AI safety
| Work | What it did | How we use it | Status |
|---|---|---|---|
| [*RoboHarm: Refuses in Chat, Complies with Arms*](https://arxiv.org/abs/2610.14043) (Robocurve, 2026) | Same models refuse harmful requests in chat (73–84%) but comply when acting through robot interfaces (refusal 18–25%) | Safety behaviour changes when models act physically, which motivates physical-agent evaluations | ◐ |
| [Grover (2026)](https://arxiv.org/abs/2610.27350): SO-101 arm with Inspect Robots | GPT-6 Astra controlling a real arm: 0/15 refusals when acting, 15/15 when asked in text | Shows a single person can produce a citable physical-AI safety result | ◐ |
| ASIMOV (Google DeepMind, CoRL 2025); SafeAgentBench; IS-Bench | Semantic and household safety benchmarks for embodied agents. Delayed hazards appear, but with **no adversary and no monitor**. | We add the adversary and the monitor | ◐ |
| PAISI, *The Case for Physical AI Safety* (white paper, Jul 2026) | Lists runtime monitoring and sim-to-real safety as open directions | Positions this project in the physical-AI safety agenda | ◐ |

### Honesty after the fact
| Work | What it did | How we use it | Status |
|---|---|---|---|
| [*Deception by Omission: Language Models Knowingly Hide Their Mistakes*](https://arxiv.org/abs/2610.11351) (2026) | Agents conceal planted mistakes in their reports (up to 19.9% for some models) | Our saboteurs' end-of-night reports blamed "unexpected" events: a related behaviour | ◐ |

### Tools
[Inspect](https://inspect.aisi.org.uk/) (UK AISI), the eval framework for the LLM robots and monitors. [Gymnasium](https://gymnasium.farama.org/), the RL environment interface (`LabWorld-v0`).

---

## 2. What others have already done on omission attacks
**The core idea, that action monitors miss omission, is not new.**

| Work | Setting | How the omissions were made | Key result | Status |
|---|---|---|---|---|
| [Kemeklis & Vemuri (Mar 2026). *Omission Attacks: When Doing Nothing Is the Attack*](https://apartresearch.com/sprints/projects/omission-attacks-when-doing-nothing-is-the-attack-0y1v) (Apart AI Control Hackathon, 1st place) | LinuxArena (software) | **5 hand-crafted** traces | Strongest monitor (Opus 4.6) scored omissions **≤ 4/10**, against **92.3/100** for normal attacks. An **end-of-run postcondition monitor** caught all 5. They note that when damage happens immediately, it may be done before an end-of-run monitor runs. | ✅ |
| [Najt, Toft, Tracy, Roger, Benton (May 2026). *SLEIGHT-Bench*](https://arxiv.org/abs/2605.16626) (Anthropic Fellows, Redwood) | Synthetic coding transcripts | **Human-designed**, written up with AI help | Opus 4.6 monitor caught **0/10** omission attacks at a 1% false-positive rate | ✅ |
| [Ganesan, Chandrasekharan, Palanisamy (Mar 2026). *OmissionControl*](https://apartresearch.com/sprints/projects/omissioncontrol-a-controlarena-setting-for-selective-omission-attacks-in-multiagent-pipelines-1gvm) | Multi-agent software pipelines (OAuth, DB migration) | Attack-mode agent leaves out requirements | Only monitors with the original spec helped (up to 89% reduction) | ✅ |
| [Talasila et al. (2026). *The AI Sedition Acts*](https://openreview.net/forum?id=bIBZ3Bt65n) (NeurIPS 2026 AI4GOOD workshop) | Military briefing pipeline (summaries) | **Instructed** saboteurs leave out relationships | 22/30 missed notifications. Monitor caught 38/40 at ~5 flags per catch. Includes a **fatigue-degraded honest** condition. | ✅ |
| [*ASMR-Bench: Auditing for Sabotage in ML Research*](https://arxiv.org/abs/2604.16286) (2026) | ML research codebases | – | Calls omission "the most effective strategy" for research sabotage | ◐ |

**What all of these have in common:** the omission is **something missing from an artifact** (code, a regex, a document, a summary). The environment doesn't change while the agent waits, and the harm can be found by **checking the end result**.

---

## 3. The gap this project fills

| Dimension | Prior work | This project |
|---|---|---|
| What the omission is | Missing content in an artifact | **A missing action in time**: no refill, hood never on, heater left on |
| Does the world change while the agent waits? | No | **Yes**: coolant leaks, temperature drifts, pressure follows |
| When harm becomes irreversible | At or after the end of the run; caught by an end-of-run check | **Mid-run**: the runaway happens before the end, so an end-of-run check is too late |
| What a useful monitor must do | Check the final state (postcondition) or compare against a spec | **Forecast** ("what happens if this continues?"), and warn **before** the point of no return |
| Measure | Detection (AUROC, catch rate) | Detection **and lead time** (ticks of warning before harm) |
| Where attacks come from | Hand-written (Kemeklis, SLEIGHT) or explicitly instructed (Talasila) | **LLM saboteurs choosing omission unprompted** (our pilot) and an **RL attacker** |
| Domain | Software, documents | **Physical-process control** (a lab or plant), the setting of physical-AI deployment |

**Claim we can defend:** *Omission attacks are known to evade action monitors in software settings, where an end-of-run check can catch them. We test the case those checks can't handle: agents controlling physical processes, where omission harm builds over time and becomes irreversible before the run ends. There, monitors must forecast, and warning time is what matters.*

---

## 4. What's worth researching, and what each extends

Marked by fit for the TARA timeline: **core** (in the plan), **stretch** (if time allows), **future** (after TARA).

| # | Research question | Extends | Why it's worth doing | Fit |
|---|---|---|---|---|
| 1 | **Temporal omission:** in a world that keeps changing, how do action monitors, end-of-run postcondition checks, a rule-based safety switch and a **forecasting (consequence) monitor** compare, on both detection and **lead time**? | Kemeklis & Vemuri (their postcondition fix; their stated limitation), Ctrl-Z | The central gap. Tests whether the known fix fails when harm is time-dependent. | **Core** |
| 2 | **Do LLM saboteurs choose omission unprompted?** How often, across models and prompts? | Kemeklis & Vemuri (lists live LLM agents as future work), SHADE-Arena | Our pilot says yes (Sonnet 5, nodecode-cyber-v1, Hermes). A larger sample would show whether omission is the **default** evasion strategy. | **Core** (small), with more seeds as stretch |
| 3 | **RL-discovered attacks:** does an attacker optimised against action monitors converge on omission? | Perez et al. 2022 (automated red teaming), control evaluations | Removes the "you wrote the attacks yourself" circularity, and shows the weakness is found by optimisation | **Stretch** |
| 4 | **Sabotage vs negligence:** can any monitor tell a saboteur from a lazy robot when both skip the same chore? | Talasila et al. (fatigue-degraded honest condition) | If not, audit policy must treat negligent omission as a safety incident, which matters for deployment rules | **Core** (lazy robot already built) |
| 5 | **Information access for omission monitors:** with or without the rule manual, and how often snapshots arrive | OmissionControl (spec access was decisive), Arike et al. 2026 | Tells deployers what a monitor of a physical process needs to see | **Stretch** |
| 6 | **Reasoning visibility:** does seeing the agent's reasoning catch omission saboteurs? | SHADE-Arena (hidden scratchpad), ARENA 4.3 | Sonnet 5 leaked its intent in its text and nodecode-cyber-v1 didn't, so the answer may depend on the model | **Stretch** |
| 7 | **Protocols for waiting:** defer-to-trusted on `wait`, resampling, forced check-ins, an audit budget weighted toward irreversible states | Ctrl-Z (resampling), Greenblatt et al. (defer-to-trusted) | Turns a detection result into a defence | **Stretch** |
| 8 | **Cover-up after omission:** do saboteurs' reports hide or reframe the harm? | Deception by Omission (2026) | Our saboteurs blamed "unexpected" events. Honest incident reporting is part of oversight. | **Future** (data already logged) |
| 9 | **Sim-to-real:** does omission behaviour carry over to a real robot? | RoboHarm, Grover (SO-101 with Inspect Robots) | The bridge from simulation to a physical deployment | **Future** |

**Recommended focus for TARA:** questions **1 + 2 + 4** form one coherent result, with **3** as the standout extra if week 2 allows.
