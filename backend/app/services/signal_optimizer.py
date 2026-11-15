from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.core.config import settings

class SignalOptimizer:
    """
    Intersection Traffic-Signal Timing Optimizer using Webster's Formula / Equal Saturation.
    Simulates a 4-way intersection (North, South, East, West).
    Calculates recommended green times constrained by safety clearance and min/max bounds.
    """
    def __init__(
        self,
        min_green: int = settings.MIN_GREEN_SECONDS,
        max_green: int = settings.MAX_GREEN_SECONDS,
        yellow_clearance: int = settings.YELLOW_CLEARANCE_SECONDS,
        all_red: int = settings.ALL_RED_CLEARANCE_SECONDS,
        default_cycle: int = settings.DEFAULT_CYCLE_SECONDS
    ):
        self.min_green = min_green
        self.max_green = max_green
        self.yellow_clearance = yellow_clearance
        self.all_red = all_red
        self.phase_lost_time = yellow_clearance + all_red  # Total clearance lost time per phase
        self.default_cycle = default_cycle

    def optimize_intersection(
        self,
        approach_counts: Dict[str, int],
        cycle_time: Optional[int] = None,
        min_green: Optional[int] = None,
        max_green: Optional[int] = None,
        intersection_name: str = "Intersection Alpha"
    ) -> Dict[str, Any]:
        """
        approach_counts: e.g. {"NORTH": 18, "SOUTH": 12, "EAST": 28, "WEST": 6}
        """
        cycle = cycle_time or self.default_cycle
        min_g = min_green or self.min_green
        max_g = max_green or self.max_green

        approaches = ["NORTH", "SOUTH", "EAST", "WEST"]
        # Standardize keys
        counts = {app: max(1, approach_counts.get(app, 10)) for app in approaches}
        total_vehicles = sum(counts.values())

        # Total lost time across 4 phases: 4 phases * clearance
        # Often modeled as 2 paired phases (N-S together, E-W together) or 4 sequential phases.
        # Let's model 4 sequential dedicated phases for maximum granularity and safety:
        total_lost_time = len(approaches) * self.phase_lost_time
        available_green_time = max(len(approaches) * min_g, cycle - total_lost_time)

        # Baseline: Uniform equal distribution
        equal_green = int(available_green_time / len(approaches))
        baselines = {app: equal_green for app in approaches}

        # Dynamic allocation proportional to actual observed arrival density:
        # Green_i = available_green * (q_i / sum(q))
        allocated_green = {}
        for app in approaches:
            prop = counts[app] / total_vehicles
            raw_g = round(available_green_time * prop)
            bounded_g = max(min_g, min(max_g, raw_g))
            allocated_green[app] = bounded_g

        # Adjust total sum to match available_green_time without violating bounds
        current_sum = sum(allocated_green.values())
        diff = available_green_time - current_sum

        if diff != 0:
            # Distribute residual seconds to highest volume approach without exceeding max_green
            sorted_by_vol = sorted(approaches, key=lambda a: counts[a], reverse=True)
            for app in sorted_by_vol:
                if diff == 0:
                    break
                if diff > 0 and allocated_green[app] < max_g:
                    allocated_green[app] += 1
                    diff -= 1
                elif diff < 0 and allocated_green[app] > min_g:
                    allocated_green[app] -= 1
                    diff += 1

        # Formulate detailed engineering reasoning
        reasons = []
        for app in approaches:
            c = counts[app]
            g = allocated_green[app]
            base = baselines[app]
            delta = g - base
            if delta > 0:
                reasons.append(
                    f"{app} approach observed high volume ({c} vehicles, {c/total_vehicles:.1%}): "
                    f"allocated +{delta}s green time (total {g}s) to discharge queue."
                )
            elif delta < 0:
                reasons.append(
                    f"{app} approach observed lighter volume ({c} vehicles, {c/total_vehicles:.1%}): "
                    f"reallocated {abs(delta)}s to busier approaches while keeping safety minimum of {g}s."
                )
            else:
                reasons.append(
                    f"{app} approach observed balanced volume ({c} vehicles): maintained {g}s green."
                )

        full_reasoning = (
            f"Webster/Equal-Saturation Optimization: Total intersection volume = {total_vehicles} vehicles across 4 approaches. "
            f"Cycle = {cycle}s (Total lost clearance time = {total_lost_time}s across 4 phases). "
            f"Net available green budget = {available_green_time}s. "
            + " | ".join(reasons)
        )

        return {
            "intersection_name": intersection_name,
            "timestamp": datetime.now(timezone.utc),
            "approach_n_green": allocated_green["NORTH"],
            "approach_s_green": allocated_green["SOUTH"],
            "approach_e_green": allocated_green["EAST"],
            "approach_w_green": allocated_green["WEST"],
            "baseline_n_green": baselines["NORTH"],
            "baseline_s_green": baselines["SOUTH"],
            "baseline_e_green": baselines["EAST"],
            "baseline_w_green": baselines["WEST"],
            "cycle_duration": cycle,
            "clearance_interval": self.phase_lost_time,
            "reasoning": full_reasoning,
            "is_simulation": True  # Explicit safety flag
        }
