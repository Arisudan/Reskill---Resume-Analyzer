#!/usr/bin/env python3
"""Test Flask app API endpoint."""

import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from app import app


def test_api():
    """Test the /analyze endpoint."""
    print("Testing Flask API Endpoint")
    print("=" * 60)

    # Create test client
    client = app.test_client()

    test_cases = [
        {
            "name": "Backend Developer - Good Match",
            "role": "backend_developer",
            "resume_text": "Senior backend engineer with 5 years Python, SQL, Docker. Led APIs.",
        },
        {
            "name": "Frontend Developer - Moderate Match",
            "role": "frontend_developer",
            "resume_text": "React specialist with JavaScript, HTML/CSS experience.",
        },
        {
            "name": "Empty Resume - Error",
            "role": "data_scientist",
            "resume_text": "",
        },
        {
            "name": "Unknown Role - Falls back to default",
            "role": "unicorn_wrangler",
            "resume_text": "good communication and problem solving skills",
        },
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n[Test {i}] {test['name']}")
        print("-" * 60)

        response = client.post(
            "/analyze",
            json={"role": test["role"], "resume_text": test["resume_text"]},
            content_type="application/json",
        )

        print(f"Status Code: {response.status_code}")
        data = response.get_json()

        if response.status_code == 200:
            print(f"Score: {data.get('score')}")
            print(f"Role Used: {data.get('role_used')}")
            print(f"Missing Skills: {', '.join(data.get('missing_skills', [])[:3])}")
            print(f"Execution Time: {data.get('elapsed_ms')}ms")
            print(f"Truncated: {data.get('truncated')}")
            if data.get('error'):
                print(f"Error: {data.get('error')}")
            else:
                print(f"First Suggestion: {data.get('suggestions', [''])[0][:50]}...")
        else:
            error = data.get("error", "Unknown error")
            print(f"Error: {error}")

    print("\n" + "=" * 60)
    print("API Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    test_api()
