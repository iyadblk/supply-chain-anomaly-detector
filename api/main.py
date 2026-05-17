"""FastAPI entry point — Supply Chain Anomaly Detector."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.detector import DOMAINS, ENGINE
from api.models import (StatsResponse, StatusResponse, TrainRequest, TrainResponse)
from api.routes import deliveries as deliveries_router
from api.routes import inventory as inventory_router
from api.routes import operators as operators_router
from api.routes import realtime as realtime_router
from api.routes import routes as routes_router

logger = logging.getLogger("anomaly-detector")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Bootstrapping detection engine…")
    ENGINE.bootstrap()
    logger.info("Detection engine ready — models trained on %d domains.", len(DOMAINS))
    yield


app = FastAPI(
    title="Supply Chain Anomaly Detector",
    description=("Real-time anomaly detection across operators, inventory, "
                 "picking routes and supplier deliveries — Project 4 of the "
                 "logistics portfolio by Iyad Belkadi."),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Root / status
# ---------------------------------------------------------------------------
@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "name": "Supply Chain Anomaly Detector",
        "version": "1.0.0",
        "api": "v1",
        "docs": "/docs",
        "swagger": "/api/v1/docs",
        "author": "Iyad Belkadi",
        "domains": list(DOMAINS),
        "status": "online",
    }


@app.get("/api/v1/docs", include_in_schema=False)
def alias_docs() -> Dict[str, str]:
    return {"docs": "/docs", "redoc": "/redoc"}


@app.get("/api/v1/status", response_model=StatusResponse, tags=["meta"])
def status() -> StatusResponse:
    s = ENGINE.status()
    return StatusResponse(**s)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
@app.post("/api/v1/train", response_model=TrainResponse, tags=["meta"])
def train(req: TrainRequest) -> TrainResponse:
    try:
        info = ENGINE.train(req.domain)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Training failed: {e}") from e
    return TrainResponse(
        status="ok",
        trained_at=datetime.now().isoformat(timespec="seconds"),
        domains=info,
    )


# ---------------------------------------------------------------------------
# Detect (per-domain routers + cross-domain endpoint)
# ---------------------------------------------------------------------------
app.include_router(operators_router.router)
app.include_router(inventory_router.router)
app.include_router(routes_router.router)
app.include_router(deliveries_router.router)
app.include_router(realtime_router.router)


@app.post("/api/v1/detect/all", tags=["meta"])
def detect_all(snapshot: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    try:
        results = ENGINE.detect_all(snapshot)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Detection failed: {e}") from e
    summary = {d: {"total": len(v), "anomalies": sum(1 for x in v if x["is_anomaly"])}
               for d, v in results.items()}
    return {
        "detected_at": datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "results": results,
    }


# ---------------------------------------------------------------------------
# History / stats
# ---------------------------------------------------------------------------
@app.get("/api/v1/anomalies/history", tags=["history"])
def anomaly_history(
    domain: Optional[str] = Query(default=None),
    severity_min: float = Query(default=0.0, ge=0.0, le=100.0),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> Dict[str, Any]:
    items = ENGINE.history(domain=domain, severity_min=severity_min,
                           date_from=date_from, date_to=date_to, limit=limit)
    return {"count": len(items), "items": items}


@app.get("/api/v1/anomalies/stats", response_model=StatsResponse, tags=["history"])
def anomaly_stats() -> StatsResponse:
    return StatsResponse(**ENGINE.stats())


@app.get("/api/v1/models/{domain}", tags=["meta"])
def model_info(domain: str) -> Dict[str, Any]:
    if domain not in DOMAINS:
        raise HTTPException(status_code=404, detail=f"Unknown domain: {domain}")
    return ENGINE.model_info(domain)


@app.get("/api/v1/data/{domain}", tags=["meta"])
def sample_dataset(domain: str, limit: int = Query(default=200, ge=1, le=5000)) -> Dict[str, Any]:
    if domain not in DOMAINS:
        raise HTTPException(status_code=404, detail=f"Unknown domain: {domain}")
    df = ENGINE.dataset(domain).head(limit)
    return {"domain": domain, "count": len(df), "records": df.to_dict(orient="records")}
