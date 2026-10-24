"""
Core Validation Engine for Clinical and Healthcare Datasets.
Evaluates completeness, formatting, domain constraints, duplicates, and protocol rules.
"""
from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Set
import pandas as pd

from .schema import CLINICAL_FIELDS, FieldConstraint, Severity
from .anomaly import IQRAnomalyDetector, ZScoreAnomalyDetector, AnomalyDetectionResult


@dataclass
class ValidationIssue:
    """Individual data quality defect identified during an audit."""
    row_index: Optional[int]
    column: str
    value: Any
    rule: str
    severity: Severity
    message: str


@dataclass
class ValidationSummary:
    """Consolidated audit metrics and quality scorecard."""
    total_rows: int
    total_columns: int
    clean_rows_count: int
    quarantined_rows_count: int
    critical_issues_count: int
    warning_issues_count: int
    data_quality_score: float
    column_completeness: Dict[str, float]
    issues: List[ValidationIssue]
    anomalies: List[AnomalyDetectionResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return round((self.clean_rows_count / self.total_rows) * 100, 2)


class ClinicalDataValidator:
    """
    Automated validator executing systematic data quality audits against clinical schemas.
    """

    def __init__(self, constraints: Optional[Dict[str, FieldConstraint]] = None):
        self.constraints = constraints or CLINICAL_FIELDS
        self.iqr_detector = IQRAnomalyDetector(factor=1.5)
        self.zscore_detector = ZScoreAnomalyDetector(threshold=3.0)

    def audit(self, df: pd.DataFrame) -> ValidationSummary:
        """Runs the complete suite of quality checks over the given clinical DataFrame."""
        issues: List[ValidationIssue] = []
        critical_row_indices: Set[int] = set()

        total_rows, total_cols = df.shape
        completeness_map: Dict[str, float] = {}

        # 1. Column Completeness and Missing Value Audits
        for col_name, constraint in self.constraints.items():
            if col_name not in df.columns:
                issues.append(ValidationIssue(
                    row_index=None,
                    column=col_name,
                    value=None,
                    rule="MISSING_COLUMN",
                    severity=Severity.CRITICAL,
                    message=f"Mandatory schema column '{col_name}' is entirely missing from dataset."
                ))
                completeness_map[col_name] = 0.0
                continue

            null_series = df[col_name].isna() | (df[col_name].astype(str).str.strip().isin(["", "nan", "None", "NULL"]))
            null_count = int(null_series.sum())
            comp_pct = round(((total_rows - null_count) / total_rows) * 100, 2) if total_rows > 0 else 0.0
            completeness_map[col_name] = comp_pct

            if constraint.required and null_count > 0:
                for idx in df[null_series].index:
                    issues.append(ValidationIssue(
                        row_index=int(idx),
                        column=col_name,
                        value=None,
                        rule="REQUIRED_FIELD_NULL",
                        severity=Severity.CRITICAL if col_name in ["patient_id", "consent_signed", "age"] else Severity.WARNING,
                        message=f"Missing value detected in required field '{col_name}'."
                    ))
                    if col_name in ["patient_id", "consent_signed", "age"]:
                        critical_row_indices.add(int(idx))

        # 2. Patient ID Format & Duplicate Integrity
        if "patient_id" in df.columns:
            pid_series = df["patient_id"].astype(str).str.strip()
            pattern = re.compile(self.constraints["patient_id"].regex_pattern or r"^PT-\d{5}$")
            
            for idx, pid in pid_series.items():
                if pd.isna(pid) or not pattern.match(pid):
                    issues.append(ValidationIssue(
                        row_index=int(idx),
                        column="patient_id",
                        value=pid,
                        rule="INVALID_IDENTIFIER_FORMAT",
                        severity=Severity.CRITICAL,
                        message=f"Patient ID '{pid}' does not conform to standardized pattern 'PT-XXXXX'."
                    ))
                    critical_row_indices.add(int(idx))

            # Duplicate ID check
            duplicated_mask = pid_series.duplicated(keep=False) & pid_series.ne("")
            if duplicated_mask.any():
                for idx, pid in pid_series[duplicated_mask].items():
                    issues.append(ValidationIssue(
                        row_index=int(idx),
                        column="patient_id",
                        value=pid,
                        rule="DUPLICATE_PATIENT_ID",
                        severity=Severity.CRITICAL,
                        message=f"Duplicate patient identifier collision detected for '{pid}'."
                    ))
                    critical_row_indices.add(int(idx))

        # 3. Categorical Integrity Verification
        categorical_fields = ["gender", "cancer_type", "stage", "biomarker_status"]
        for col in categorical_fields:
            if col in df.columns:
                allowed = self.constraints[col].allowed_values or set()
                for idx, val in df[col].items():
                    if pd.notna(val) and str(val).strip() not in allowed:
                        issues.append(ValidationIssue(
                            row_index=int(idx),
                            column=col,
                            value=val,
                            rule="INVALID_CATEGORICAL_VALUE",
                            severity=Severity.WARNING,
                            message=f"Value '{val}' in '{col}' is outside approved clinical ontology {allowed}."
                        ))

        # 4. Numerical Range and Physiological Boundary Audits
        numeric_fields = ["age", "white_blood_cell_k_ul", "hemoglobin_g_dl", "creatinine_mg_dl", "systolic_bp"]
        for col in numeric_fields:
            if col in df.columns:
                bounds = self.constraints[col].bounds
                if not bounds:
                    continue

                numeric_vals = pd.to_numeric(df[col], errors="coerce")
                for idx, val in numeric_vals.items():
                    if pd.isna(val) and pd.notna(df.at[idx, col]):
                        issues.append(ValidationIssue(
                            row_index=int(idx),
                            column=col,
                            value=df.at[idx, col],
                            rule="NON_NUMERIC_TYPE_ERROR",
                            severity=Severity.CRITICAL,
                            message=f"Non-numeric value '{df.at[idx, col]}' found in metric column '{col}'."
                        ))
                        critical_row_indices.add(int(idx))
                    elif pd.notna(val):
                        if val < bounds.min_value or val > bounds.max_value:
                            is_critical = col == "age" or val < 0
                            issues.append(ValidationIssue(
                                row_index=int(idx),
                                column=col,
                                value=val,
                                rule="PHYSIOLOGICAL_LIMIT_VIOLATION",
                                severity=Severity.CRITICAL if is_critical else Severity.WARNING,
                                message=f"Value {val} {bounds.unit} breaches physiological boundary [{bounds.min_value}, {bounds.max_value}]."
                            ))
                            if is_critical:
                                critical_row_indices.add(int(idx))

        # 5. Protocol & Business Logic Enforcement
        if "consent_signed" in df.columns:
            for idx, val in df["consent_signed"].items():
                # GCP compliance: clinical trial data cannot be utilized without affirmative signed consent
                if str(val).lower() in ["false", "0", "no", "none"]:
                    issues.append(ValidationIssue(
                        row_index=int(idx),
                        column="consent_signed",
                        value=val,
                        rule="UNCONSENTED_TRIAL_RECORD",
                        severity=Severity.CRITICAL,
                        message="Patient record lacks verified informed consent signature (Regulatory GCP violation)."
                    ))
                    critical_row_indices.add(int(idx))

        # 6. Statistical Anomaly Detection (IQR & Z-Score on Lab Metrics)
        anomalies: List[AnomalyDetectionResult] = []
        for col in ["white_blood_cell_k_ul", "hemoglobin_g_dl", "creatinine_mg_dl"]:
            if col in df.columns:
                res_iqr = self.iqr_detector.detect(df[col])
                res_z = self.zscore_detector.detect(df[col])
                anomalies.extend([res_iqr, res_z])

                # Log statistical warnings for IQR outliers
                for idx in res_iqr.outlier_indices:
                    issues.append(ValidationIssue(
                        row_index=int(idx),
                        column=col,
                        value=df.at[idx, col],
                        rule="STATISTICAL_IQR_OUTLIER",
                        severity=Severity.WARNING,
                        message=f"Statistical outlier detected by IQR (Thresholds: [{res_iqr.lower_threshold}, {res_iqr.upper_threshold}])."
                    ))

        # 7. Quality Scorecard Computation
        critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        warning_count = sum(1 for i in issues if i.severity == Severity.WARNING)

        quarantined_count = len(critical_row_indices)
        clean_count = max(0, total_rows - quarantined_count)

        # Weighted quality scoring: Critical penalty = 2.5%, Warning penalty = 0.5% normalized to rows
        penalty = ((critical_count * 2.5) + (warning_count * 0.5)) / max(1, total_rows) * 10
        quality_score = max(0.0, min(100.0, round(100.0 - penalty, 2)))

        return ValidationSummary(
            total_rows=total_rows,
            total_columns=total_cols,
            clean_rows_count=clean_count,
            quarantined_rows_count=quarantined_count,
            critical_issues_count=critical_count,
            warning_issues_count=warning_count,
            data_quality_score=quality_score,
            column_completeness=completeness_map,
            issues=issues,
            anomalies=anomalies
        )
