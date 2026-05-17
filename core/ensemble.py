"""Ensemble of Isolation Forest + LOF + DBSCAN."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from core.dbscan import DBSCANModel
from core.isolation_forest import IsolationForestModel
from core.local_outlier import LOFModel


@dataclass
class EnsembleResult:
    is_anomaly: np.ndarray         # 0/1
    severity: np.ndarray           # 0-100
    score_if: np.ndarray
    score_lof: np.ndarray
    score_dbscan: np.ndarray
    flag_if: np.ndarray
    flag_lof: np.ndarray
    flag_dbscan: np.ndarray
    agreement: np.ndarray          # number of models flagging (0-3)


class AnomalyEnsemble:
    WEIGHTS = {"if": 0.4, "lof": 0.4, "dbscan": 0.2}

    def __init__(self, contamination: float = 0.05):
        self.iso = IsolationForestModel(contamination=contamination)
        self.lof = LOFModel(contamination=contamination)
        self.db = DBSCANModel()
        self.feature_names: List[str] = []
        self.fitted = False

    def fit(self, X: np.ndarray, feature_names: List[str]) -> "AnomalyEnsemble":
        self.feature_names = list(feature_names)
        self.iso.fit(X, feature_names)
        self.lof.fit(X)
        self.db.fit(X)
        self.fitted = True
        return self

    def predict(self, X: np.ndarray) -> EnsembleResult:
        X = np.asarray(X, dtype=float)
        flag_if = self.iso.predict(X)
        flag_lof = self.lof.predict(X)
        flag_db = self.db.predict(X)
        score_if = self.iso.score(X)
        score_lof = self.lof.score(X)
        score_db = self.db.score(X)
        agreement = flag_if + flag_lof + flag_db
        is_anom = (agreement >= 2).astype(int)
        severity = (
            self.WEIGHTS["if"] * score_if
            + self.WEIGHTS["lof"] * score_lof
            + self.WEIGHTS["dbscan"] * score_db
        ) * 100.0
        severity = np.clip(severity, 0.0, 100.0)
        return EnsembleResult(
            is_anomaly=is_anom,
            severity=severity,
            score_if=score_if,
            score_lof=score_lof,
            score_dbscan=score_db,
            flag_if=flag_if,
            flag_lof=flag_lof,
            flag_dbscan=flag_db,
            agreement=agreement,
        )

    def model_agreement_rate(self, X: np.ndarray) -> float:
        res = self.predict(X)
        # rate at which 2+ models concur out of the flagged points
        flagged_any = (res.agreement >= 1).sum()
        if flagged_any == 0:
            return 1.0
        return float((res.agreement >= 2).sum() / flagged_any)

    def metrics_vs_truth(self, X: np.ndarray, y_true: np.ndarray) -> Dict[str, Dict[str, float]]:
        from sklearn.metrics import (precision_score, recall_score, f1_score, roc_auc_score)
        out: Dict[str, Dict[str, float]] = {}
        y_true = np.asarray(y_true).astype(int)
        flag_if = self.iso.predict(X)
        flag_lof = self.lof.predict(X)
        flag_db = self.db.predict(X)
        score_if = self.iso.score(X)
        score_lof = self.lof.score(X)
        score_db = self.db.score(X)
        ens = self.predict(X)
        for name, flag, score in [
            ("isolation_forest", flag_if, score_if),
            ("lof", flag_lof, score_lof),
            ("dbscan", flag_db, score_db),
            ("ensemble", ens.is_anomaly, ens.severity / 100.0),
        ]:
            try:
                auc = float(roc_auc_score(y_true, score))
            except ValueError:
                auc = 0.5
            out[name] = {
                "precision": float(precision_score(y_true, flag, zero_division=0)),
                "recall": float(recall_score(y_true, flag, zero_division=0)),
                "f1": float(f1_score(y_true, flag, zero_division=0)),
                "roc_auc": auc,
            }
        return out
