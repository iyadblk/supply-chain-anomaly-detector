"""Per-domain training pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

import numpy as np
import pandas as pd

from core.ensemble import AnomalyEnsemble
from core.explainer import Explainer

DOMAIN_FEATURES: Dict[str, List[str]] = {
    "operators": [
        "picks_per_hour", "error_rate", "distance_m", "stock_accuracy",
        "orders_completed", "zone", "shift", "day_of_week",
    ],
    "inventory": [
        "units_sold", "stock_level", "days_since_last_delivery",
        "demand_vs_forecast_ratio", "stock_vs_safety_ratio", "zone",
    ],
    "routes": [
        "total_distance_m", "total_time_min", "aisles_visited", "door_crossings",
        "picks_per_km", "cold_exposure_sec", "algorithm_used", "sku_count", "zone_spread",
    ],
    "deliveries": [
        "delay_days", "quantity_ordered", "quantity_received", "shortfall_pct",
        "damage_rate", "zone", "supplier_late_streak",
    ],
}


@dataclass
class TrainedDomain:
    name: str
    ensemble: AnomalyEnsemble
    explainer: Explainer
    features: List[str]
    n_records: int
    trained_at: str
    metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)


def _feature_matrix(df: pd.DataFrame, features: List[str]) -> np.ndarray:
    return df[features].astype(float).to_numpy()


def train_domain(domain: str, df: pd.DataFrame) -> TrainedDomain:
    features = DOMAIN_FEATURES[domain]
    X = _feature_matrix(df, features)
    ens = AnomalyEnsemble().fit(X, features)
    explainer = Explainer(domain=domain, baseline=df, features=features)
    metrics: Dict[str, Dict[str, float]] = {}
    if "true_anomaly" in df.columns:
        metrics = ens.metrics_vs_truth(X, df["true_anomaly"].astype(int).to_numpy())
    return TrainedDomain(
        name=domain,
        ensemble=ens,
        explainer=explainer,
        features=features,
        n_records=len(df),
        trained_at=datetime.now().isoformat(timespec="seconds"),
        metrics=metrics,
    )
