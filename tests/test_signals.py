import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.signal_optimizer import SignalOptimizer

def test_signal_optimizer_bounds_and_constraints():
    optimizer = SignalOptimizer(
        min_green=10,
        max_green=60,
        yellow_clearance=4,
        all_red=2,
        default_cycle=120
    )

    # Heavily asymmetric traffic: East has huge queue, West is almost empty
    counts = {
        "NORTH": 15,
        "SOUTH": 15,
        "EAST": 80,
        "WEST": 2
    }

    plan = optimizer.optimize_intersection(counts, cycle_time=120, min_green=10, max_green=60)

    # 1. Minimum green constraint: West MUST have at least min_green (10s) despite only 2 vehicles
    assert plan["approach_w_green"] >= 10

    # 2. Maximum green constraint: East MUST NOT exceed max_green (60s)
    assert plan["approach_e_green"] <= 60

    # 3. Dynamic responsiveness: East MUST receive more green than West, North, or South
    assert plan["approach_e_green"] > plan["approach_w_green"]
    assert plan["approach_e_green"] > plan["approach_n_green"]

    # 4. Mandatory safety simulation flag
    assert plan["is_simulation"] is True

    # 5. Explanatory reasoning is present
    assert "Webster/Equal-Saturation Optimization" in plan["reasoning"]
    assert "EAST approach" in plan["reasoning"]
