"""
Executive Audit Reporting Engine.
Produces responsive standalone HTML quality dashboards and GitHub Markdown summaries.
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import pandas as pd

from .schema import Severity
from .validator import ValidationSummary
from .cleaner import SanitizationSummary


class AuditReporter:
    """Generates visual executive audit reports and machine-readable data quality summaries."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_html_report(
        self,
        audit: ValidationSummary,
        sanitization: SanitizationSummary,
        filename: str = "data_quality_audit_report.html"
    ) -> Path:
        """Renders an interactive, responsive standalone HTML audit dashboard."""
        out_path = self.output_dir / filename
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Top 15 sample issues for display
        sample_issues = audit.issues[:15]

        # Anomaly rows
        anomaly_rows = []
        for anom in audit.anomalies:
            anomaly_rows.append(f"""
            <tr>
                <td><strong>{anom.column}</strong></td>
                <td><span class="badge method">{anom.method}</span></td>
                <td>{anom.outlier_count}</td>
                <td>{anom.outlier_percentage}%</td>
                <td>[{anom.lower_threshold}, {anom.upper_threshold}]</td>
            </tr>
            """)

        # Completeness rows
        comp_rows = []
        for col, pct in audit.column_completeness.items():
            status_color = "#10b981" if pct == 100.0 else ("#f59e0b" if pct >= 95.0 else "#ef4444")
            comp_rows.append(f"""
            <div class="comp-item">
                <div class="comp-header">
                    <span>{col}</span>
                    <strong>{pct}%</strong>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {pct}%; background-color: {status_color};"></div>
                </div>
            </div>
            """)

        # Issues rows
        issue_rows = []
        for issue in sample_issues:
            sev_class = "critical" if issue.severity == Severity.CRITICAL else "warning"
            row_str = f"Row #{issue.row_index}" if issue.row_index is not None else "Global / Batch"
            val_str = str(issue.value) if issue.value is not None else "<em>NULL / Missing</em>"
            issue_rows.append(f"""
            <tr>
                <td><span class="badge {sev_class}">{issue.severity.value}</span></td>
                <td>{issue.column}</td>
                <td><code>{issue.rule}</code></td>
                <td>{val_str}</td>
                <td>{issue.message}</td>
                <td>{row_str}</td>
            </tr>
            """)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Clinical Data Quality Audit Dashboard</title>
