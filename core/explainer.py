"""Human-readable anomaly explanations."""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from core.scorer import severity_band


class Explainer:
    """Generates pattern-based hypotheses + standard-deviation context."""

    def __init__(self, domain: str, baseline: pd.DataFrame, features: List[str]):
        self.domain = domain
        self.features = list(features)
        self.mean = baseline[features].mean()
        self.std = baseline[features].std().replace(0, 1e-6)

    # ------------------------------------------------------------------
    def _z(self, row: pd.Series) -> Dict[str, float]:
        return {f: float((row[f] - self.mean[f]) / self.std[f]) for f in self.features}

    def _top_feature(self, row: pd.Series) -> tuple[str, float]:
        z = self._z(row)
        f = max(z, key=lambda k: abs(z[k]))
        return f, z[f]

    # ------------------------------------------------------------------
    def explain(self, row: pd.Series, severity: float) -> Dict[str, str]:
        feat, z = self._top_feature(row)
        cause = self._likely_cause(row)
        entity = self._entity(row)
        band = severity_band(severity)
        value = row[feat]
        mean = self.mean[feat]
        std = self.std[feat]
        text = (
            f"{entity} shows anomalous {feat} of {value:.2f} "
            f"(expected: {mean:.2f} ± {std:.2f}). "
            f"Deviation: {abs(z):.1f} standard deviations from mean. "
            f"Severity: {severity:.0f}/100 ({band}). "
            f"Likely cause: {cause}."
        )
        return {
            "entity": entity,
            "top_feature": feat,
            "z_score": round(float(z), 2),
            "severity_band": band,
            "likely_cause": cause,
            "explanation": text,
        }

    # ------------------------------------------------------------------
    def _entity(self, row: pd.Series) -> str:
        if self.domain == "operators":
            return f"Operator {row.get('operator_name', row.get('operator_id', '?'))}"
        if self.domain == "inventory":
            return f"SKU {row.get('sku', '?')} ({row.get('name', '')})".strip()
        if self.domain == "routes":
            return f"Route {row.get('order_id', '?')} ({row.get('operator_name', '')})".strip()
        if self.domain == "deliveries":
            return f"Delivery {row.get('delivery_id', '?')} from {row.get('supplier', '?')}"
        return "Record"

    # ------------------------------------------------------------------
    def _likely_cause(self, row: pd.Series) -> str:
        d = self.domain
        m, s = self.mean, self.std
        if d == "operators":
            ph = row.get("picks_per_hour", m["picks_per_hour"])
            er = row.get("error_rate", m["error_rate"])
            di = row.get("distance_m", m["distance_m"])
            sa = row.get("stock_accuracy", m["stock_accuracy"])
            if ph < m["picks_per_hour"] - 2 * s["picks_per_hour"] and er > m["error_rate"] + 2 * s["error_rate"]:
                return "Possible fatigue or distraction event"
            if ph < m["picks_per_hour"] - 3 * s["picks_per_hour"] and di > m["distance_m"] + 2 * s["distance_m"]:
                return "Possible navigation issue in warehouse"
            if er > m["error_rate"] + 3 * s["error_rate"]:
                return "Quality spike — supervision recommended"
            if sa < m["stock_accuracy"] - 3 * s["stock_accuracy"]:
                return "Stock-accuracy collapse — recount the zone"
            return "Multi-feature drift from operator baseline"
        if d == "inventory":
            sold = row.get("units_sold", m["units_sold"])
            stock = row.get("stock_level", m["stock_level"])
            ratio = row.get("demand_vs_forecast_ratio", m["demand_vs_forecast_ratio"])
            if stock < m["stock_level"] * 0.30:
                return "Possible inventory miscounting or theft event"
            if sold == 0:
                return "Suspected stockout not flagged by the system"
            if sold > m["units_sold"] + 3 * s["units_sold"] or ratio > 2.5:
                return "Possible unregistered promotional event"
            return "Demand pattern diverges from historical baseline"
        if d == "routes":
            dist = row.get("total_distance_m", m["total_distance_m"])
            cold = row.get("door_crossings", m["door_crossings"])
            ppk = row.get("picks_per_km", m["picks_per_km"])
            tim = row.get("total_time_min", m["total_time_min"])
            if dist > m["total_distance_m"] + 2 * s["total_distance_m"]:
                return "Route 2σ longer than optimal — operator may be lost"
            if cold > m["door_crossings"] + 3 * s["door_crossings"]:
                return "Excessive cold-zone door crossings — pathing error"
            if ppk < m["picks_per_km"] * 0.5:
                return "picks_per_km 50% below average — efficiency drop"
            if tim > m["total_time_min"] + 2 * s["total_time_min"]:
                return "Route duration far above prediction"
            return "Route metrics drift from optimizer baseline"
        if d == "deliveries":
            delay = row.get("delay_days", m["delay_days"])
            dmg = row.get("damage_rate", m["damage_rate"])
            short = row.get("shortfall_pct", m.get("shortfall_pct", 0))
            streak = row.get("supplier_late_streak", 0)
            if delay > 5:
                return "Supplier reliability issue detected"
            if dmg > 5:
                return "Possible handling or transport problem"
            if short > 20:
                return "Quantity received well below order — supplier shortfall"
            if streak >= 3:
                return "Recurring supplier delay pattern"
            return "Delivery metrics drift from supplier baseline"
        return "Multi-feature drift from baseline"
