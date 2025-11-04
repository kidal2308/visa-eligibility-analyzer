# visa-eligibility-analyzer

An AI-powered tool to analyze US visa eligibility using Claude API.

## Features

- Analyzes 6 major US work visa categories (H-1B, O-1A, O-1B, EB-2, EB-3, L-1)
- Provides personalized recommendations based on user profile
- Shows confidence levels, timelines, and cost estimates
- Identifies risk factors and next steps

## Tech Stack

- **Backend:** Python, Flask
- **AI:** Anthropic Claude API (Sonnet 4)
- **Frontend:** HTML, CSS, JavaScript

## Setup

1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Create `.env` file:
```bash
   cp .env.example .env
```
4. Add your Anthropic API key to `.env`:
```
   ANTHROPIC_API_KEY=sk-ant-xxxxx
```
5. Run: `python app.py`
6. Visit http://127.0.0.1:5000 or http://localhost:5000

## Architecture

The system uses Claude's reasoning capabilities to analyze complex immigration eligibility across multiple visa categories. The prompt engineering approach ensures:
- Structured JSON output for reliable parsing
- Multi-factor analysis (education, experience, achievements)
- Confidence scoring for transparency
- Actionable next steps

## Future Enhancements

- [ ] Add document upload for automatic profile extraction
- [ ] Implement RAG for real-time policy updates
- [ ] Add multi-language support
- [ ] Build a comparison tool for multiple family members

## Demo

[ ]

## Note

This tool provides general guidance only. Consult with a licensed immigration attorney for your specific case.

