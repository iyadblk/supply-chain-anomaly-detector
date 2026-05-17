"""Picking-route anomaly endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from api.detector import ENGINE
from api.models import DetectResponse, RouteRecord

router = APIRouter(prefix="/api/v1/detect", tags=["routes"])


@router.post("/routes", response_model=DetectResponse)
def detect_routes(records: List[RouteRecord]) -> DetectResponse:
    try:
        payload = [r.model_dump() for r in records]
        results = ENGINE.detect("routes", payload)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Detection failed: {e}") from e
    return DetectResponse(
        domain="routes",
        detected_at=datetime.now().isoformat(timespec="seconds"),
        total=len(results),
        anomalies=sum(1 for r in results if r["is_anomaly"]),
        results=results,
    )
