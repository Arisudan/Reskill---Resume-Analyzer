#!/usr/bin/env python3
"""Run analyzer on all sample test cases and report results."""

import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from resume_analyzer.analyzer import analyze_resume
from resume_analyzer.models import ResumeInput
from resume_analyzer.output import format_result


def run_samples():
    """Load and run all sample test cases."""
    samples_path = Path(__file__).with_name("samples.json")
    with open(samples_path, "r", encoding="utf-8") as f:
        samples_data = json.load(f)
    
    test_cases = samples_data["test_cases"]
    passed = 0
    failed = 0
    
    print("=" * 80)
    print("Resume Analyzer - Sample Test Run")
    print("=" * 80)
    
    for idx, test_case in enumerate(test_cases, 1):
        case_id = test_case["id"]
        role = test_case["role"]
        resume_text = test_case["resume_text"]
        expected_min = test_case["expected_score_min"]
        expected_max = test_case["expected_score_max"]
        description = test_case["description"]
        
        result = analyze_resume(ResumeInput(role=role, resume_text=resume_text))
        
        # Validate score is in expected range
        score_valid = (expected_min <= result.score <= expected_max) if result.score is not None else False
        
        status = "✓ PASS" if score_valid else "✗ FAIL"
        if score_valid:
            passed += 1
        else:
            failed += 1
        
        print(f"\n[{idx}] {status} - {case_id}")
        print(f"    Description: {description}")
        print(f"    Role: {role} → {result.role_used}")
        print(f"    Score: {result.score} (expected {expected_min}–{expected_max})")
        print(f"    Missing Skills ({len(result.missing_skills)}): {', '.join(result.missing_skills[:3])}")
        print(f"    Execution: {result.elapsed_ms}ms")
        if result.truncated:
            print(f"    ⚠ Input was truncated")
        if result.error:
            print(f"    ✗ Error: {result.error}")
    
    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = run_samples()
    sys.exit(0 if success else 1)
