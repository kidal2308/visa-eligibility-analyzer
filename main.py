from anthropic import Anthropic
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import time
from dotenv import load_dotenv
import json
from werkzeug.utils import secure_filename
import PyPDF2

# Load environment variables (API keys) from .env file
load_dotenv()

# Initialise Flask app and Anthropic client
app = Flask(__name__)
CORS(app)

client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# This prompt instructs Claude to act as an immigration attorney and analyze
# visa eligibility across multiple visa categories (H-1B, O-1A, O-1B, EB-2, etc.)
VISA_ANALYSIS_PROMPT = """You are an expert US immigration attorney. Analyze this candidate's profile and provide visa eligibility assessment.

Candidate Profile:
- Education: {education}
- Work Experience: {experience} years in {field}
- Current Status: {current_status}
- Has Job Offer: {has_offer}
- Job Details: {job_details}
- Special Achievements: {achievements}
- Country of Origin: {country}

Analyze eligibility for these visa categories:
1. H-1B (Specialty Occupation)
2. O-1A (Extraordinary Ability - Sciences/Business/Education)
3. O-1B (Extraordinary Ability - Arts/Entertainment)
4. EB-2 (Advanced Degree or Exceptional Ability)
5. EB-3 (Skilled Worker)
6. L-1 (Intracompany Transfer, if applicable)

For EACH visa type, provide:
- eligible: "yes" | "maybe" | "no"
- confidence: 1-10
- reasoning: detailed explanation (2-3 sentences)
- requirements_met: list of requirements they satisfy
- requirements_missing: list of requirements they don't meet
- next_steps: concrete actions they should take
- timeline: estimated processing time
- estimated_cost: filing fees + attorney fees range

Also provide:
- recommended_path: which visa to pursue first
- overall_assessment: 2-3 sentence summary
- risk_factors: potential issues to address

Respond with ONLY valid JSON. No markdown, no backticks, no additional text.

JSON structure:
{{
  "visas": {{
    "H1B": {{
      "eligible": "yes|maybe|no",
      "confidence": 8,
      "reasoning": "...",
      "requirements_met": [],
      "requirements_missing": [],
      "next_steps": [],
      "timeline": "...",
      "estimated_cost": "..."
    }},
    // ... other visas
  }},
  "recommended_path": "...",
  "overall_assessment": "...",
  "risk_factors": []
}}"""


def extract_text_from_pdf(pdf_file):
    """
    Extract text content from an uploaded PDF file.

    Args:
        pdf_file: FileStorage object from Flask request

    Returns:
        str: Extracted text from all pages, or None if extraction fails
    """
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return None

def parse_resume_with_claude(resume_text):
    """
    Use Claude AI to extract structured information from resume text.

    This function sends the raw resume text to Claude and asks it to extract
    key information like education, experience, field, achievements, etc.

    Args:
        resume_text (str): Raw text extracted from resume PDF

    Returns:
        dict: Structured data with keys: education, field, experience_years,
              current_status, country, achievements, has_offer, job_details
        None: If parsing fails
    """
    prompt = f"""Extract the following information from this resume. Return ONLY valid JSON with no markdown.

Resume text:
{resume_text}

Extract:
{{
    "education": "highest degree (e.g., Master's Degree, Bachelor's Degree, PhD)",
    "field": "primary field/industry (e.g., Software Engineering, Data Science)",
    "experience_years": <number of years>,
    "current_status": "best guess of immigration status if mentioned, otherwise 'Unknown'",
    "country": "country of origin if mentioned, otherwise 'Unknown'",
    "achievements": "list notable achievements: publications, awards, patents, etc. If none, say 'None listed'",
    "has_offer": "yes or no - best guess based on resume",
    "job_details": "current or most recent company and role"
}}

Be concise. If information is not found, use reasonable defaults."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()

        # Clean markdown
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        return json.loads(response_text)
    except Exception as e:
        print(f"Resume parsing error: {e}")
        return None


#### Flask Routes ####
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/parse-resume', methods=['POST'])
def parse_resume():
    """
    Handle resume upload and parsing.

    Accepts a PDF file, extracts text, and uses Claude to parse structured
    information. This endpoint is called when users upload their resume.

    Returns:
        JSON response with parsed data or error message
    """
    try:
        if 'resume' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['resume']

        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Only PDF files are supported'}), 400

        # Extract text from PDF
        resume_text = extract_text_from_pdf(file)

        if not resume_text:
            return jsonify({'success': False, 'error': 'Could not extract text from PDF'}), 500

        # Parse with Claude
        parsed_data = parse_resume_with_claude(resume_text)

        if not parsed_data:
            return jsonify({'success': False, 'error': 'Could not parse resume'}), 500

        return jsonify({
            'success': True,
            'data': parsed_data
        })

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Analyze visa eligibility based on user profile.

    This takes user data (education, experience, etc.) in text, sends it to Claude
    with the visa analysis prompt, and returns detailed eligibility assessment
    for multiple visa types.

    Returns:
        JSON response with visa analysis or error message
    """
    try:
        data = request.json

        # Build prompt with user data
        prompt = VISA_ANALYSIS_PROMPT.format(
            education=data.get('education', ''),
            experience=data.get('experience', ''),
            field=data.get('field', ''),
            current_status=data.get('current_status', ''),
            has_offer=data.get('has_offer', 'No'),
            job_details=data.get('job_details', 'N/A'),
            achievements=data.get('achievements', 'None'),
            country=data.get('country', '')
        )

        # Call Claude API with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    temperature=0.3,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                break  # Success, exit retry loop
            except Exception as api_error:
                if attempt == max_retries - 1:
                    # Last attempt failed
                    return jsonify({
                        'success': False,
                        'error': f'API Error: {str(api_error)}. The service might be overloaded. Please try again in a moment.'
                    }), 503
                time.sleep(2)  # Wait before retry

        # Parse response
        response_text = message.content[0].text

        # Clean up response (remove markdown if present)
        response_text = response_text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        result = json.loads(response_text)

        return jsonify({
            'success': True,
            'analysis': result
        })

    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Raw response: {response_text[:500]}")  # Print first 500 chars
        return jsonify({
            'success': False,
            'error': 'Failed to parse AI response. Please try again.',
            'details': str(e)
        }), 500
    except Exception as e:
        print(f"General Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Run Flask development server
    # Note: In production, use a proper server like Gunicorn or uWSGI
    app.run(debug=True, port=5000)