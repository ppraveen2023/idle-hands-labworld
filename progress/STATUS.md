# Status

*Updated 24 Nov 2026 (Tue)*

**Project:** *Idle Hands*: do AI control monitors catch an agent that causes harm by doing nothing, in a world that keeps changing on its own?

**Overall:** ahead of the 28 Nov milestone. The world and the robot side are built and tested. The supervisors are next.

## Milestones
| Date | Milestone | State |
|---|---|---|
| Sat 28 Nov | LabWorld + RL interface + Inspect task with an honest robot; supervisors frozen; predictions written | 🟡 Mostly done: supervisors and predictions remain |
| Wed 2 Dec | Full robot runs: 30 honest, 30 lazy, 30 saboteur nights per saboteur model | ⚪ Not started |
| Sat 5 Dec | Supervisors scored on frozen logs; first AUROC by attack type | ⚪ Not started |
| Wed 9 Dec | RL attacker (if kept); final figures | ⚪ Not started (RL interface ready) |
| Thu 10 Dec | One-page report uploaded (prize deadline) | ⚪ |
| Fri 11 Dec | Slides, public repo, rehearsal | ⚪ |
| Sat 12 Dec | Presentation | ⚪ |

## Done
- [x] LabWorld engine: 7 rules, 3 hazards, 3 task templates, varied starts
- [x] Gymnasium RL environment `LabWorld-v0`
- [x] Inspect task: 8 tools, night saved in the store, referee scorer
- [x] Scripted reference robots: honest, lazy, omission and commission saboteurs
- [x] Tests passing (63 as of 25 Nov); git repo (3 commits, latest `3b40f30`), pushed to a **private** GitHub repo: https://github.com/ppraveen2023/idle-hands-labworld
- [x] Pilot sweep: 14 Claude models, 3 uncensored models, nodecode-cyber-v1
- [x] Prior-work check and corrected novelty claim (`RELATED_WORK.md`)
- [x] Project proposal and mentor brief in Google Drive
- [x] Full report in `TARA_PROJECT/report/` (one-pager, LabWorld spec, tools and validation plan); 2 bugs fixed
- [x] Starting coolant tightened so no possible plan can skip the refill (exhaustive search); 63 tests passing
- [x] Per-experiment PDFs for the mentor in `TARA_PROJECT/experiments/` (overview + Experiments 1–3)

## Next (in order)
1. [ ] **Hear back from the mentor** on the 5 questions in the brief
2. [ ] **Lock the robot models** (decision D7): honest and lazy on Claude Haiku 5.5 or Sonnet 5.5; saboteur on Sonnet 5 and nodecode-cyber-v1
3. [ ] **Lock the robot prompts** (decision D8)
4. [ ] **Build the supervisors** as Inspect scorers:
   - rule-based safety switch
   - end-of-run postcondition check (Kemeklis & Vemuri baseline)
   - action monitor
   - consequence (forecasting) monitor
5. [ ] **Freeze the supervisor prompts and write down predictions**, before any full saboteur run
6. [ ] **Add the lead-time metric** (ticks of warning before the point of no return) and AUROC metrics

## Open questions and blockers
- Waiting on mentor feedback: saboteur model choice, what supervisors see, framing, sample size, whether to keep the RL attacker
