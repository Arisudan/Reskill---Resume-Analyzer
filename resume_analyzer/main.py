#!/usr/bin/env python3
"""CLI entry point for Resume Analyzer."""

import json
import sys
from typing import Optional

from .analyzer import analyze_resume
from .models import ResumeInput
from .output import format_result


def read_input_from_file(filepath: str) -> Optional[ResumeInput]:
    """Read JSON input from file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return ResumeInput(role=data.get("role", ""), resume_text=data.get("resume_text", ""))
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        return None


def read_input_from_stdin() -> Optional[ResumeInput]:
    """Read JSON input from stdin."""
    try:
        data = json.loads(sys.stdin.read())
        return ResumeInput(role=data.get("role", ""), resume_text=data.get("resume_text", ""))
    except Exception as e:
        print(f"Error reading from stdin: {e}", file=sys.stderr)
        return None


def main():
    """Main CLI entry point."""
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        resume_input = read_input_from_file(input_file)
    else:
        resume_input = read_input_from_stdin()

    if not resume_input:
        print(json.dumps({"error": "Invalid input format"}))
        sys.exit(1)

    result = analyze_resume(resume_input)
    print(format_result(result))


if __name__ == "__main__":
    main()
