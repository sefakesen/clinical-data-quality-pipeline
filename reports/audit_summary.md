# Clinical Data Quality & Anomaly Detection Summary Report

* **Generated At:** `2026-10-25 02:41:36`
* **Dataset Size:** `1,000 records` | `12 columns`
* **Overall Data Quality Score:** **`97.47%`**

---

## 📊 Key Quality Performance Indicators

| KPI Metric | Value | Proportion / Target |
|---|:---:|:---:|
| **Total Ingested Records** | `1,000` | 100% |
| **Clean & Validated Records** | `934` | **93.4%** |
| **Quarantined Records (Critical)** | `66` | **6.6%** |
| **Critical Rule Violations** | `68` | *Blocks downstream models* |
| **Warning Anomalies (IQR / Z-Score)** | `166` | *Routed for review* |
| **Imputed Laboratory Fields** | `75` | *Group-wise median imputed* |
| **Normalized Text Representations** | `30` | *Canonical title-casing* |

---

## 🚫 Quarantine Breakdown by Failure Mode

The following critical defects prevented records from advancing to the clean analytical pipeline:

| Failure Mode | Trigger Count | Description |
|---|:---:|---|
| `INVALID_IDENTIFIER_FORMAT` | `10` | Critical constraint breach |
| `UNCONSENTED_TRIAL_RECORD` | `15` | Critical constraint breach |
| `DUPLICATE_PATIENT_ID` | `29` | Critical constraint breach |
| `PHYSIOLOGICAL_LIMIT_VIOLATION` | `14` | Critical constraint breach |

---

## 🔬 Statistical Biomarker Anomaly Detection (IQR vs. Z-Score)

| Biomarker Metric | Method | Outlier Count | Outlier % | Valid Empirical Thresholds |
|---|---|:---:|:---:|---|
| **white_blood_cell_k_ul** | `IQR(factor=1.5)` | `15` | `1.5%` | `[2.1575, 12.1775]` |
| **white_blood_cell_k_ul** | `ZScore(threshold=3.0)` | `7` | `0.7%` | `[-9.1165, 24.3262]` |
| **hemoglobin_g_dl** | `IQR(factor=1.5)` | `17` | `1.7%` | `[9.445, 18.045]` |
| **hemoglobin_g_dl** | `ZScore(threshold=3.0)` | `7` | `0.7%` | `[8.2455, 19.2233]` |
| **creatinine_mg_dl** | `IQR(factor=1.5)` | `9` | `0.9%` | `[0.345, 1.505]` |
| **creatinine_mg_dl** | `ZScore(threshold=3.0)` | `6` | `0.6%` | `[-1.0417, 2.9831]` |

---

## 💡 Engineering & Clinical Actions Taken
1. **Quarantine Routing:** Isolated records with unconsented entries, corrupted IDs, or physiological impossibilities into `data/processed/quarantined_records.csv`.
2. **Deterministic Imputation:** Solved non-critical missing lab values using median group imputation grouped by cancer histology.
3. **Artifact Generation:** Rendered full interactive executive HTML dashboard to `reports/data_quality_audit_report.html`.
