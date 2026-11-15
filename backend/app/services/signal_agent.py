"""
Autonomous 4-Way Traffic Signal Control Agent.
Performs real-time multi-camera traffic assessment across a 4-square road intersection:
- Approach 1: North (Camera 1)
- Approach 2: East  (Camera 2)
- Approach 3: South (Camera 3)
- Approach 4: West  (Camera 4)

Dynamically computes Webster-optimal green signal timings based on measured queue volume
and auto-updates phase signals (GREEN, YELLOW, RED) in real time.
"""

import time
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.database.models import Camera, Video, SignalPlan, TrafficRecord
from app.services.signal_optimizer import SignalOptimizer
from app.config import settings

class TrafficSignalAgent:
    _instance: Optional["TrafficSignalAgent"] = None

    APPROACH_ORDER = ["NORTH", "EAST", "SOUTH", "WEST"]
    APPROACH_CAMERA_MAP = {
        "NORTH": 1,
        "EAST": 2,
        "SOUTH": 3,
        "WEST": 4,
    }

    def __init__(self):
        self.is_adaptive_agent_running: bool = True
        self.cycle_seconds: int = 120
        self.min_green: int = 15
        self.max_green: int = 60
        self.yellow_seconds: int = 4

        # Initial signal phase
        self.current_approach_index: int = 0
        self.phase_state: str = "GREEN"  # "GREEN", "YELLOW"
        self.active_approach: str = "NORTH"

        # Allocations (seconds)
        self.allocated_green: Dict[str, int] = {
            "NORTH": 38,
            "EAST": 26,
            "SOUTH": 34,
            "WEST": 22,
        }

        self.phase_remaining_seconds: float = float(self.allocated_green["NORTH"])
        self.last_tick_time: float = time.time()
        self.last_optimized_at: Optional[datetime] = None
        self.current_reasoning: str = "Autonomous Agent initialized: Webster equal-saturation allocation active."
        self.emergency_override: Optional[str] = None
        self.total_cycles_completed: int = 0

    @classmethod
    def get_instance(cls) -> "TrafficSignalAgent":
        if cls._instance is None:
            cls._instance = TrafficSignalAgent()
        return cls._instance

    def _sample_approach_telemetry(self, db: Session) -> Dict[str, Dict[str, Any]]:
        """
        Samples actual live metrics or recent traffic records for the 4 camera approaches.
        """
        telemetry = {}
        for app in self.APPROACH_ORDER:
            cam_id = self.APPROACH_CAMERA_MAP[app]
            cam = db.query(Camera).filter(Camera.id == cam_id).first()

            # 1. Directly sample real-time YOLOv8 detection metrics from active streams
            live_t = None
            try:
                from app.routes.videos import CAMERA_TELEMETRY
                live_t = CAMERA_TELEMETRY.get(cam_id)
            except Exception:
                pass

            if live_t and (live_t.get("vehicles_in_frame") is not None):
                veh_count = live_t.get("vehicles_in_frame", 0)
                density = live_t.get("density", 15.0)
                queue = live_t.get("queue_length", max(1, int(veh_count * 0.35)))
            else:
                # Query recent traffic record for this camera if available
                recent_rec = db.query(TrafficRecord).filter(TrafficRecord.analysis_id == cam_id).order_by(TrafficRecord.timestamp.desc()).first()
                if not recent_rec:
                    recent_rec = db.query(TrafficRecord).order_by(TrafficRecord.timestamp.desc()).first()

                # Sensible defaults based on camera id / time
                default_v = 16 if app == "NORTH" else (10 if app == "EAST" else (14 if app == "SOUTH" else 8))
                veh_count = recent_rec.total_vehicles if (recent_rec and recent_rec.total_vehicles > 0) else default_v
                density = round(recent_rec.traffic_density if recent_rec else (veh_count * 3.5), 1)
                queue = recent_rec.queue_length if (recent_rec and recent_rec.queue_length) else max(1, int(veh_count * 0.35))

            telemetry[app] = {
                "approach": app,
                "camera_id": cam_id,
                "camera_name": cam.camera_name if cam else f"Camera #{cam_id}",
                "location": cam.location if cam else f"{app.capitalize()} Approach",
                "stream_url": f"/api/cameras/{cam_id}/stream",
                "vehicles": veh_count,
                "density": min(98.5, max(5.0, density)),
                "queue_length": queue,
            }
        return telemetry

    def recompute_allocations(self, db: Session, telemetry: Dict[str, Dict[str, Any]]):
        """
        Applies Webster's formula to optimize green times based on live sampled counts.
        """
        approach_counts = {app: telemetry[app]["vehicles"] for app in self.APPROACH_ORDER}
        optimizer = SignalOptimizer(
            min_green=self.min_green,
            max_green=self.max_green,
            yellow_clearance=self.yellow_seconds,
            default_cycle=self.cycle_seconds
        )

        res = optimizer.optimize_intersection(
            approach_counts=approach_counts,
            cycle_time=self.cycle_seconds,
            min_green=self.min_green,
            max_green=self.max_green,
            intersection_name="4-Way Smart Junction"
        )

        self.allocated_green["NORTH"] = res["approach_n_green"]
        self.allocated_green["SOUTH"] = res["approach_s_green"]
        self.allocated_green["EAST"] = res["approach_e_green"]
        self.allocated_green["WEST"] = res["approach_w_green"]
        self.current_reasoning = res["reasoning"]
        self.last_optimized_at = datetime.now(timezone.utc)

        # Persist plan to SQLite
        try:
            plan = SignalPlan(
                intersection_name="4-Way Smart Junction",
                timestamp=datetime.now(timezone.utc),
                approach_n_green=res["approach_n_green"],
                approach_s_green=res["approach_s_green"],
                approach_e_green=res["approach_e_green"],
                approach_w_green=res["approach_w_green"],
                baseline_n_green=res["baseline_n_green"],
                baseline_s_green=res["baseline_s_green"],
                baseline_e_green=res["baseline_e_green"],
                baseline_w_green=res["baseline_w_green"],
                cycle_duration=self.cycle_seconds,
                clearance_interval=self.yellow_seconds,
                reasoning=res["reasoning"],
                is_simulation=True
            )
            db.add(plan)
            db.commit()
        except Exception:
            db.rollback()

    def tick(self, db: Session) -> None:
        """
        Advances the signal controller clock and handles transitions.
        """
        now = time.time()
        elapsed = now - self.last_tick_time
        self.last_tick_time = now

        # In emergency override mode, hold green indefinitely on target
        if self.emergency_override:
            self.active_approach = self.emergency_override
            self.phase_state = "GREEN"
            self.phase_remaining_seconds = 99
            return

        self.phase_remaining_seconds -= elapsed

        # Yellow clearance interval before switching phase
        if self.phase_state == "GREEN" and self.phase_remaining_seconds <= self.yellow_seconds:
            self.phase_state = "YELLOW"

        # Phase expired -> advance to next approach
        if self.phase_remaining_seconds <= 0:
            telemetry = self._sample_approach_telemetry(db)

            # Move to next approach in round-robin order
            self.current_approach_index = (self.current_approach_index + 1) % len(self.APPROACH_ORDER)
            self.active_approach = self.APPROACH_ORDER[self.current_approach_index]
            self.phase_state = "GREEN"

            # If completing full cycle, re-evaluate adaptive green allocations
            if self.current_approach_index == 0:
                self.total_cycles_completed += 1
                if self.is_adaptive_agent_running:
                    self.recompute_allocations(db, telemetry)

            self.phase_remaining_seconds = float(self.allocated_green[self.active_approach])

    def get_status(self, db: Session) -> Dict[str, Any]:
        """
        Returns full real-time status of the 4-way intersection and all signals.
        """
        self.tick(db)
        telemetry = self._sample_approach_telemetry(db)

        # Build signal lamp statuses for each approach
        signals = {}
        for app in self.APPROACH_ORDER:
            is_active = (app == self.active_approach)
            if is_active:
                lamp = self.phase_state  # "GREEN" or "YELLOW"
                countdown = max(1, int(round(self.phase_remaining_seconds)))
            else:
                lamp = "RED"
                # Estimate countdown until this approach turns green
                steps_away = (self.APPROACH_ORDER.index(app) - self.current_approach_index) % len(self.APPROACH_ORDER)
                est_countdown = int(self.phase_remaining_seconds)
                for step in range(1, steps_away):
                    intermediate_app = self.APPROACH_ORDER[(self.current_approach_index + step) % len(self.APPROACH_ORDER)]
                    est_countdown += self.allocated_green[intermediate_app] + self.yellow_seconds
                countdown = max(1, est_countdown)

            signals[app] = {
                "approach": app,
                "camera_id": self.APPROACH_CAMERA_MAP[app],
                "color": lamp,
                "countdown_seconds": countdown,
                "allocated_green_seconds": self.allocated_green[app],
                "telemetry": telemetry[app]
            }

        return {
            "intersection_name": "4-Way Smart Road Junction (North-East-South-West)",
            "agent_active": self.is_adaptive_agent_running,
            "emergency_override": self.emergency_override,
            "active_approach": self.active_approach,
            "phase_state": self.phase_state,
            "phase_remaining_seconds": max(1, int(round(self.phase_remaining_seconds))),
            "cycle_seconds": self.cycle_seconds,
            "yellow_seconds": self.yellow_seconds,
            "total_cycles_completed": self.total_cycles_completed,
            "reasoning": self.current_reasoning,
            "approaches": signals,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def manual_override(self, approach: Optional[str], duration: Optional[int] = None) -> Dict[str, Any]:
        """Forces a specific approach green, or clears override."""
        if approach and approach.upper() in self.APPROACH_ORDER:
            target = approach.upper()
            self.active_approach = target
            self.current_approach_index = self.APPROACH_ORDER.index(target)
            self.phase_state = "GREEN"
            self.phase_remaining_seconds = float(duration or self.allocated_green[target])
            self.emergency_override = None
            return {"status": "success", "message": f"Phase switched to {target} for {self.phase_remaining_seconds}s"}
        elif approach == "CLEAR":
            self.emergency_override = None
            return {"status": "success", "message": "Manual override cleared. Autonomous agent resumed."}
        else:
            return {"status": "error", "message": f"Invalid approach: {approach}"}

    def toggle_emergency(self, approach: Optional[str]) -> Dict[str, Any]:
        """Toggles emergency vehicle priority green hold."""
        if approach and approach.upper() in self.APPROACH_ORDER:
            self.emergency_override = approach.upper()
            self.active_approach = self.emergency_override
            self.phase_state = "GREEN"
            self.phase_remaining_seconds = 99
            return {"status": "success", "message": f"Emergency Priority GREEN held for {self.emergency_override}."}
        else:
            self.emergency_override = None
            self.phase_remaining_seconds = float(self.allocated_green[self.active_approach])
            return {"status": "success", "message": "Emergency Priority released."}
