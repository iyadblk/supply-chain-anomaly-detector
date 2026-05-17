"""Local Outlier Factor wrapper (novelty mode)."""
from __future__ import annotations

import numpy as np
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler


class LOFModel:
    def __init__(self, n_neighbors: int = 20, contamination: float = 0.05):
        self.n_neighbors = n_neighbors
        self.contamination = contamination
        self.scaler = StandardScaler()
        self.model = LocalOutlierFactor(
            n_neighbors=n_neighbors,
            contamination=contamination,
            novelty=True,
            n_jobs=-1,
        )
        self.fitted = False

    def fit(self, X: np.ndarray) -> "LOFModel":
        X = np.asarray(X, dtype=float)
        n = max(2, min(self.n_neighbors, len(X) - 1))
        self.model = LocalOutlierFactor(
            n_neighbors=n,
            contamination=self.contamination,
            novelty=True,
            n_jobs=-1,
        )
        Xs = self.scaler.fit_transform(X)
        self.model.fit(Xs)
        self.fitted = True
        raw_train = -self.model.score_samples(Xs)
        self._score_lo = float(np.percentile(raw_train, 5))
        self._score_hi = float(np.percentile(raw_train, 99))
        if self._score_hi - self._score_lo < 1e-9:
            self._score_hi = self._score_lo + 1.0
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        Xs = self.scaler.transform(np.asarray(X, dtype=float))
        return (self.model.predict(Xs) == -1).astype(int)

    def score(self, X: np.ndarray) -> np.ndarray:
        Xs = self.scaler.transform(np.asarray(X, dtype=float))
        raw = -self.model.score_samples(Xs)
        scaled = (raw - self._score_lo) / (self._score_hi - self._score_lo)
        return np.clip(scaled, 0.0, 1.0)
