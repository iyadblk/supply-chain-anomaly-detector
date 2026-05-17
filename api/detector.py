"""Core detection engine — singleton wrapping trained models + history."""
from __future__ import annotations

import threading
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

import numpy as np
import pandas as pd

from core.trainer import DOMAIN_FEATURES, TrainedDomain, train_domain
from data import sample_data

DOMAINS = ("operators", "inventory", "routes", "deliveries")


class DetectionEngine:
    """Trains per-domain ensembles, scores incoming records, keeps anomaly history."""

    HISTORY_SIZE = 500

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._models: Dict[str, TrainedDomain] = {}
        self._history: Deque[Dict[str, Any]] = deque(maxlen=self.HISTORY_SIZE)
        self._datasets: Dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------------
    def bootstrap(self) -> None:
        """Generate baseline data and train all 4 domains on startup."""
        self._datasets = sample_data.all_data()
        for d in DOMAINS:
            self._models[d] = train_domain(d, self._datasets[d])
        # seed history with anomalies found in the training set
        for d in DOMAINS:
            df = self._datasets[d]
            res = self.detect(d, df.to_dict(orient="records"), record_history=False)
            for item in res:
                if item["is_anomaly"]:
                    self._history.append({
                        "detected_at": datetime.now().isoformat(timespec="seconds"),
                        "domain": d,
                        "entity": item["entity"],
                        "severity": item["severity"],
                        "severity_band": item["severity_band"],
                        "likely_cause": item["likely_cause"],
                        "record": item["record"],
                    })

    # ------------------------------------------------------------------
    def train(self, domain: str = "all") -> Dict[str, Dict[str, Any]]:
        with self._lock:
            target = DOMAINS if domain == "all" else (domain,)
            out: Dict[str, Dict[str, Any]] = {}
            for d in target:
                if d not in DOMAINS:
                    raise ValueError(f"Unknown domain: {d}")
                self._datasets[d] = self._datasets.get(d) or getattr(sample_data, f"{d}_df")()
                td = train_domain(d, self._datasets[d])
                self._models[d] = td
                out[d] = {
                    "trained_at": td.trained_at,
                    "n_records": td.n_records,
                    "features": td.features,
                    "metrics": td.metrics,
                }
            return out

    # ------------------------------------------------------------------
    def status(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "api_version": "v1",
            "trained": {d: d in self._models for d in DOMAINS},
            "last_trained_at": {d: (self._models[d].trained_at if d in self._models else None)
                                for d in DOMAINS},
            "data_points": {d: int(len(self._datasets.get(d, pd.DataFrame())))
                            for d in DOMAINS},
            "history_size": len(self._history),
        }

    # ------------------------------------------------------------------
    def detect(self, domain: str, records: List[Dict[str, Any]],
               record_history: bool = True) -> List[Dict[str, Any]]:
        if domain not in self._models:
            raise RuntimeError(f"Models for '{domain}' are not trained.")
        if not records:
            return []
        td = self._models[domain]
        df = pd.DataFrame(records)
        for f in td.features:
            if f not in df.columns:
                df[f] = 0
        X = df[td.features].astype(float).to_numpy()
        res = td.ensemble.predict(X)
        out: List[Dict[str, Any]] = []
        ts = datetime.now().isoformat(timespec="seconds")
        for i, rec in enumerate(records):
            is_anom = bool(res.is_anomaly[i])
            severity = float(res.severity[i])
            row = df.iloc[i]
            expl = td.explainer.explain(row, severity)
            item = {
                "record_index": i,
                "is_anomaly": is_anom,
                "severity": round(severity, 2),
                "severity_band": expl["severity_band"],
                "agreement": int(res.agreement[i]),
                "entity": expl["entity"],
                "top_feature": expl["top_feature"],
                "z_score": expl["z_score"],
                "likely_cause": expl["likely_cause"],
                "explanation": expl["explanation"],
                "record": rec,
            }
            out.append(item)
            if is_anom and record_history:
                self._history.append({
                    "detected_at": ts,
                    "domain": domain,
                    "entity": expl["entity"],
                    "severity": severity,
                    "severity_band": expl["severity_band"],
                    "likely_cause": expl["likely_cause"],
                    "record": rec,
                })
        return out

    # ------------------------------------------------------------------
    def detect_all(self, snapshot: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        result: Dict[str, List[Dict[str, Any]]] = {}
        for d in DOMAINS:
            if d in snapshot and snapshot[d]:
                result[d] = self.detect(d, snapshot[d])
            else:
                result[d] = []
        return result

    # ------------------------------------------------------------------
    def history(self, domain: Optional[str] = None, severity_min: float = 0.0,
                date_from: Optional[str] = None, date_to: Optional[str] = None,
                limit: int = 200) -> List[Dict[str, Any]]:
        items = list(self._history)
        if domain and domain != "all":
            items = [x for x in items if x["domain"] == domain]
        items = [x for x in items if x["severity"] >= severity_min]
        if date_from:
            items = [x for x in items if x["detected_at"] >= date_from]
        if date_to:
            items = [x for x in items if x["detected_at"] <= date_to]
        items = sorted(items, key=lambda x: x["detected_at"], reverse=True)
        return items[:limit]

    # ------------------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        items = list(self._history)
        total = len(items)
        by_domain: Dict[str, int] = {d: 0 for d in DOMAINS}
        bands = {"high": 0, "medium": 0, "low": 0}
        entity_counts: Dict[str, int] = {}
        for x in items:
            by_domain[x["domain"]] = by_domain.get(x["domain"], 0) + 1
            bands[x["severity_band"]] = bands.get(x["severity_band"], 0) + 1
            entity_counts[x["entity"]] = entity_counts.get(x["entity"], 0) + 1
        top = sorted(
            ({"entity": k, "count": v} for k, v in entity_counts.items()),
            key=lambda x: x["count"], reverse=True,
        )[:10]
        return {
            "total_anomalies": total,
            "by_domain": by_domain,
            "severity_distribution": bands,
            "top_entities": top,
        }

    # ------------------------------------------------------------------
    def model_info(self, domain: str) -> Dict[str, Any]:
        if domain not in self._models:
            return {}
        td = self._models[domain]
        ds = self._datasets.get(domain, pd.DataFrame())
        X = ds[td.features].astype(float).to_numpy() if not ds.empty else np.zeros((0, len(td.features)))
        return {
            "domain": domain,
            "features": td.features,
            "n_records": td.n_records,
            "trained_at": td.trained_at,
            "metrics": td.metrics,
            "feature_importance": td.ensemble.iso.feature_importance(X) if len(X) else {},
            "agreement_rate": td.ensemble.model_agreement_rate(X) if len(X) else 0.0,
        }

    # ------------------------------------------------------------------
    def dataset(self, domain: str) -> pd.DataFrame:
        return self._datasets.get(domain, pd.DataFrame()).copy()


ENGINE = DetectionEngine()
