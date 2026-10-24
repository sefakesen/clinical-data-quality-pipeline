"""
Main Entrypoint and Pipeline CLI Runner for the Clinical Data Quality Engine.
Usage:
    python main.py [--generate] [--audit] [--clean] [--report] [--all]
"""
import argparse
from pathlib import Path
import sys
import pandas as pd

# Ensure UTF-8 output handling in diverse terminal environments
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.generator import ClinicalDataGenerator
from src.validator import ClinicalDataValidator
from src.cleaner import DataSanitizer
from src.reporter import AuditReporter


BASE_DIR = Path(__file__).resolve().parent
DATA_RAW = BASE_DIR / "data" / "raw" / "patient_trial_records_raw.csv"
DATA_CLEAN = BASE_DIR / "data" / "processed" / "clean_patient_records.csv"
DATA_QUARANTINE = BASE_DIR / "data" / "processed" / "quarantined_records.csv"
REPORTS_DIR = BASE_DIR / "reports"


def run_pipeline(
    do_generate: bool = False,
    do_audit: bool = True,
    do_clean: bool = True,
    do_report: bool = True,
    n_records: int = 1000
):
    print("=" * 70)
    print("[*] CLINICAL DATA QUALITY & ANOMALY DETECTION ENGINE")
    print("=" * 70)

    # 1. Generation Step
    if do_generate or not DATA_RAW.exists():
        print(f"\n[1/4] Generating {n_records:,} synthetic clinical records with controlled defects...")
        generator = ClinicalDataGenerator(seed=42)
        raw_df = generator.generate(n_records=n_records)
        DATA_RAW.parent.mkdir(parents=True, exist_ok=True)
        raw_df.to_csv(DATA_RAW, index=False)
        print(f"      [OK] Raw dataset saved to: {DATA_RAW}")
    else:
        print(f"\n[1/4] Loading existing raw dataset from: {DATA_RAW}")
        raw_df = pd.read_csv(DATA_RAW)

    # 2. Audit & Anomaly Detection Step
    validator = ClinicalDataValidator()
    print(f"\n[2/4] Executing comprehensive quality validation suite...")
    audit_summary = validator.audit(raw_df)
    print(f"      [OK] Total Records Evaluated : {audit_summary.total_rows:,}")
    print(f"      [OK] Overall Quality Score   : {audit_summary.data_quality_score}%")
    print(f"      [OK] Critical Violations     : {audit_summary.critical_issues_count:,}")
    print(f"      [OK] Statistical Warnings    : {audit_summary.warning_issues_count:,}")

    # 3. Cleaning & Quarantine Separation Step
    clean_df = raw_df
    quarantine_df = pd.DataFrame()
    sanitization_summary = None

    if do_clean:
        print(f"\n[3/4] Running automated sanitization, imputation & quarantine isolation...")
        cleaner = DataSanitizer()
        clean_df, quarantine_df, sanitization_summary = cleaner.clean_and_quarantine(raw_df, audit_summary)
        
        DATA_CLEAN.parent.mkdir(parents=True, exist_ok=True)
        clean_df.to_csv(DATA_CLEAN, index=False)
        quarantine_df.to_csv(DATA_QUARANTINE, index=False)
        
        print(f"      [OK] Clean Records Approved  : {len(clean_df):,} saved to {DATA_CLEAN.name}")
        print(f"      [OK] Quarantined Records     : {len(quarantine_df):,} saved to {DATA_QUARANTINE.name}")
        print(f"      [OK] Imputed Fields          : {sanitization_summary.imputed_fields_count:,}")
        print(f"      [OK] Normalized Fields       : {sanitization_summary.normalized_fields_count:,}")

    # 4. Reporting Step
    if do_report and sanitization_summary:
        print(f"\n[4/4] Compiling executive audit reports...")
        reporter = AuditReporter(output_dir=REPORTS_DIR)
        html_path = reporter.generate_html_report(audit_summary, sanitization_summary)
        md_path = reporter.generate_markdown_summary(audit_summary, sanitization_summary)
        print(f"      [OK] Interactive HTML Dashboard : {html_path}")
        print(f"      [OK] Markdown Summary           : {md_path}")

    print("\n" + "=" * 70)
    print("[SUCCESS] PIPELINE EXECUTION COMPLETED SUCCESSFULLY")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Clinical Data Quality & Anomaly Detection Pipeline CLI"
    )
    parser.add_argument("--generate", action="store_true", help="Force synthetic raw data generation")
    parser.add_argument("--records", type=int, default=1000, help="Number of records to generate (default: 1000)")
    parser.add_argument("--audit-only", action="store_true", help="Run audit validation without cleaning")
    parser.add_argument("--no-report", action="store_true", help="Skip report generation")

    args = parser.parse_args()

    run_pipeline(
        do_generate=args.generate,
        do_audit=True,
        do_clean=not args.audit_only,
        do_report=not args.no_report,
        n_records=args.records
    )


if __name__ == "__main__":
    main()
