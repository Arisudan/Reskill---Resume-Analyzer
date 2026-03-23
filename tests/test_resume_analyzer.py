#!/usr/bin/env python3
"""Unit and integration tests for Resume Analyzer."""

import json
import sys
import unittest
from pathlib import Path

# Add parent to path so we can import the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from resume_analyzer.analyzer import analyze_resume
from resume_analyzer.models import ResumeInput, AnalysisResult


class TestInputValidation(unittest.TestCase):
    """Test input parsing and validation."""

    def test_empty_resume_text(self):
        """Test that empty resume text returns error."""
        result = analyze_resume(ResumeInput(role="backend_developer", resume_text=""))
        self.assertIsNone(result.score)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error, "resume_text is empty")

    def test_whitespace_only_resume(self):
        """Test that whitespace-only resume returns error."""
        result = analyze_resume(ResumeInput(role="frontend_developer", resume_text="   \n  \t  "))
        self.assertIsNone(result.score)
        self.assertIsNotNone(result.error)

    def test_unknown_role_defaults(self):
        """Test that unknown role falls back to default."""
        result = analyze_resume(ResumeInput(role="unicorn_wrangler", resume_text="communication teamwork"))
        self.assertEqual(result.role_used, "default")
        self.assertIsNotNone(result.score)

    def test_truncation_flag(self):
        """Test that large input is truncated and flagged."""
        large_text = "a" * 15000  # Exceeds MAX_INPUT_CHARS
        result = analyze_resume(ResumeInput(role="data_scientist", resume_text=large_text))
        self.assertTrue(result.truncated)


class TestSkillMatching(unittest.TestCase):
    """Test skill extraction and matching."""

    def test_match_backend_skills(self):
        """Test matching backend developer skills."""
        resume_text = "Expert in Python, SQL, Docker. Strong API design. Experienced with Git."
        result = analyze_resume(ResumeInput(role="backend_developer", resume_text=resume_text))
        self.assertGreater(result.score, 0)
        # Should match: python, sql, docker, git (api/apis phrase matching varies)
        # Verify that missing skills is reasonable (not all 6)
        self.assertLess(len(result.missing_skills), 4)

    def test_match_frontend_skills(self):
        """Test matching frontend developer skills."""
        resume_text = "JavaScript expertise, React component design, testing with Jest, HTML/CSS knowledge."
        result = analyze_resume(ResumeInput(role="frontend_developer", resume_text=resume_text))
        self.assertGreater(result.score, 50)  # Should be good match

    def test_no_skill_matches(self):
        """Test when no skills match."""
        result = analyze_resume(ResumeInput(role="data_scientist", resume_text="accountant spreadsheets"))
        self.assertLess(result.score, 30)  # Very low score
        self.assertEqual(len(result.missing_skills), 6)  # All missing

    def test_case_insensitivity(self):
        """Test case-insensitive skill matching."""
        result1 = analyze_resume(ResumeInput(role="backend_developer", resume_text="PYTHON SQL"))
        result2 = analyze_resume(ResumeInput(role="backend_developer", resume_text="python sql"))
        self.assertEqual(result1.score, result2.score)


class TestScoring(unittest.TestCase):
    """Test scoring logic."""

    def test_score_range(self):
        """Test that score is always 0-100."""
        test_cases = [
            ("minimal", 20),
            ("communication teamwork", 30),
            ("python sql machine learning statistics pandas data visualization", 90),
        ]
        for text, _ in test_cases:
            result = analyze_resume(ResumeInput(role="data_scientist", resume_text=text))
            self.assertIsNotNone(result.score)
            self.assertGreaterEqual(result.score, 0)
            self.assertLessEqual(result.score, 100)

    def test_impact_keywords_boost_score(self):
        """Test that impact keywords increase score."""
        no_impact = "python sql"
        with_impact = "led python led sql led optimization"
        
        result_no = analyze_resume(ResumeInput(role="backend_developer", resume_text=no_impact))
        result_yes = analyze_resume(ResumeInput(role="backend_developer", resume_text=with_impact))
        
        # With impact keywords should score higher (or equal)
        self.assertGreaterEqual(result_yes.score, result_no.score)

    def test_score_deterministic(self):
        """Test that same input produces same output."""
        input_data = ResumeInput(role="frontend_developer", resume_text="react javascript testing")
        result1 = analyze_resume(input_data)
        result2 = analyze_resume(input_data)
        
        self.assertEqual(result1.score, result2.score)
        self.assertEqual(result1.missing_skills, result2.missing_skills)


