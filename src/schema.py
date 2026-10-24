"""
Data schema contracts, domain boundaries, and validation severity definitions.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class Severity(Enum):
    """Validation issue severity levels."""
    CRITICAL = "CRITICAL"  # Data corruption or protocol violation: must be quarantined.
    WARNING = "WARNING"    # Statistical outlier or minor deviation: requires clinical review.
    INFO = "INFO"          # Imputed field or benign normalization.


@dataclass(frozen=True)
class NumericBounds:
    """Defines valid physiological and clinical trial measurement limits."""
    min_value: float
    max_value: float
    unit: str
    normal_range: Tuple[float, float]


@dataclass(frozen=True)
class FieldConstraint:
    """Constraint definition for a single column in the clinical dataset."""
    name: str
    dtype: str
    required: bool = True
    allowed_values: Optional[Set[Any]] = None
    bounds: Optional[NumericBounds] = None
    regex_pattern: Optional[str] = None
    description: str = ""


# Reference ranges derived from standard adult clinical laboratory guidelines
CLINICAL_FIELDS: Dict[str, FieldConstraint] = {
    "patient_id": FieldConstraint(
        name="patient_id",
        dtype="string",
        required=True,
        regex_pattern=r"^PT-\d{5}$",
        description="Unique patient identifier formatted as PT-XXXXX"
    ),
    "age": FieldConstraint(
        name="age",
        dtype="integer",
        required=True,
        bounds=NumericBounds(min_value=18, max_value=95, unit="years", normal_range=(18, 80)),
        description="Adult patient age in completed years (clinical trial inclusion >= 18)"
    ),
    "gender": FieldConstraint(
        name="gender",
        dtype="category",
        required=True,
        allowed_values={"Female", "Male", "Non-Binary"},
        description="Patient self-identified gender"
    ),
    "cancer_type": FieldConstraint(
        name="cancer_type",
        dtype="category",
        required=True,
        allowed_values={
            "Breast Cancer",
            "Non-Small Cell Lung Cancer",
            "Colorectal Cancer",
            "Melanoma",
            "Pancreatic Cancer"
        },
        description="Primary histological cancer diagnosis"
    ),
    "stage": FieldConstraint(
        name="stage",
        dtype="category",
        required=True,
        allowed_values={"Stage I", "Stage II", "Stage III", "Stage IV"},
        description="TNM clinical staging index"
    ),
    "biomarker_status": FieldConstraint(
        name="biomarker_status",
        dtype="category",
        required=True,
        allowed_values={"Positive", "Negative", "Pending", "Inconclusive"},
        description="Target genomic biomarker status (e.g. HER2, EGFR, KRAS)"
    ),
    "white_blood_cell_k_ul": FieldConstraint(
        name="white_blood_cell_k_ul",
        dtype="float",
        required=True,
        bounds=NumericBounds(min_value=1.5, max_value=40.0, unit="k/uL", normal_range=(4.0, 11.0)),
        description="Total leukocyte count per microliter"
    ),
    "hemoglobin_g_dl": FieldConstraint(
        name="hemoglobin_g_dl",
        dtype="float",
        required=True,
        bounds=NumericBounds(min_value=5.0, max_value=22.0, unit="g/dL", normal_range=(11.5, 17.5)),
        description="Blood hemoglobin concentration"
    ),
    "creatinine_mg_dl": FieldConstraint(
        name="creatinine_mg_dl",
        dtype="float",
        required=True,
        bounds=NumericBounds(min_value=0.2, max_value=6.0, unit="mg/dL", normal_range=(0.5, 1.3)),
        description="Serum creatinine level indicating renal clearance"
    ),
    "systolic_bp": FieldConstraint(
        name="systolic_bp",
        dtype="integer",
        required=True,
        bounds=NumericBounds(min_value=70, max_value=230, unit="mmHg", normal_range=(90, 140)),
        description="Resting systolic blood pressure measurement"
    ),
    "consent_signed": FieldConstraint(
        name="consent_signed",
        dtype="boolean",
        required=True,
        allowed_values={True, False},
        description="GCP-compliant informed consent signed status"
    ),
    "enrollment_date": FieldConstraint(
        name="enrollment_date",
        dtype="date",
        required=True,
        regex_pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Trial enrollment date formatted as YYYY-MM-DD"
    ),
}
