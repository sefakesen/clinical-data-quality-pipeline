"""
Unit tests for the ClinicalDataValidator quality engine.
"""
import pandas as pd
from src.validator import ClinicalDataValidator
from src.schema import Severity


def test_validator_detects_unconsented_records():
    df = pd.DataFrame([{
        "patient_id": "PT-00001",
        "age": 45,
        "gender": "Female",
        "cancer_type": "Breast Cancer",
        "stage": "Stage II",
        "biomarker_status": "Positive",
        "white_blood_cell_k_ul": 6.5,
        "hemoglobin_g_dl": 13.5,
        "creatinine_mg_dl": 0.9,
        "systolic_bp": 120,
        "consent_signed": False,  # Regulatory GCP violation
        "enrollment_date": "2026-05-10"
    }])

    validator = ClinicalDataValidator()
    summary = validator.audit(df)

    assert summary.critical_issues_count >= 1
    unconsented = [i for i in summary.issues if i.rule == "UNCONSENTED_TRIAL_RECORD"]
    assert len(unconsented) == 1
    assert unconsented[0].severity == Severity.CRITICAL


def test_validator_detects_duplicate_patient_ids():
    df = pd.DataFrame([
        {
            "patient_id": "PT-00001",
            "age": 50,
            "gender": "Male",
            "cancer_type": "Melanoma",
            "stage": "Stage I",
            "biomarker_status": "Negative",
            "white_blood_cell_k_ul": 7.0,
            "hemoglobin_g_dl": 14.0,
            "creatinine_mg_dl": 0.8,
            "systolic_bp": 125,
            "consent_signed": True,
            "enrollment_date": "2026-06-01"
        },
        {
            "patient_id": "PT-00001",  # Duplicate collision
            "age": 52,
            "gender": "Male",
            "cancer_type": "Melanoma",
            "stage": "Stage I",
            "biomarker_status": "Negative",
            "white_blood_cell_k_ul": 7.1,
            "hemoglobin_g_dl": 14.2,
            "creatinine_mg_dl": 0.85,
            "systolic_bp": 130,
            "consent_signed": True,
            "enrollment_date": "2026-06-02"
        }
    ])

    validator = ClinicalDataValidator()
    summary = validator.audit(df)

    dup_issues = [i for i in summary.issues if i.rule == "DUPLICATE_PATIENT_ID"]
    assert len(dup_issues) == 2


def test_validator_detects_physiological_violations():
    df = pd.DataFrame([{
        "patient_id": "PT-00002",
        "age": -10,  # Negative age violation
        "gender": "Female",
        "cancer_type": "Colorectal Cancer",
        "stage": "Stage III",
        "biomarker_status": "Positive",
        "white_blood_cell_k_ul": 6.0,
        "hemoglobin_g_dl": 12.0,
        "creatinine_mg_dl": 0.9,
        "systolic_bp": 120,
        "consent_signed": True,
        "enrollment_date": "2026-05-12"
    }])

    validator = ClinicalDataValidator()
    summary = validator.audit(df)

    age_issues = [i for i in summary.issues if i.column == "age" and i.rule == "PHYSIOLOGICAL_LIMIT_VIOLATION"]
    assert len(age_issues) == 1
    assert age_issues[0].severity == Severity.CRITICAL
