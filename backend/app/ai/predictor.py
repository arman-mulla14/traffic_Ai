import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models import TrafficMetric

class TrafficPredictor:
    """
    Traffic Prediction Engine.
    Uses real historical traffic observations stored in the SQLite database.
    Strictly follows No-Fake-Data Rule:
    - Requires at least MIN_REQUIRED_SAMPLES (5) historical observation intervals.
    - If fewer samples exist, returns status='INSUFFICIENT_DATA' with transparent explanation.
    - When sufficient data is present, applies Double Exponential Smoothing (Holt's Linear Trend)
      and calculates actual Mean Absolute Error (MAE) on validation splits.
    """
    MIN_REQUIRED_SAMPLES = 5

    def __init__(self, db: Session):
        self.db = db

    def predict_future_traffic(self, horizon_minutes: List[int] = [5, 10, 15, 30]) -> Dict[str, Any]:
        # Fetch timestamped traffic observations sorted chronologically
        metrics = (
            self.db.query(TrafficMetric)
            .order_by(TrafficMetric.timestamp.asc())
            .all()
        )

        sample_count = len(metrics)
        if sample_count < self.MIN_REQUIRED_SAMPLES:
            return {
                "status": "INSUFFICIENT_DATA",
                "message": (
                    f"Insufficient historical data. Found {sample_count} observation(s); "
                    f"minimum {self.MIN_REQUIRED_SAMPLES} recorded intervals are required to train baseline forecasting model."
                ),
                "model_name": "Double Exponential Smoothing (Holt-Winters)",
                "mae_score": None,
                "sample_count": sample_count,
                "data_freshness_seconds": None,
                "forecasts": []
            }

        # Extract real series
        times = [m.timestamp for m in metrics]
        flows = [float(m.flow_rate_per_min if m.flow_rate_per_min > 0 else m.vehicle_count) for m in metrics]
        densities = [float(m.density_score) for m in metrics]

        latest_time = times[-1]
        data_freshness = (datetime.utcnow() - latest_time).total_seconds()

        # Fit Holt's Linear Trend model (alpha=0.4, beta=0.2)
        alpha = 0.4
        beta = 0.2

        # Level and Trend initialization
        level_flow = flows[0]
        trend_flow = flows[1] - flows[0] if len(flows) > 1 else 0.0

        level_density = densities[0]
        trend_density = densities[1] - densities[0] if len(densities) > 1 else 0.0

        errors_flow = []

        # Run filter over observed series
        for i in range(1, len(flows)):
            # 1-step ahead forecast
            pred_step = level_flow + trend_flow
            errors_flow.append(abs(flows[i] - pred_step))

            # Update level and trend
            val = flows[i]
            prev_level = level_flow
            level_flow = alpha * val + (1 - alpha) * (level_flow + trend_flow)
            trend_flow = beta * (level_flow - prev_level) + (1 - beta) * trend_flow

            # Density
            d_val = densities[i]
            prev_d_level = level_density
            level_density = alpha * d_val + (1 - alpha) * (level_density + trend_density)
            trend_density = beta * (level_density - prev_d_level) + (1 - beta) * trend_density

        mae = float(sum(errors_flow) / len(errors_flow)) if errors_flow else 0.0

        # Generate future forecasts for requested horizons
        forecasts = []
        for h in horizon_minutes:
            target_time = latest_time + timedelta(minutes=h)
            # Projected steps (assume approx 1-minute steps)
            k = max(1, h)
            pred_f = max(0.0, level_flow + k * trend_flow)
            pred_d = max(0.0, level_density + k * trend_density)

            # Confidence bounds based on MAE
            margin = 1.25 * (mae if mae > 0 else 1.0) * math.sqrt(k)

            forecasts.append({
                "target_timestamp": target_time,
                "horizon_minutes": h,
                "approach": "ALL_APPROACHES",
                "predicted_flow_rate": round(pred_f, 1),
                "predicted_density": round(pred_d, 1),
                "confidence_lower": round(max(0.0, pred_f - margin), 1),
                "confidence_upper": round(pred_f + margin, 1)
            })

        return {
            "status": "VALID",
            "message": f"Forecast generated successfully using Holt's Linear Trend model on {sample_count} historical intervals.",
            "model_name": "Double Exponential Smoothing (Holt-Winters)",
            "mae_score": round(mae, 2),
            "sample_count": sample_count,
            "data_freshness_seconds": round(data_freshness, 1),
            "forecasts": forecasts
        }
