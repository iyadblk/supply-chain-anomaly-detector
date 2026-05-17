"""Real-time stream endpoint."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

from api.detector import ENGINE
from api.models import StreamTickRequest, StreamTickResponse
from data.generator import generate_tick

router = APIRouter(prefix="/api/v1/stream", tags=["realtime"])


@router.post("/tick", response_model=StreamTickResponse)
def stream_tick(req: StreamTickRequest) -> StreamTickResponse:
    if req.domain not in ("operators", "inventory", "routes", "deliveries"):
        raise HTTPException(status_code=400, detail=f"Unknown domain: {req.domain}")
    record = generate_tick(req.domain, force_anomaly=req.force_anomaly)
    try:
        results = ENGINE.detect(req.domain, [record])
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    res = results[0]
    return StreamTickResponse(
        domain=req.domain,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        record=record,
        is_anomaly=res["is_anomaly"],
        severity=res["severity"],
        severity_band=res["severity_band"],
        explanation=res["explanation"] if res["is_anomaly"] else None,
    )
