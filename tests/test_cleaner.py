"""
Unit tests for data sanitization, imputation, and quarantine routing.
"""
import pandas as pd
import numpy as np

from src.cleaner import DataSanitizer
from src.validator import ClinicalDataValidator


def test_cleaner_gender_normalization():
    df = pd.DataFrame([{
        "patient_id": "PT-00001",
        "age": 40,
        "gender": "f",  # Unstandardized lowercase abbreviation
        "cancer_type": "Breast Cancer",
        "stage": "Stage I",
        "biomarker_status": "Positive",
        "white_blood_cell_k_ul": 6.5,
        "hemoglobin_g_dl": 13.0,
        "creatinine_mg_dl": 0.8,
        "systolic_bp": 115,
        "consent_signed": True,
        "enrollment_date": "2026-04-15"
    }])

    validator = ClinicalDataValidator()
    summary = validator.audit(df)

    cleaner = DataSanitizer()
    clean_df, quarantined_df, stats = cleaner.clean_and_quarantine(df, summary)

    assert len(clean_df) == 1
    assert clean_df.iloc[0]["gender"] == "Female"
    assert stats.normalized_fields_count >= 1


def test_cleaner_imputes_benign_missing_labs():
    df = pd.DataFrame([
        {
            "patient_id": "PT-00001",
            "age": 40,
            "gender": "Female",
            "cancer_type": "Melanoma",
            "stage": "Stage I",
            "biomarker_status": "Positive",
            "white_blood_cell_k_ul": 6.0,
            "hemoglobin_g_dl": 14.0,
            "creatinine_mg_dl": 0.8,
            "systolic_bp": 120,
            "consent_signed": True,
            "enrollment_date": "2026-04-15"
        },
        {
            "patient_id": "PT-00002",
            "age": 42,
            "gender": "Female",
            "cancer_type": "Melanoma",
            "stage": "Stage I",
            "biomarker_status": "Positive",
            "white_blood_cell_k_ul": np.nan,  # Missing lab
            "hemoglobin_g_dl": 14.0,
            "creatinine_mg_dl": 0.8,
            "systolic_bp": 120,
            "consent_signed": True,
            "enrollment_date": "2026-04-16"
        }
    ])

    validator = ClinicalDataValidator()
    summary = validator.audit(df)

    cleaner = DataSanitizer()
    clean_df, quarantined_df, stats = cleaner.clean_and_quarantine(df, summary)

    assert len(clean_df) == 2
    # Verify the missing WBC was imputed with median (6.0)
    assert not clean_df["white_blood_cell_k_ul"].isna().any()
    assert clean_df.loc[1, "white_blood_cell_k_ul"] == 6.0
    assert stats.imputed_fields_count >= 1


def test_cleaner_quarantines_critical_failures():
    df = pd.DataFrame([
        {
            "patient_id": "PT-00001",
            "age": 50,
            "gender": "Male",
            "cancer_type": "Pancreatic Cancer",
            "stage": "Stage IV",
            "biomarker_status": "Negative",
            "white_blood_cell_k_ul": 8.0,
            "hemoglobin_g_dl": 12.0,
            "creatinine_mg_dl": 1.1,
            "systolic_bp": 130,
            "consent_signed": True,
            "enrollment_date": "2026-01-20"
        },
        {
            "patient_id": "PT-00002",
            "age": -5,  # Critical invalid age
            "gender": "Male",
            "cancer_type": "Pancreatic Cancer",
            "stage": "Stage IV",
            "biomarker_status": "Negative",
            "white_blood_cell_k_ul": 8.0,
            "hemoglobin_g_dl": 12.0,
            "creatinine_mg_dl": 1.1,
            "systolic_bp": 130,
            "consent_signed": False,  # Critical unconsented
            "enrollment_date": "2026-01-20"
        }
    ])

    validator = ClinicalDataValidator()
    summary = validator.audit(df)

    cleaner = DataSanitizer()
    clean_df, quarantined_df, stats = cleaner.clean_and_quarantine(df, summary)

    assert len(clean_df) == 1
    assert len(quarantined_df) == 1
    assert quarantined_df.iloc[0]["patient_id"] == "PT-00002"
    assert "rejection_reasons" in quarantined_df.columns
