"""Design rule: every night needs a refill, so skipping it is a genuine omission.

The full threshold search for every template takes minutes (scripts/check_refill_needed.py).
These tests run the fast parts on every change.
"""

from labworld import TEMPLATES, LabEpisode
from labworld.refill_check import cross_check, refill_free_success_possible
from labworld.tasks import REFILL_FREE_THRESHOLD, START_COOLANT_RANGE


def test_compact_rules_match_the_engine():
    cross_check(trials=500)


def test_sampling_ranges_stay_below_the_refill_free_thresholds():
    for name in TEMPLATES:
        lo, hi = getattr(TEMPLATES[name], "coolant_range", START_COOLANT_RANGE)
        assert hi < REFILL_FREE_THRESHOLD[name], (name, hi)


def test_fume_batch_top_of_range_needs_a_refill_but_threshold_does_not():
    """Exhaustive check at the edges for the fastest template: the warmest start and lowest target."""
    params = {"target": 55.0}
    hi = TEMPLATES["fume_batch"].coolant_range[1]
    assert not refill_free_success_possible("fume_batch", 30.0, float(hi), params)
    assert refill_free_success_possible("fume_batch", 30.0, float(REFILL_FREE_THRESHOLD["fume_batch"]), params)


def test_sampled_fume_batch_nights_all_need_a_refill():
    for seed in range(30):
        sp = LabEpisode.sample("fume_batch", seed).spec
        assert not refill_free_success_possible("fume_batch", sp.start_temp, sp.start_coolant, sp.params), seed
