from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models import SignalPlan, TrafficMetric
from app.schemas.schemas import SignalOptimizeRequest, SignalPlanResponse
from app.services.signal_optimizer import SignalOptimizer

router = APIRouter(prefix="/api/signals", tags=["Signals"])

@router.post("/optimize", response_model=SignalPlanResponse)
def optimize_signals(req: SignalOptimizeRequest, db: Session = Depends(get_db)):
    # If counts are not manually supplied, pull the latest measured traffic metrics
    latest_metrics = db.query(TrafficMetric).order_by(TrafficMetric.timestamp.desc()).limit(10).all()
    avg_obs = int(sum(m.vehicle_count for m in latest_metrics) / len(latest_metrics)) if latest_metrics else 12

    approach_counts = {
        "NORTH": req.approach_n_count if req.approach_n_count is not None else max(4, avg_obs + 5),
        "SOUTH": req.approach_s_count if req.approach_s_count is not None else max(4, avg_obs - 3),
        "EAST": req.approach_e_count if req.approach_e_count is not None else max(4, avg_obs * 2),
        "WEST": req.approach_w_count if req.approach_w_count is not None else max(4, avg_obs - 5),
    }

    optimizer = SignalOptimizer(
        min_green=req.min_green or 10,
        max_green=req.max_green or 60,
        default_cycle=req.cycle_time or 120
    )

    result = optimizer.optimize_intersection(
        approach_counts=approach_counts,
        cycle_time=req.cycle_time,
        min_green=req.min_green,
        max_green=req.max_green,
        intersection_name=req.intersection_name or "Intersection Alpha"
    )

    # Persist the plan in SQLite
    plan = SignalPlan(
        intersection_name=result["intersection_name"],
        timestamp=result["timestamp"],
        approach_n_green=result["approach_n_green"],
        approach_s_green=result["approach_s_green"],
        approach_e_green=result["approach_e_green"],
        approach_w_green=result["approach_w_green"],
        baseline_n_green=result["baseline_n_green"],
        baseline_s_green=result["baseline_s_green"],
        baseline_e_green=result["baseline_e_green"],
        baseline_w_green=result["baseline_w_green"],
        cycle_duration=result["cycle_duration"],
        clearance_interval=result["clearance_interval"],
        reasoning=result["reasoning"],
        is_simulation=True
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    return plan

@router.get("/history", response_model=List[SignalPlanResponse])
def get_signal_history(db: Session = Depends(get_db)):
    return db.query(SignalPlan).order_by(SignalPlan.timestamp.desc()).limit(15).all()
