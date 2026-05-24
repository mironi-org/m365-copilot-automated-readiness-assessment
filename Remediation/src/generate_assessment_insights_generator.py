"""
M365 Copilot Assessment — Insights Generator (Orchestrator)

Runs all 5 generation steps in fixed order from a single command.
Each step reads directly from the source Excel — but they execute sequentially
and the orchestrator stops if any step fails.

Usage:
    python generate_assessment_insights_generator.py <input_excel> <output_directory>

Arguments:
    input_excel       Path to the assessment Excel file (.xlsx)
    output_directory  Directory to save output files
"""
import sys
import os
import subprocess

if len(sys.argv) < 3:
    print("Usage: python generate_assessment_insights_generator.py <input_excel> <output_directory>")
    sys.exit(1)

EXCEL = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])

if not os.path.isfile(EXCEL):
    print(f"Error: Input file not found: {EXCEL}")
    sys.exit(1)

os.makedirs(OUT, exist_ok=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("Step 1: Executive Summary & Visualizations", "run_step1_365B.py"),
    ("Step 2: Detailed Action Plan", "run_step2_365B.py"),
    ("Step 3: Enterprise Project Tracker", "run_step3_365B.py"),
    ("Step 4: Email Templates", "run_step4_365B.py"),
    ("Step 5: Priority Document Segmentation", "run_step5_365B.py"),
]

print(f"\n{'='*60}")
print(f"  M365 Copilot Assessment — Insights Generator")
print(f"{'='*60}")
print(f"  Input:  {EXCEL}")
print(f"  Output: {OUT}")
print(f"  Steps:  {len(STEPS)}")
print(f"{'='*60}\n")

for label, script in STEPS:
    print(f"\n{'─'*60}")
    print(f"  Running: {label}")
    print(f"{'─'*60}")
    script_path = os.path.join(SCRIPT_DIR, script)
    result = subprocess.run(
        [sys.executable, script_path, EXCEL, OUT],
        cwd=SCRIPT_DIR
    )
    if result.returncode != 0:
        print(f"\n  ✗ FAILED: {label} (exit code {result.returncode})")
        print(f"  Stopping — fix the error above and re-run.")
        sys.exit(result.returncode)

print(f"\n{'='*60}")
print(f"  ✓ All {len(STEPS)} steps completed successfully")
print(f"  Output: {OUT}")
print(f"{'='*60}\n")

