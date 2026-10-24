"""
Statistical Anomaly and Outlier Detection Algorithms.
Provides robust implementations of IQR (Interquartile Range) and Z-Score detectors.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


@dataclass
class AnomalyDetectionResult:
    """Summary of an anomaly detection pass over a single numerical series."""
    column: str
    method: str
    total_samples: int
    outlier_count: int
    outlier_percentage: float
    outlier_indices: List[int]
    lower_threshold: float
    upper_threshold: float
    summary_stats: Dict[str, float] = field(default_factory=dict)

    @property
    def has_anomalies(self) -> bool:
        return self.outlier_count > 0


class IQRAnomalyDetector:
    """
    Tukey's Fences Interquartile Range (IQR) Outlier Detector.
    Resistant to extreme viral or corrupted points compared to mean-based methods.
    """

    def __init__(self, factor: float = 1.5):
        if factor <= 0:
            raise ValueError(f"IQR factor must be positive, got {factor}")
        self.factor = factor

    def detect(self, series: pd.Series, column_name: Optional[str] = None) -> AnomalyDetectionResult:
        col = column_name or (series.name if hasattr(series, "name") and series.name else "unnamed_metric")
        clean_s = pd.to_numeric(series, errors="coerce").dropna()

        if len(clean_s) < 4:
            return AnomalyDetectionResult(
                column=str(col),
                method=f"IQR(factor={self.factor})",
                total_samples=len(series),
                outlier_count=0,
                outlier_percentage=0.0,
                outlier_indices=[],
                lower_threshold=float("-inf"),
                upper_threshold=float("inf"),
                summary_stats={"n_valid": len(clean_s)}
            )

        q25 = float(clean_s.quantile(0.25))
        q75 = float(clean_s.quantile(0.75))
        iqr = q75 - q25

        lower_bound = q25 - (self.factor * iqr)
        upper_bound = q75 + (self.factor * iqr)

        outlier_mask = (clean_s < lower_bound) | (clean_s > upper_bound)
        outlier_indices = clean_s[outlier_mask].index.tolist()
        outlier_count = len(outlier_indices)
        pct = (outlier_count / len(series)) * 100 if len(series) > 0 else 0.0

        return AnomalyDetectionResult(
            column=str(col),
            method=f"IQR(factor={self.factor})",
            total_samples=len(series),
            outlier_count=outlier_count,
            outlier_percentage=round(pct, 2),
            outlier_indices=outlier_indices,
            lower_threshold=round(lower_bound, 4),
            upper_threshold=round(upper_bound, 4),
            summary_stats={
                "q25": round(q25, 4),
                "q75": round(q75, 4),
                "iqr": round(iqr, 4),
                "median": round(float(clean_s.median()), 4),
                "min": round(float(clean_s.min()), 4),
                "max": round(float(clean_s.max()), 4),
            }
        )


class ZScoreAnomalyDetector:
    """
    Standard Score (Z-Score) Outlier Detector.
    Quantifies the distance of samples from the mean in units of standard deviation.
    """

    def __init__(self, threshold: float = 3.0):
        if threshold <= 0:
            raise ValueError(f"Z-score threshold must be positive, got {threshold}")
        self.threshold = threshold

    def detect(self, series: pd.Series, column_name: Optional[str] = None) -> AnomalyDetectionResult:
        col = column_name or (series.name if hasattr(series, "name") and series.name else "unnamed_metric")
        clean_s = pd.to_numeric(series, errors="coerce").dropna()

        if len(clean_s) < 2:
            return AnomalyDetectionResult(
                column=str(col),
                method=f"ZScore(threshold={self.threshold})",
                total_samples=len(series),
                outlier_count=0,
                outlier_percentage=0.0,
                outlier_indices=[],
                lower_threshold=float("-inf"),
                upper_threshold=float("inf"),
                summary_stats={"n_valid": len(clean_s)}
            )

        mean_val = float(clean_s.mean())
        std_val = float(clean_s.std(ddof=1))

        if std_val == 0.0:
            return AnomalyDetectionResult(
                column=str(col),
                method=f"ZScore(threshold={self.threshold})",
                total_samples=len(series),
                outlier_count=0,
                outlier_percentage=0.0,
                outlier_indices=[],
                lower_threshold=mean_val,
                upper_threshold=mean_val,
                summary_stats={"mean": mean_val, "std": 0.0}
            )

        z_scores = np.abs((clean_s - mean_val) / std_val)
        outlier_mask = z_scores > self.threshold
        outlier_indices = clean_s[outlier_mask].index.tolist()
        outlier_count = len(outlier_indices)
        pct = (outlier_count / len(series)) * 100 if len(series) > 0 else 0.0

        lower_bound = mean_val - (self.threshold * std_val)
        upper_bound = mean_val + (self.threshold * std_val)

        return AnomalyDetectionResult(
            column=str(col),
            method=f"ZScore(threshold={self.threshold})",
            total_samples=len(series),
            outlier_count=outlier_count,
            outlier_percentage=round(pct, 2),
            outlier_indices=outlier_indices,
            lower_threshold=round(lower_bound, 4),
            upper_threshold=round(upper_bound, 4),
            summary_stats={
                "mean": round(mean_val, 4),
                "std": round(std_val, 4),
                "threshold_stds": self.threshold
            }
        )
