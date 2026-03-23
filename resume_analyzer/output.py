import json
from dataclasses import asdict

from .models import AnalysisResult


def format_result(result: AnalysisResult) -> str:
    payload = asdict(result)
    return json.dumps(payload, indent=2, sort_keys=True)
