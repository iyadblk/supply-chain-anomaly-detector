"""Pydantic schemas for the REST API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Records (lenient — extra fields are tolerated and echoed back)
# ---------------------------------------------------------------------------
class OperatorRecord(BaseModel):
    operator_id: str
    picks_per_hour: float
    error_rate: float
    distance_m: float
    stock_accuracy: float
    orders_completed: int = 0
    zone: int = 0
    shift: int = 0
    day_of_week: int = 0
    operator_name: Optional[str] = None
    date: Optional[str] = None

    model_config = {"extra": "allow"}


class InventoryRecord(BaseModel):
    sku: str
    units_sold: float
    stock_level: float
    days_since_last_delivery: int = 0
    demand_vs_forecast_ratio: float = 1.0
    stock_vs_safety_ratio: float = 1.0
    zone: int = 0
    name: Optional[str] = None
    date: Optional[str] = None
    reorder_triggered: Optional[bool] = None

    model_config = {"extra": "allow"}


class RouteRecord(BaseModel):
    order_id: str
    total_distance_m: float
    total_time_min: float
    aisles_visited: int
    door_crossings: int
    picks_per_km: float
    cold_exposure_sec: int = 0
    algorithm_used: int = 0
    sku_count: int = 0
    zone_spread: int = 0
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    timestamp: Optional[str] = None

    model_config = {"extra": "allow"}


class DeliveryRecord(BaseModel):
    delivery_id: str
    supplier: str
    delay_days: int
    quantity_ordered: int
    quantity_received: int
    shortfall_pct: float
    damage_rate: float
    zone: int = 0
    supplier_late_streak: int = 0
    sku: Optional[str] = None
    expected_date: Optional[str] = None
    actual_date: Optional[str] = None

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Requests / responses
# ---------------------------------------------------------------------------
class TrainRequest(BaseModel):
    domain: str = Field(default="all",
                        description="all | operators | inventory | routes | deliveries")


class TrainResponse(BaseModel):
    status: str
    trained_at: str
    domains: Dict[str, Dict[str, Any]]


class AnomalyResult(BaseModel):
    record_index: int
    is_anomaly: bool
    severity: float
    severity_band: str
    agreement: int
    entity: str
    top_feature: str
    z_score: float
    likely_cause: str
    explanation: str
    record: Dict[str, Any]


class DetectResponse(BaseModel):
    domain: str
    detected_at: str
    total: int
    anomalies: int
    results: List[AnomalyResult]


class StatusResponse(BaseModel):
    status: str
    api_version: str
    trained: Dict[str, bool]
    last_trained_at: Dict[str, Optional[str]]
    data_points: Dict[str, int]
    history_size: int


class AnomalyHistoryEntry(BaseModel):
    detected_at: str
    domain: str
    entity: str
    severity: float
    severity_band: str
    likely_cause: str
    record: Dict[str, Any]


class StatsResponse(BaseModel):
    total_anomalies: int
    by_domain: Dict[str, int]
    severity_distribution: Dict[str, int]
    top_entities: List[Dict[str, Any]]


class StreamTickRequest(BaseModel):
    domain: str = Field(default="operators")
    force_anomaly: bool = False


class StreamTickResponse(BaseModel):
    domain: str
    generated_at: str
    record: Dict[str, Any]
    is_anomaly: bool
    severity: float
    severity_band: str
    explanation: Optional[str] = None
