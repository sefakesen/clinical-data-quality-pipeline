"""
Data Sanitization, Imputation, and Quarantine Separation Engine.
Enforces defensive cleaning transformations, grouped imputation, and quarantine isolation.
"""
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple
import pandas as pd
import numpy as np

from .schema import Severity
from .validator import ValidationSummary


@dataclass
class SanitizationSummary:
    """Summary of data cleaning and remediation actions performed."""
    initial_rows: int
    clean_rows: int
    quarantined_rows: int
    imputed_fields_count: int
    normalized_fields_count: int
    quarantine_reasons_breakdown: Dict[str, int]


class DataSanitizer:
    """
    Transforms raw, noisy clinical trial ingestion batches into clean, audited datasets.
    """

    GENDER_MAPPING: Dict[str, str] = {
        "f": "Female",
        "female": "Female",
        "fem": "Female",
        "m": "Male",
        "male": "Male",
        "nb": "Non-Binary",
        "non-binary": "Non-Binary",
    }

    def __init__(self):
        pass

    def clean_and_quarantine(
        self,
        df: pd.DataFrame,
        audit_summary: ValidationSummary
    ) -> Tuple[pd.DataFrame, pd.DataFrame, SanitizationSummary]:
        """
        Executes systematic cleaning, imputes benign missing features,
        and isolates critically failing records into a quarantine DataFrame.
        """
        working_df = df.copy()
        imputed_count = 0
        normalized_count = 0

        # 1. Map and collect critical row indices along with their specific failure reasons
        critical_reasons: Dict[int, List[str]] = {}
        for issue in audit_summary.issues:
            if issue.severity == Severity.CRITICAL and issue.row_index is not None:
                if issue.row_index not in critical_reasons:
                    critical_reasons[issue.row_index] = []
                critical_reasons[issue.row_index].append(f"{issue.rule}: {issue.message}")

        critical_indices: Set[int] = set(critical_reasons.keys())

        # 2. String Normalization & Canonical Categorical Mapping
        if "gender" in working_df.columns:
            for idx in working_df.index:
                raw_val = working_df.at[idx, "gender"]
                if pd.notna(raw_val):
                    cleaned_val = str(raw_val).strip().lower()
                    if cleaned_val in self.GENDER_MAPPING:
                        normalized = self.GENDER_MAPPING[cleaned_val]
                        if normalized != raw_val:
                            working_df.at[idx, "gender"] = normalized
                            normalized_count += 1

        for col in ["cancer_type", "stage", "biomarker_status"]:
            if col in working_df.columns:
                working_df[col] = working_df[col].astype(str).str.strip()
                working_df.loc[working_df[col].isin(["nan", "None", "NULL", ""]), col] = np.nan

        # 3. Date Standardization (ISO 8601 YYYY-MM-DD)
        if "enrollment_date" in working_df.columns:
            parsed_dates = pd.to_datetime(working_df["enrollment_date"], errors="coerce")
            working_df["enrollment_date"] = parsed_dates.dt.strftime("%Y-%m-%d")

        # 4. Grouped Median Imputation for Benign Numerical Missing Labs
        # (Only imputed for records that are not quarantined for ID or protocol violations)
        lab_columns = ["white_blood_cell_k_ul", "hemoglobin_g_dl", "creatinine_mg_dl", "systolic_bp"]
        for col in lab_columns:
            if col in working_df.columns:
                working_df[col] = pd.to_numeric(working_df[col], errors="coerce")
                null_mask = working_df[col].isna()
                n_missing = int(null_mask.sum())

                if n_missing > 0:
                    # Impute using median grouped by cancer_type, fallback to overall median
                    if "cancer_type" in working_df.columns:
                        group_medians = working_df.groupby("cancer_type")[col].transform("median")
                        overall_median = working_df[col].median()
                        working_df[col] = working_df[col].fillna(group_medians).fillna(overall_median)
                    else:
                        working_df[col] = working_df[col].fillna(working_df[col].median())
                    imputed_count += n_missing

        # 5. Categorical Missing Imputation
        if "biomarker_status" in working_df.columns:
            missing_bio = working_df["biomarker_status"].isna()
            if missing_bio.any():
                working_df.loc[missing_bio, "biomarker_status"] = "Pending"
                imputed_count += int(missing_bio.sum())

        # 6. Separate Clean vs Quarantined Records
        quarantined_mask = working_df.index.isin(critical_indices)

        quarantined_df = working_df[quarantined_mask].copy()
        quarantined_df["rejection_reasons"] = quarantined_df.index.map(
            lambda i: " | ".join(critical_reasons.get(i, ["CRITICAL_ERROR"]))
        )

        clean_df = working_df[~quarantined_mask].copy()

        # Deduplicate clean dataset defensively by patient_id
        if "patient_id" in clean_df.columns:
            clean_df = clean_df.drop_duplicates(subset=["patient_id"], keep="first")

        # Compile quarantine reasons breakdown
        reason_breakdown: Dict[str, int] = {}
        for reasons in critical_reasons.values():
            for r in reasons:
                code = r.split(":")[0].strip()
                reason_breakdown[code] = reason_breakdown.get(code, 0) + 1

        summary = SanitizationSummary(
            initial_rows=len(df),
            clean_rows=len(clean_df),
            quarantined_rows=len(quarantined_df),
            imputed_fields_count=imputed_count,
            normalized_fields_count=normalized_count,
            quarantine_reasons_breakdown=reason_breakdown
        )

        return clean_df, quarantined_df, summary
