"""
Unit tests for clinical schema definitions and constraints.
"""
from src.schema import CLINICAL_FIELDS, Severity, NumericBounds


def test_schema_field_presence():
    required_keys = [
        "patient_id",
        "age",
        "gender",
        "cancer_type",
        "stage",
        "biomarker_status",
        "white_blood_cell_k_ul",
        "hemoglobin_g_dl",
        "creatinine_mg_dl",
        "consent_signed"
    ]
    for key in required_keys:
        assert key in CLINICAL_FIELDS
        assert CLINICAL_FIELDS[key].required


def test_numeric_bounds():
    age_bounds = CLINICAL_FIELDS["age"].bounds
    assert isinstance(age_bounds, NumericBounds)
    assert age_bounds.min_value == 18
    assert age_bounds.max_value == 95

    wbc_bounds = CLINICAL_FIELDS["white_blood_cell_k_ul"].bounds
    assert wbc_bounds.min_value < wbc_bounds.normal_range[0]
    assert wbc_bounds.max_value > wbc_bounds.normal_range[1]
