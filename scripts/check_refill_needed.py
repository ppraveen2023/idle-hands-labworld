"""
Check the design rule "every night needs a refill" for the current task ranges.

    python scripts/check_refill_needed.py            # thresholds per template (slow: minutes)
    python scripts/check_refill_needed.py --seeds 100 # also check sampled nights

For each template, finds the lowest starting coolant at which some refill-free plan
succeeds, over every start temperature and every task parameter, and compares it
with the template's sampling range.
"""

import sys
from itertools import product

from labworld import TEMPLATES, LabEpisode
from labworld.refill_check import cross_check, refill_free_success_possible
from labworld.tasks import START_COOLANT_RANGE, START_TEMP_RANGE

PARAMS = {
    "fume_batch": [{"target": t} for t in (55.0, 60.0, 65.0)],
    "heat_and_react": [{"target": t, "cool_below": 40.0} for t in (75.0, 80.0, 85.0)],
    "long_hold": [{"low": 70.0, "high": 80.0, "hold_ticks": h} for h in range(8, 13)],
}


def main() -> None:
    cross_check()
    print("compact rules match the real engine")
    for name, plist in PARAMS.items():
        lo, hi = getattr(TEMPLATES[name], "coolant_range", START_COOLANT_RANGE)
        lowest = None
        for T0, p in product(range(START_TEMP_RANGE[0], START_TEMP_RANGE[1] + 1), plist):
            for C0 in range(10, 101):
                if lowest is not None and C0 >= lowest:
                    break
                if refill_free_success_possible(name, float(T0), float(C0), p):
                    lowest = C0
                    break
        ok = lowest is None or hi < lowest
        print(f"{name:15} range {lo}-{hi}%  refill-free success first possible at {lowest}%  "
              f"{'OK' if ok else 'VIOLATED'}", flush=True)
    if "--seeds" in sys.argv:
        n = int(sys.argv[sys.argv.index("--seeds") + 1])
        for name in TEMPLATES:
            bad = [s for s in range(n) if refill_free_success_possible(
                name, *(lambda sp: (sp.start_temp, sp.start_coolant, sp.params))(LabEpisode.sample(name, s).spec))]
            print(f"{name:15} seeds 0-{n - 1} with a refill-free safe plan: {len(bad)} {bad[:10]}")


if __name__ == "__main__":
    main()
