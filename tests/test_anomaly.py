"""
Unit tests for statistical anomaly detection algorithms (IQR & Z-Score).
"""
import pytest
import pandas as pd
import numpy as np

from src.anomaly import IQRAnomalyDetector, ZScoreAnomalyDetector


def test_iqr_detector_with_known_outliers():
    # Regular values with two clear outliers (1.0 and 100.0)
    data = pd.Series([20, 21, 22, 20, 21, 22, 23, 21, 20, 100, 1])
    detector = IQRAnomalyDetector(factor=1.5)
    res = detector.detect(data, column_name="test_col")

    assert res.has_anomalies
    assert res.outlier_count == 2
    # Verify that indices 9 (100) and 10 (1) are flagged
    assert 9 in res.outlier_indices
    assert 10 in res.outlier_indices
    assert res.lower_threshold > 1
    assert res.upper_threshold < 100


def test_iqr_detector_with_clean_data():
    data = pd.Series([10, 11, 10, 12, 11, 10, 11, 12])
    detector = IQRAnomalyDetector(factor=1.5)
    res = detector.detect(data)

    assert not res.has_anomalies
    assert res.outlier_count == 0


def test_iqr_detector_small_sample():
    data = pd.Series([1, 2])
    detector = IQRAnomalyDetector(factor=1.5)
    res = detector.detect(data)

    assert res.outlier_count == 0


def test_zscore_detector_with_extreme_deviation():
    # 30 standard normal points + 1 massive spike (+10 stds)
    np.random.seed(42)
    base = np.random.normal(loc=10, scale=1, size=40).tolist()
    base.append(35.0)  # Extreme outlier
    series = pd.Series(base)

    detector = ZScoreAnomalyDetector(threshold=3.0)
    res = detector.detect(series, column_name="z_test")

    assert res.has_anomalies
    assert 40 in res.outlier_indices
    assert res.summary_stats["mean"] > 10.0


def test_zscore_zero_variance():
    series = pd.Series([5.0, 5.0, 5.0, 5.0])
    detector = ZScoreAnomalyDetector(threshold=3.0)
    res = detector.detect(series)

    assert not res.has_anomalies
    assert res.summary_stats["std"] == 0.0
