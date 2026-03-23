#!/usr/bin/env python3
"""Flask web application for Resume Analyzer."""

import json
from flask import Flask, render_template, request, jsonify
from resume_analyzer.analyzer import analyze_resume
from resume_analyzer.models import ResumeInput

app = Flask(__name__)

# Supported roles for the dropdown
ROLES = [
    ("backend_developer", "Backend Developer"),
    ("frontend_developer", "Frontend Developer"),
    ("data_scientist", "Data Scientist"),
    ("default", "General Role"),
]


@app.route("/", methods=["GET"])
def index():
    """Render the input form."""
    return render_template("index.html", roles=ROLES)


@app.route("/analyze", methods=["POST"])
def analyze():
    """Process resume analysis request."""
    try:
        data = request.get_json()
        role = data.get("role", "").strip()
        resume_text = data.get("resume_text", "").strip()

        if not role or not resume_text:
            return (
                jsonify({"error": "Both role and resume_text are required"}),
                400,
            )

        # Analyze the resume
        result = analyze_resume(ResumeInput(role=role, resume_text=resume_text))

        # Convert to dict for JSON response
        from dataclasses import asdict
        response = asdict(result)

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/result", methods=["GET"])
def result_page():
    """Render the result display page."""
    return render_template("result.html")


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Server error"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
