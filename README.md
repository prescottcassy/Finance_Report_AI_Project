# Finance_Report_AI_Project

Finance_Report_AI_Project is a full-stack 10-K analysis app that turns SEC filing PDFs into investor-ready reports with structured extraction, AI-generated summaries, a bottom line, and a narrative view of the business.

## What it does

- Upload a 10-K PDF from any company.
- Extract key sections such as Business Overview, Risk Factors, MD&A, and Financial Statements.
- Pull numeric financial table content when available.
- Generate section summaries, a bottom line, and a long-form company story using Anthropic.
- Render the finished report in the browser and export it as a PDF.

## Tech Stack

- Frontend: Vue 3 + Vite
- Backend: Flask
- PDF extraction: pypdf, pdfplumber
- Report generation: reportlab
- AI generation: Anthropic API

## Project Structure

- `backend/` Flask API, report generation, and AI summarization
- `scripts/` 10-K extraction and section parsing logic
- `src/` Vue frontend

## Setup

### 1. Install Python dependencies

```powershell
python -m pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_MODEL=claude-3-5-haiku-latest
SECTION_SUMMARY_MAX_TOKENS=700
SECTION_SUMMARY_TARGET_WORDS=420
FINANCIAL_SUMMARY_TARGET_WORDS=520
NARRATIVE_TARGET_WORDS=700
NARRATIVE_MAX_TOKENS=950
ANTHROPIC_CONTINUATION_ROUNDS=2
```

### 3. Install frontend dependencies

```powershell
cd src
npm install
```

## Run the app

### Start the backend

```powershell
python backend/app.py
```

### Start the frontend

```powershell
cd src
npm run dev
```

Open the Vite URL shown in the terminal, upload a 10-K PDF, and wait for the report to finish.

## Output

The app produces:

- A bottom line summary
- A long-form narrative
- Section-level analysis for:
  - Business Overview
    - Risk Factors
- MD&A
- Financials
- A downloadable PDF report

## Notes

- The pipeline is designed to work across different companies and 10-K formats.
- Financial statement data is enhanced with extracted numeric table excerpts when available.
- If a model or environment variable is missing, the backend will fail fast with a clear error.

## License

No license has been specified yet.