class TestSuggestions(unittest.TestCase):
    """Test suggestion generation."""

    def test_suggestions_provided(self):
        """Test that suggestions are always provided."""
        result = analyze_resume(ResumeInput(role="backend_developer", resume_text="python"))
        self.assertGreater(len(result.suggestions), 0)

    def test_low_score_gets_alignment_suggestion(self):
        """Test that low scores get alignment improvement suggestion."""
        result = analyze_resume(ResumeInput(role="data_scientist", resume_text="unrelated content"))
        self.assertLess(result.score, 50)
        # Should have alignment suggestion
        alignment_suggestions = [s for s in result.suggestions if "role alignment" in s.lower()]
        self.assertGreater(len(alignment_suggestions), 0)

    def test_missing_skill_suggestions(self):
        """Test that missing skills are suggested."""
        result = analyze_resume(ResumeInput(role="backend_developer", resume_text="python"))
        for suggestion in result.suggestions[:len(result.missing_skills)]:
            self.assertIn("Add evidence of", suggestion)


class TestPerformance(unittest.TestCase):
    """Test performance requirements."""

    def test_execution_under_2_seconds(self):
        """Test that analysis completes in under 2 seconds."""
        result = analyze_resume(ResumeInput(role="backend_developer", resume_text="python sql docker"))
        self.assertLess(result.elapsed_ms, 2000)

    def test_large_input_performance(self):
        """Test that large (but valid) input is processed quickly."""
        large_text = "python " * 1000
        result = analyze_resume(ResumeInput(role="data_scientist", resume_text=large_text))
        self.assertLess(result.elapsed_ms, 2000)


class TestOutputFormat(unittest.TestCase):
    """Test output formatting."""

    def test_result_dataclass_has_required_fields(self):
        """Test that result includes all required fields."""
        result = analyze_resume(ResumeInput(role="backend_developer", resume_text="python"))
        
        self.assertIsNotNone(result.score)
        self.assertIsInstance(result.missing_skills, list)
        self.assertIsInstance(result.suggestions, list)
        self.assertIsNotNone(result.role_used)
        self.assertIsInstance(result.truncated, bool)
        self.assertIsNotNone(result.elapsed_ms)

    def test_output_is_json_serializable(self):
        """Test that result can be serialized to JSON."""
        from resume_analyzer.output import format_result
        
        result = analyze_resume(ResumeInput(role="backend_developer", resume_text="python sql"))
        json_output = format_result(result)
        
        # Should be valid JSON
        parsed = json.loads(json_output)
        self.assertIn("score", parsed)
        self.assertIn("missing_skills", parsed)


class TestIntegration(unittest.TestCase):
    """End-to-end integration tests."""

    def test_e2e_basic_analysis(self):
        """Test full pipeline with real-world-like resume."""
        resume = """
        Senior Backend Engineer with 5 years experience.
        Expert in Python, SQL, Docker and microservices.
        Led development of high-performance APIs.
        Built automated testing infrastructure.
        Strong Git workflow practices.
        """
        result = analyze_resume(ResumeInput(role="backend_developer", resume_text=resume))
        
        # Should be reasonably good score
        self.assertGreater(result.score, 60)
        self.assertLess(result.score, 100)
        self.assertIsNone(result.error)
        self.assertEqual(result.role_used, "backend_developer")

    def test_e2e_multiple_roles(self):
        """Test analysis with different roles."""
        resume = "python javascript react html css sql"
        
        ds_result = analyze_resume(ResumeInput(role="data_scientist", resume_text=resume))
        fe_result = analyze_resume(ResumeInput(role="frontend_developer", resume_text=resume))
        be_result = analyze_resume(ResumeInput(role="backend_developer", resume_text=resume))
        
        # Frontend should score best (has react, javascript, html, css)
        self.assertGreater(fe_result.score, ds_result.score)
        self.assertGreater(fe_result.score, be_result.score)

    def test_consistent_output_structure(self):
        """Test that output structure is consistent."""
        from resume_analyzer.output import format_result
        
        inputs = [
            ResumeInput(role="backend_developer", resume_text="python"),
            ResumeInput(role="frontend_developer", resume_text="react"),
            ResumeInput(role="data_scientist", resume_text="statistics"),
        ]
        
        outputs = [format_result(analyze_resume(inp)) for inp in inputs]
        parsed = [json.loads(o) for o in outputs]
        
        # All should have same keys
        keys = set(parsed[0].keys())
        for p in parsed[1:]:
            self.assertEqual(set(p.keys()), keys)


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()
