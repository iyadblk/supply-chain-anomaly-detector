"""Synthetic data generator for all 4 anomaly domains."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
import pandas as pd

from data.catalog import SKUS, SUPPLIERS, ZONES, ZONE_TO_INT
from data.operators import OPERATORS

RNG = np.random.default_rng(42)

ALGORITHMS = ["nearest_neighbor", "or_tools", "genetic", "manual"]
ALGO_TO_INT = {a: i for i, a in enumerate(ALGORITHMS)}


# ---------------------------------------------------------------------------
# Domain 1 — operators
# ---------------------------------------------------------------------------
def generate_operators(days: int = 90, anomaly_rate: float = 0.05) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    start = datetime.now() - timedelta(days=days)
    rows: List[Dict] = []

    for d in range(days):
        date = start + timedelta(days=d)
        for shift in range(3):
            for op in OPERATORS:
                base_picks = op["baseline_picks"]
                base_err = op["baseline_error"]
                is_anom = rng.random() < anomaly_rate
                if is_anom:
                    kind = rng.choice(["fatigue", "errors", "lost", "stock_drop"])
                    if kind == "fatigue":
                        picks = max(10.0, base_picks * rng.uniform(0.25, 0.45))
                        err = base_err * rng.uniform(3.5, 6.0)
                        dist = 9500 * rng.uniform(0.9, 1.1)
                        stock_acc = rng.uniform(82, 90)
                    elif kind == "errors":
                        picks = base_picks * rng.uniform(0.8, 1.0)
                        err = base_err * rng.uniform(5.0, 9.0)
                        dist = 9500 * rng.uniform(1.0, 1.2)
                        stock_acc = rng.uniform(80, 88)
                    elif kind == "lost":
                        picks = base_picks * rng.uniform(0.4, 0.6)
                        err = base_err * rng.uniform(1.2, 2.0)
                        dist = 9500 * rng.uniform(2.0, 2.6)
                        stock_acc = rng.uniform(90, 96)
                    else:  # stock_drop
                        picks = base_picks * rng.uniform(0.8, 1.0)
                        err = base_err * rng.uniform(1.0, 1.6)
                        dist = 9500 * rng.uniform(0.9, 1.1)
                        stock_acc = rng.uniform(70, 82)
                else:
                    picks = rng.normal(base_picks, base_picks * 0.07)
                    err = max(0.1, rng.normal(base_err, 0.3))
                    dist = rng.normal(9500, 800)
                    stock_acc = rng.normal(98.0, 0.8)

                rows.append({
                    "date": date.date().isoformat(),
                    "operator_id": op["id"],
                    "operator_name": op["name"],
                    "shift": shift,
                    "day_of_week": date.weekday(),
                    "picks_per_hour": round(float(picks), 2),
                    "error_rate": round(float(min(err, 25.0)), 3),
                    "distance_m": round(float(max(dist, 1500.0)), 1),
                    "stock_accuracy": round(float(np.clip(stock_acc, 50, 100)), 2),
                    "orders_completed": int(max(2, picks * 0.18 + rng.normal(0, 1.0))),
                    "zone": int(rng.integers(0, len(ZONES))),
                    "true_anomaly": bool(is_anom),
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Domain 2 — inventory
# ---------------------------------------------------------------------------
def generate_inventory(days: int = 90, anomaly_rate: float = 0.05) -> pd.DataFrame:
    rng = np.random.default_rng(22)
    start = datetime.now() - timedelta(days=days)
    rows: List[Dict] = []

    for sku in SKUS:
        base_demand = rng.uniform(15, 75)
        stock = rng.uniform(200, 600)
        safety = base_demand * 4
        zero_streak = 0
        for d in range(days):
            date = start + timedelta(days=d)
            is_anom = rng.random() < anomaly_rate
            if is_anom:
                kind = rng.choice(["spike", "crash", "zero", "forecast"])
                if kind == "spike":
                    sold = base_demand * rng.uniform(4.5, 6.5)
                    forecast_ratio = rng.uniform(3.0, 5.0)
                elif kind == "crash":
                    sold = base_demand * rng.uniform(0.6, 1.0)
                    forecast_ratio = rng.uniform(0.9, 1.1)
                    stock = stock * rng.uniform(0.15, 0.30)
                elif kind == "zero":
                    sold = 0
                    forecast_ratio = 0
                    zero_streak += 1
                else:  # forecast
                    sold = base_demand * rng.uniform(2.8, 3.5)
                    forecast_ratio = rng.uniform(2.8, 3.5)
            else:
                sold = max(0.0, rng.normal(base_demand, base_demand * 0.18))
                forecast_ratio = rng.uniform(0.85, 1.15)
                zero_streak = 0

            stock -= sold
            reorder = stock < safety
            if reorder:
                stock += base_demand * rng.uniform(10, 18)

            rows.append({
                "date": date.date().isoformat(),
                "sku": sku["sku"],
                "name": sku["name"],
                "zone": ZONE_TO_INT[sku["zone"]],
                "zone_name": sku["zone"],
                "units_sold": round(float(sold), 1),
                "stock_level": round(float(max(stock, 0)), 1),
                "reorder_triggered": bool(reorder),
                "days_since_last_delivery": int(rng.integers(0, 14)),
                "demand_vs_forecast_ratio": round(float(forecast_ratio), 3),
                "stock_vs_safety_ratio": round(float(max(stock, 0) / max(safety, 1)), 3),
                "true_anomaly": bool(is_anom),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Domain 3 — picking routes
# ---------------------------------------------------------------------------
def generate_routes(n_orders: int = 500, anomaly_rate: float = 0.05) -> pd.DataFrame:
    rng = np.random.default_rng(33)
    start = datetime.now() - timedelta(days=90)
    rows: List[Dict] = []

    for i in range(n_orders):
        date = start + timedelta(days=int(rng.integers(0, 90)),
                                 hours=int(rng.integers(6, 22)))
        op = rng.choice(OPERATORS)
        sku_count = int(rng.integers(8, 30))
        is_anom = rng.random() < anomaly_rate
        if is_anom:
            kind = rng.choice(["long", "cold", "slow", "predict"])
            if kind == "long":
                distance = rng.uniform(3.0, 4.5) * (200 + sku_count * 35)
                duration = rng.uniform(2.5, 3.5) * (sku_count * 0.95)
                cold = rng.integers(0, 4)
                ppk = sku_count / max(distance / 1000, 0.1)
            elif kind == "cold":
                distance = rng.normal(200 + sku_count * 35, 80)
                duration = rng.normal(sku_count * 0.95, 1.5)
                cold = rng.integers(12, 25)
                ppk = sku_count / max(distance / 1000, 0.1)
            elif kind == "slow":
                distance = rng.normal(200 + sku_count * 35, 80)
                duration = rng.uniform(2.5, 3.2) * (sku_count * 0.95)
                cold = rng.integers(0, 4)
                ppk = sku_count / max(distance / 1000, 0.1) * 0.4
            else:  # predict
                distance = rng.uniform(2.0, 3.0) * (200 + sku_count * 35)
                duration = rng.uniform(2.0, 2.8) * (sku_count * 0.95)
                cold = rng.integers(0, 6)
                ppk = sku_count / max(distance / 1000, 0.1)
        else:
            distance = max(80, rng.normal(200 + sku_count * 35, 60))
            duration = max(3.0, rng.normal(sku_count * 0.95, 1.2))
            cold = int(rng.integers(0, 5))
            ppk = sku_count / max(distance / 1000, 0.1)

        rows.append({
            "order_id": f"ORD-{i+1:05d}",
            "timestamp": date.isoformat(timespec="seconds"),
            "operator_id": op["id"],
            "operator_name": op["name"],
            "algorithm_used": int(rng.integers(0, len(ALGORITHMS))),
            "sku_count": sku_count,
            "total_distance_m": round(float(distance), 1),
            "total_time_min": round(float(duration), 2),
            "aisles_visited": int(min(20, max(2, sku_count // 2 + rng.integers(-2, 3)))),
            "door_crossings": int(cold),
            "picks_per_km": round(float(ppk), 2),
            "cold_exposure_sec": int(cold * rng.uniform(45, 120)),
            "zone_spread": int(min(8, max(1, sku_count // 4 + rng.integers(-1, 2)))),
            "true_anomaly": bool(is_anom),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Domain 4 — deliveries
# ---------------------------------------------------------------------------
def generate_deliveries(weeks: int = 12, anomaly_rate: float = 0.05) -> pd.DataFrame:
    rng = np.random.default_rng(44)
    start = datetime.now() - timedelta(weeks=weeks)
    rows: List[Dict] = []

    delivery_id = 0
    supplier_streaks: Dict[str, int] = {s: 0 for s in SUPPLIERS}

    for w in range(weeks):
        for sku in SKUS:
            delivery_id += 1
            supplier = rng.choice(SUPPLIERS)
            expected = start + timedelta(weeks=w, days=int(rng.integers(0, 5)))
            qty_ordered = int(rng.integers(80, 400))
            is_anom = rng.random() < anomaly_rate
            if is_anom:
                kind = rng.choice(["late", "short", "damage", "pattern"])
                if kind == "late":
                    delay = int(rng.integers(5, 14))
                    qty_recv = qty_ordered
                    dmg = rng.uniform(0.0, 1.5)
                elif kind == "short":
                    delay = int(rng.integers(0, 3))
                    qty_recv = int(qty_ordered * rng.uniform(0.5, 0.8))
                    dmg = rng.uniform(0.0, 1.5)
                elif kind == "damage":
                    delay = int(rng.integers(0, 3))
                    qty_recv = qty_ordered
                    dmg = rng.uniform(5.0, 18.0)
                else:  # pattern
                    delay = int(rng.integers(3, 7))
                    qty_recv = int(qty_ordered * rng.uniform(0.85, 0.95))
                    dmg = rng.uniform(0.0, 2.5)
                    supplier_streaks[supplier] += 1
            else:
                delay = int(max(0, rng.normal(1.0, 1.0)))
                qty_recv = qty_ordered - int(rng.integers(0, 4))
                dmg = max(0.0, rng.normal(0.4, 0.25))
                supplier_streaks[supplier] = 0

            actual = expected + timedelta(days=delay)
            rows.append({
                "delivery_id": f"DEL-{delivery_id:05d}",
                "supplier": str(supplier),
                "sku": sku["sku"],
                "sku_count": 1,
                "expected_date": expected.date().isoformat(),
                "actual_date": actual.date().isoformat(),
                "delay_days": int(delay),
                "quantity_ordered": int(qty_ordered),
                "quantity_received": int(qty_recv),
                "shortfall_pct": round(100.0 * (qty_ordered - qty_recv) / max(qty_ordered, 1), 2),
                "damage_rate": round(float(dmg), 2),
                "zone": ZONE_TO_INT[sku["zone"]],
                "supplier_late_streak": int(supplier_streaks[supplier]),
                "true_anomaly": bool(is_anom),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Real-time tick
# ---------------------------------------------------------------------------
def generate_tick(domain: str, force_anomaly: bool = False) -> Dict:
    rng = np.random.default_rng()
    now = datetime.now()
    if domain == "operators":
        op = OPERATORS[int(rng.integers(0, len(OPERATORS)))]
        if force_anomaly:
            picks = op["baseline_picks"] * rng.uniform(0.25, 0.50)
            err = op["baseline_error"] * rng.uniform(4.0, 8.0)
            dist = 9500 * rng.uniform(1.6, 2.5)
            stock_acc = rng.uniform(75, 88)
        else:
            picks = rng.normal(op["baseline_picks"], op["baseline_picks"] * 0.07)
            err = max(0.1, rng.normal(op["baseline_error"], 0.3))
            dist = rng.normal(9500, 800)
            stock_acc = rng.normal(98.0, 0.8)
        return {
            "date": now.date().isoformat(),
            "operator_id": op["id"],
            "operator_name": op["name"],
            "shift": int(rng.integers(0, 3)),
            "day_of_week": now.weekday(),
            "picks_per_hour": round(float(picks), 2),
            "error_rate": round(float(min(err, 25.0)), 3),
            "distance_m": round(float(max(dist, 1500.0)), 1),
            "stock_accuracy": round(float(np.clip(stock_acc, 50, 100)), 2),
            "orders_completed": int(max(2, picks * 0.18)),
            "zone": int(rng.integers(0, len(ZONES))),
        }
    if domain == "inventory":
        sku = SKUS[int(rng.integers(0, len(SKUS)))]
        base = 40.0
        if force_anomaly:
            sold = base * rng.uniform(4.0, 6.0)
            ratio = rng.uniform(3.0, 5.0)
            stock = rng.uniform(20, 100)
        else:
            sold = max(0.0, rng.normal(base, base * 0.18))
            ratio = rng.uniform(0.85, 1.15)
            stock = rng.uniform(150, 500)
        return {
            "date": now.date().isoformat(),
            "sku": sku["sku"],
            "name": sku["name"],
            "zone": ZONE_TO_INT[sku["zone"]],
            "zone_name": sku["zone"],
            "units_sold": round(float(sold), 1),
            "stock_level": round(float(stock), 1),
            "reorder_triggered": stock < 150,
            "days_since_last_delivery": int(rng.integers(0, 14)),
            "demand_vs_forecast_ratio": round(float(ratio), 3),
            "stock_vs_safety_ratio": round(float(stock / 160.0), 3),
        }
    if domain == "routes":
        op = OPERATORS[int(rng.integers(0, len(OPERATORS)))]
        sku_count = int(rng.integers(8, 30))
        if force_anomaly:
            distance = rng.uniform(2.8, 4.0) * (200 + sku_count * 35)
            duration = rng.uniform(2.5, 3.2) * (sku_count * 0.95)
            cold = int(rng.integers(10, 22))
        else:
            distance = max(80, rng.normal(200 + sku_count * 35, 60))
            duration = max(3.0, rng.normal(sku_count * 0.95, 1.2))
            cold = int(rng.integers(0, 5))
        return {
            "order_id": f"ORD-{int(rng.integers(60000, 99999))}",
            "timestamp": now.isoformat(timespec="seconds"),
            "operator_id": op["id"],
            "operator_name": op["name"],
            "algorithm_used": int(rng.integers(0, len(ALGORITHMS))),
            "sku_count": sku_count,
            "total_distance_m": round(float(distance), 1),
            "total_time_min": round(float(duration), 2),
            "aisles_visited": int(min(20, max(2, sku_count // 2))),
            "door_crossings": cold,
            "picks_per_km": round(float(sku_count / max(distance / 1000, 0.1)), 2),
            "cold_exposure_sec": int(cold * rng.uniform(45, 120)),
            "zone_spread": int(min(8, max(1, sku_count // 4))),
        }
    # deliveries
    sku = SKUS[int(rng.integers(0, len(SKUS)))]
    supplier = SUPPLIERS[int(rng.integers(0, len(SUPPLIERS)))]
    if force_anomaly:
        delay = int(rng.integers(5, 14))
        dmg = rng.uniform(5.0, 15.0)
        qty_ord = int(rng.integers(80, 400))
        qty_recv = int(qty_ord * rng.uniform(0.55, 0.85))
    else:
        delay = int(max(0, rng.normal(1.0, 1.0)))
        dmg = max(0.0, rng.normal(0.4, 0.25))
        qty_ord = int(rng.integers(80, 400))
        qty_recv = qty_ord - int(rng.integers(0, 4))
    expected = now
    actual = expected + timedelta(days=delay)
    return {
        "delivery_id": f"DEL-{int(rng.integers(60000, 99999))}",
        "supplier": supplier,
        "sku": sku["sku"],
        "sku_count": 1,
        "expected_date": expected.date().isoformat(),
        "actual_date": actual.date().isoformat(),
        "delay_days": delay,
        "quantity_ordered": qty_ord,
        "quantity_received": qty_recv,
        "shortfall_pct": round(100.0 * (qty_ord - qty_recv) / max(qty_ord, 1), 2),
        "damage_rate": round(float(dmg), 2),
        "zone": ZONE_TO_INT[sku["zone"]],
        "supplier_late_streak": 0,
    }
