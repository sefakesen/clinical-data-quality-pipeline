"""
Realistic Synthetic Clinical Trial Patient Cohort Generator.
Injects controlled clinical anomalies, missingness, and format corruptions for pipeline benchmarking.
"""
import random
from typing import Optional
import numpy as np
import pandas as pd


class ClinicalDataGenerator:
    """Generates synthetic multi-center oncology trial patient cohorts."""

    CANCER_TYPES = [
        "Breast Cancer",
        "Non-Small Cell Lung Cancer",
        "Colorectal Cancer",
        "Melanoma",
        "Pancreatic Cancer"
    ]
    STAGES = ["Stage I", "Stage II", "Stage III", "Stage IV"]
    BIOMARKERS = ["Positive", "Negative", "Pending", "Inconclusive"]
    GENDERS = ["Female", "Male", "Non-Binary"]

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def generate(self, n_records: int = 1000) -> pd.DataFrame:
        """Constructs an uncleaned synthetic clinical cohort DataFrame with deliberate anomalies."""
        data = []

        for i in range(1, n_records + 1):
            pid = f"PT-{i:05d}"
            age = int(np.random.normal(loc=58, scale=12))
            gender = random.choices(self.GENDERS, weights=[0.52, 0.44, 0.04])[0]
            cancer = random.choice(self.CANCER_TYPES)
            stage = random.choices(self.STAGES, weights=[0.20, 0.35, 0.30, 0.15])[0]
            biomarker = random.choices(self.BIOMARKERS, weights=[0.45, 0.35, 0.15, 0.05])[0]

            # Realistic physiological lab values
            wbc = round(float(np.random.normal(loc=7.2, scale=1.8)), 2)
            hgb = round(float(np.random.normal(loc=13.8, scale=1.6)), 2)
            creatinine = round(float(np.random.normal(loc=0.92, scale=0.22)), 2)
            bp_systolic = int(np.random.normal(loc=128, scale=16))

            enroll_month = random.randint(1, 10)
            enroll_day = random.randint(1, 28)
            enrollment_date = f"2026-{enroll_month:02d}-{enroll_day:02d}"
            consent_signed = True

            data.append({
                "patient_id": pid,
                "age": age,
                "gender": gender,
                "cancer_type": cancer,
                "stage": stage,
                "biomarker_status": biomarker,
                "white_blood_cell_k_ul": wbc,
                "hemoglobin_g_dl": hgb,
                "creatinine_mg_dl": creatinine,
                "systolic_bp": bp_systolic,
                "consent_signed": consent_signed,
                "enrollment_date": enrollment_date,
            })

        df = pd.DataFrame(data)

        # Deliberately inject controlled real-world defects & edge cases
        # 1. Duplicate Patient IDs (~1.5%)
        dup_indices = random.sample(range(50, n_records), k=15)
        for idx in dup_indices:
            df.at[idx, "patient_id"] = df.at[idx - 10, "patient_id"]

        # 2. Corrupted Patient ID formats (~1%)
        malformed_id_indices = random.sample(range(n_records), k=10)
        for idx in malformed_id_indices:
            df.at[idx, "patient_id"] = f"INVALID_{idx}"

        # 3. Unconsented Trial Records (Critical GCP Violation ~1.5%)
        unconsented_indices = random.sample(range(n_records), k=15)
        for idx in unconsented_indices:
            df.at[idx, "consent_signed"] = False

        # 4. Out-of-bounds Age values (Negative or Extreme > 120 ~1.5%)
        bad_age_indices = random.sample(range(n_records), k=12)
        for idx in bad_age_indices[:6]:
            df.at[idx, "age"] = -abs(int(df.at[idx, "age"]))  # Negative age
        for idx in bad_age_indices[6:]:
            df.at[idx, "age"] = 145  # Incompatible with human lifespan

        # 5. Missing values in Labs and Biomarkers (~4%)
        for col in ["white_blood_cell_k_ul", "creatinine_mg_dl", "biomarker_status"]:
            null_indices = random.sample(range(n_records), k=25)
            for idx in null_indices:
                df.at[idx, col] = np.nan

        # 6. Statistical Outliers in Lab Values (Extreme leukocytosis, severe anemia ~2.5%)
        outlier_indices = random.sample(range(n_records), k=20)
        for idx in outlier_indices[:7]:
            df.at[idx, "white_blood_cell_k_ul"] = round(float(np.random.uniform(55.0, 92.0)), 2)
        for idx in outlier_indices[7:14]:
            df.at[idx, "hemoglobin_g_dl"] = round(float(np.random.uniform(2.1, 4.2)), 2)
        for idx in outlier_indices[14:]:
            df.at[idx, "creatinine_mg_dl"] = round(float(np.random.uniform(6.5, 11.2)), 2)

        # 7. Non-standardized gender representations (f, m, fem ~3%)
        gender_dirty_indices = random.sample(range(n_records), k=30)
        for idx in gender_dirty_indices[:15]:
            df.at[idx, "gender"] = "f" if df.at[idx, "gender"] == "Female" else "m"
        for idx in gender_dirty_indices[15:]:
            df.at[idx, "gender"] = "female" if df.at[idx, "gender"] == "Female" else "male"

        return df
