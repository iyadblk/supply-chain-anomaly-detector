"""Isolation Forest wrapper."""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class IsolationForestModel:
    """Anomaly detector using sklearn IsolationForest."""

    def __init__(self, contamination: float = 0.05, n_estimators: int = 200,
                 random_state: int = 42):
        self.contamination = contamination
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            max_features=1.0,
            random_state=random_state,
            n_jobs=-1,
        )
        self.fitted = False
        self.feature_names: list[str] = []

    def fit(self, X: np.ndarray, feature_names: list[str] | None = None) -> "IsolationForestModel":
        X = np.asarray(X, dtype=float)
        Xs = self.scaler.fit_transform(X)
        self.model.fit(Xs)
        self.fitted = True
        if feature_names:
            self.feature_names = list(feature_names)
        # Calibrate score range on training data so single-point inference
        # produces a stable [0,1] score.
        raw_train = -self.model.score_samples(Xs)
        self._score_lo = float(np.percentile(raw_train, 5))
        self._score_hi = float(np.percentile(raw_train, 99))
        if self._score_hi - self._score_lo < 1e-9:
            self._score_hi = self._score_lo + 1.0
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return 1 for anomalies, 0 for normal."""
        Xs = self.scaler.transform(np.asarray(X, dtype=float))
        return (self.model.predict(Xs) == -1).astype(int)

    def score(self, X: np.ndarray) -> np.ndarray:
        """Higher = more anomalous (0-1 scaled, calibrated on training)."""
        Xs = self.scaler.transform(np.asarray(X, dtype=float))
        raw = -self.model.score_samples(Xs)
        scaled = (raw - self._score_lo) / (self._score_hi - self._score_lo)
        return np.clip(scaled, 0.0, 1.0)

    def feature_importance(self, X: np.ndarray) -> dict[str, float]:
        """Pseudo feature importance via per-feature permutation impact on score."""
        if not self.fitted or len(self.feature_names) == 0:
            return {}
        X = np.asarray(X, dtype=float)
        base = self.score(X).mean()
        importance: dict[str, float] = {}
        rng = np.random.default_rng(0)
        for i, name in enumerate(self.feature_names):
            Xp = X.copy()
            rng.shuffle(Xp[:, i])
            shuffled = self.score(Xp).mean()
            importance[name] = float(abs(shuffled - base))
        total = sum(importance.values()) or 1.0
        return {k: v / total for k, v in importance.items()}
