"""DBSCAN clustering used as a validation signal."""
from __future__ import annotations

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


class DBSCANModel:
    def __init__(self, min_samples: int = 5):
        self.min_samples = min_samples
        self.scaler = StandardScaler()
        self.eps: float = 0.5
        self._train_Xs: np.ndarray | None = None
        self._train_labels: np.ndarray | None = None
        self.fitted = False

    @staticmethod
    def _auto_eps(Xs: np.ndarray, k: int) -> float:
        n = len(Xs)
        if n <= k:
            return 0.5
        nn = NearestNeighbors(n_neighbors=k)
        nn.fit(Xs)
        d, _ = nn.kneighbors(Xs)
        kd = np.sort(d[:, -1])
        # knee = 90th percentile (robust auto-eps)
        return float(max(0.1, np.percentile(kd, 90)))

    def fit(self, X: np.ndarray) -> "DBSCANModel":
        X = np.asarray(X, dtype=float)
        Xs = self.scaler.fit_transform(X)
        self.eps = self._auto_eps(Xs, self.min_samples)
        labels = DBSCAN(eps=self.eps, min_samples=self.min_samples, n_jobs=-1).fit_predict(Xs)
        self._train_Xs = Xs
        self._train_labels = labels
        self.fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict via nearest-training-point assignment (DBSCAN has no native predict)."""
        Xs = self.scaler.transform(np.asarray(X, dtype=float))
        if self._train_Xs is None or self._train_labels is None:
            return np.zeros(len(Xs), dtype=int)
        nn = NearestNeighbors(n_neighbors=1).fit(self._train_Xs)
        dist, idx = nn.kneighbors(Xs)
        nearest_label = self._train_labels[idx[:, 0]]
        # anomaly if nearest cluster is noise OR distance > eps
        is_anom = (nearest_label == -1) | (dist[:, 0] > self.eps)
        return is_anom.astype(int)

    def score(self, X: np.ndarray) -> np.ndarray:
        """Score = distance to nearest core sample / eps, clipped to [0,1]."""
        Xs = self.scaler.transform(np.asarray(X, dtype=float))
        if self._train_Xs is None:
            return np.zeros(len(Xs))
        nn = NearestNeighbors(n_neighbors=1).fit(self._train_Xs)
        dist, _ = nn.kneighbors(Xs)
        raw = dist[:, 0] / max(self.eps, 1e-6)
        return np.clip(raw / 3.0, 0.0, 1.0)  # 3*eps maps to score 1.0
