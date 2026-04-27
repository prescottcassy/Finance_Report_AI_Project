# Finance Report AI Project

Finance Report AI Project is a full-stack 10-K verification app that compares uploaded analysis documents against an SEC 10-K using extracted source evidence and RAG-style retrieval.

## What it does

- Upload a 10-K PDF from any company.
- Upload one or more analysis documents to verify against the 10-K.
- Extract source text and financial tables from the filing.
- Retrieve supporting 10-K evidence for claims inside uploaded analysis files and flag unsupported statements.
- Render a verification report in the browser and export it as a PDF.

## Tech Stack

- Frontend: Vue 3 + Vite
- Backend: Flask
- PDF extraction: pypdf, pdfplumber
- Report generation: reportlab
- AI generation: Anthropic API used for claim verification against retrieved evidence

## Project Structure

- `backend/` Flask API, report generation, and verification logic
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

Open the Vite URL shown in the terminal, upload a 10-K PDF, add the analysis documents you want checked, and wait for the verification report to finish.

The verification step accepts analysis PDFs, `.txt`, or `.md` files and checks their claims against retrieved 10-K evidence.

## Output

The app produces:

- Analysis verification results for any uploaded documents
- A downloadable PDF report

## Notes

- The pipeline is designed to work across different companies and 10-K formats.
- Financial statement data is extracted to improve evidence retrieval.
- Uploaded analysis documents are checked against retrieved 10-K evidence and summarized in the report.
- If a model or environment variable is missing, the backend will fail fast with a clear error.

## License

No license has been specified yet.