<style>
    :root {{
        --primary: #0f172a;
        --secondary: #1e293b;
        --accent: #2563eb;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --bg: #f8fafc;
        --card: #ffffff;
        --text: #334155;
        --border: #e2e8f0;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    body {{ background: var(--bg); color: var(--text); padding: 24px; line-height: 1.5; }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    
    header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid var(--border); }}
    .title-group h1 {{ font-size: 24px; color: var(--primary); font-weight: 700; }}
    .title-group p {{ color: #64748b; font-size: 14px; margin-top: 4px; }}
    .badge-meta {{ background: #e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 6px; font-size: 13px; font-weight: 600; }}

    .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 28px; }}
    .kpi-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
    .kpi-title {{ font-size: 13px; text-transform: uppercase; color: #64748b; font-weight: 600; letter-spacing: 0.5px; }}
    .kpi-value {{ font-size: 32px; font-weight: 800; margin: 8px 0; color: var(--primary); }}
    .kpi-value.green {{ color: var(--success); }}
    .kpi-value.red {{ color: var(--danger); }}
    .kpi-sub {{ font-size: 12px; color: #64748b; }}

    .grid-two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 28px; }}
    @media(max-width: 768px) {{ .grid-two {{ grid-template-columns: 1fr; }} }}

    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 24px; }}
    .card h2 {{ font-size: 17px; font-weight: 700; color: var(--primary); margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }}

    .comp-item {{ margin-bottom: 12px; }}
    .comp-header {{ display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; margin-bottom: 4px; }}
    .progress-bar {{ height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; }}
    .progress-fill {{ height: 100%; border-radius: 4px; }}

    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
    th {{ background: #f1f5f9; color: var(--primary); font-weight: 700; }}
    tr:hover {{ background: #f8fafc; }}

    .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; }}
    .badge.critical {{ background: #fee2e2; color: #991b1b; }}
    .badge.warning {{ background: #fef3c7; color: #92400e; }}
    .badge.method {{ background: #e0f2fe; color: #0369a1; }}
    
    .recom-box {{ background: #eff6ff; border-left: 4px solid var(--accent); padding: 16px; border-radius: 6px; font-size: 14px; margin-top: 12px; }}
    .recom-box ul {{ padding-left: 20px; margin-top: 8px; }}
    .recom-box li {{ margin-bottom: 4px; }}
</style>
</head>
<body>
<div class="container">
    <header>
        <div class="title-group">
            <h1>Clinical Data Quality & Anomaly Detection Audit</h1>
            <p>Automated Regulatory & Statistical Pipeline Report • Generated on {timestamp}</p>
        </div>
        <div class="badge-meta">Pipeline Status: AUDIT COMPLETE</div>
    </header>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-title">Data Quality Score</div>
            <div class="kpi-value green">{audit.data_quality_score}%</div>
            <div class="kpi-sub">Composite reliability metric</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Total Records</div>
            <div class="kpi-value">{audit.total_rows:,}</div>
            <div class="kpi-sub">Ingested patient batch</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Clean & Approved</div>
            <div class="kpi-value green">{sanitization.clean_rows:,}</div>
            <div class="kpi-sub">{round((sanitization.clean_rows/audit.total_rows)*100, 1)}% acceptance rate</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Quarantined Records</div>
            <div class="kpi-value red">{sanitization.quarantined_rows:,}</div>
            <div class="kpi-sub">Isolated for clinical safety</div>
        </div>
    </div>

    <div class="grid-two">
        <div class="card">
            <h2>Field Completeness Rates</h2>
            {''.join(comp_rows)}
        </div>
        <div class="card">
            <h2>Biomarker Outlier Detection</h2>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Method</th>
                        <th>Outliers</th>
                        <th>Rate</th>
                        <th>Valid Boundary</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(anomaly_rows)}
                </tbody>
            </table>
        </div>
    </div>

    <div class="card">
        <h2>Defect Log Sample (Top 15 Flagged Issues)</h2>
        <table>
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>Column</th>
                    <th>Rule Code</th>
                    <th>Observed Value</th>
                    <th>Audit Message</th>
                    <th>Record</th>
                </tr>
            </thead>
            <tbody>
                {''.join(issue_rows)}
            </tbody>
        </table>
    </div>

    <div class="card">
        <h2>Clinical Operations Action Plan</h2>
        <div class="recom-box">
            <strong>Recommended Governance Steps:</strong>
            <ul>
                <li><strong>Quarantine Triage:</strong> Review <code>data/processed/quarantined_records.csv</code> with Data Management to resolve unconsented subjects and ID collisions.</li>
                <li><strong>Imputation Sign-off:</strong> {sanitization.imputed_fields_count} benign laboratory missing fields were imputed via group-wise cancer type medians.</li>
                <li><strong>Biomarker Outliers:</strong> Patients exhibiting extreme leukocytosis (WBC > 50 k/uL) should be routed to safety review for acute reaction assessment.</li>
            </ul>
        </div>
    </div>
</div>
</body>
</html>
"""
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return out_path

    def generate_markdown_summary(
        self,
        audit: ValidationSummary,
        sanitization: SanitizationSummary,
        filename: str = "audit_summary.md"
    ) -> Path:
        """Constructs a clean Markdown summary report optimized for GitHub previews."""
        out_path = self.output_dir / filename
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        md_content = f"""# Clinical Data Quality & Anomaly Detection Summary Report

* **Generated At:** `{timestamp}`
* **Dataset Size:** `{audit.total_rows:,} records` | `{audit.total_columns} columns`
* **Overall Data Quality Score:** **`{audit.data_quality_score}%`**

---

## 📊 Key Quality Performance Indicators

| KPI Metric | Value | Proportion / Target |
|---|:---:|:---:|
| **Total Ingested Records** | `{audit.total_rows:,}` | 100% |
| **Clean & Validated Records** | `{sanitization.clean_rows:,}` | **{round((sanitization.clean_rows / audit.total_rows) * 100, 1)}%** |
| **Quarantined Records (Critical)** | `{sanitization.quarantined_rows:,}` | **{round((sanitization.quarantined_rows / audit.total_rows) * 100, 1)}%** |
| **Critical Rule Violations** | `{audit.critical_issues_count:,}` | *Blocks downstream models* |
| **Warning Anomalies (IQR / Z-Score)** | `{audit.warning_issues_count:,}` | *Routed for review* |
| **Imputed Laboratory Fields** | `{sanitization.imputed_fields_count:,}` | *Group-wise median imputed* |
| **Normalized Text Representations** | `{sanitization.normalized_fields_count:,}` | *Canonical title-casing* |

---

## 🚫 Quarantine Breakdown by Failure Mode

The following critical defects prevented records from advancing to the clean analytical pipeline:

| Failure Mode | Trigger Count | Description |
|---|:---:|---|
"""
        for rule, count in sanitization.quarantine_reasons_breakdown.items():
            md_content += f"| `{rule}` | `{count}` | Critical constraint breach |\n"

        md_content += """
---

## 🔬 Statistical Biomarker Anomaly Detection (IQR vs. Z-Score)

| Biomarker Metric | Method | Outlier Count | Outlier % | Valid Empirical Thresholds |
|---|---|:---:|:---:|---|
"""
        for anom in audit.anomalies:
            md_content += f"| **{anom.column}** | `{anom.method}` | `{anom.outlier_count}` | `{anom.outlier_percentage}%` | `[{anom.lower_threshold}, {anom.upper_threshold}]` |\n"

        md_content += f"""
---

## 💡 Engineering & Clinical Actions Taken
1. **Quarantine Routing:** Isolated records with unconsented entries, corrupted IDs, or physiological impossibilities into `data/processed/quarantined_records.csv`.
2. **Deterministic Imputation:** Solved non-critical missing lab values using median group imputation grouped by cancer histology.
3. **Artifact Generation:** Rendered full interactive executive HTML dashboard to `reports/data_quality_audit_report.html`.
"""
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return out_path
