# Finance Report AI Project

Finance Report AI Project is a focused verification tool that compares numeric statements in user-supplied analysis documents against the authoritative text and tables in an SEC 10-K filing. The goal is not to provide investment advice or opinions, but to confirm whether numeric claims (amounts, percentages, years, counts) in an analysis document match the source 10-K.

Key features
- Extracts full text and financial tables from a 10-K PDF.
- Builds a retrievable corpus (RAG) of source excerpts split into overlapping chunks.
- For each uploaded analysis document, finds candidate claims and verifies them against retrieved excerpts with a model prompt that focuses exclusively on numeric correctness.
- Prioritizes numeric evidence during retrieval and scoring so matching numbers are favored.
- Produces a JSON verification result and an optional downloadable PDF report summarizing verification status.

Architecture overview
- Frontend: Vue 3 + Vite — simple UI to upload a 10-K and one or more analysis documents, view verification cards, and download the PDF report.
- Backend: Flask API (in `backend/`) — handles extraction, RAG corpus building, verification, and PDF generation.
- Extraction: `scripts/extract_10k.py` extracts ITEM sections and CSV-style financial tables.
- Verification logic and RAG utilities: `backend/10k_reader.py`.
- PDF generation: `backend/pdf_generator.py` (ReportLab).

How it verifies
1. Extraction: the backend extracts the 10-K full text and saves key ITEM sections (Business Overview, Risk Factors, MD&A, Financials). Financial tables are saved as CSV snippets when found.
2. Corpus: extracted sections are chunked into overlapping text blocks to form a RAG corpus.
3. Claim selection: uploaded analysis documents are split into candidate claims (sentences/paragraphs) but common metadata lines (e.g., "Prepared by:", "Date:") are removed before claim extraction.
4. Retrieval: lexical overlap plus numeric-priority scoring returns the most relevant chunks for each claim. Exact numeric token matches are heavily weighted.
5. Model verification: the verifier prompt requires numeric-only comparisons (no opinions). The model must return a structured short response:
	 - VERDICT: Supported | Partially Supported | Unsupported | Unclear
	 - REASON: concise numeric comparison(s) only
	 - EVIDENCE: one or two short quotes/paraphrases from the retrieved excerpts
6. Aggregation: findings are combined into a job result and optionally rendered into a PDF report.

Supported file types
- 10-K input: PDF (best when text-extractable; image-only PDFs will yield limited results).
- Analysis documents: PDF, .txt, .md (PDFs are text-extracted; if extraction fails the document will be marked "needs_review").

API endpoints (backend)
- `POST /analyze` — multipart/form-data: `file` (10-K PDF) and `analysis_files[]` (one or more analysis files). Returns `{ job_id, status }`.
- `GET /job/<job_id>` — job status and JSON verification results.
- `GET /download/<job_id>` — download generated PDF (when available).

Important environment variables
- `ANTHROPIC_API_KEY` — API key for Anthropic (required for AI verification).
- `ANTHROPIC_MODEL` — preferred model id (optional, falls back to configured candidates).
- `ANTHROPIC_CONTINUATION_ROUNDS` — how many continuation rounds to request from the model (default: 2).
- Optional metadata for PDFs: `COURSE_NAME`, `PROFESSOR_NAME` (used only for cover metadata when generating PDFs).

Quick setup
1. Create and activate a Python virtual environment.

```bash
python -m venv venv
# Windows PowerShell
.\venv\Scripts\Activate.ps1
```

2. Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

3. Create a `.env` (project root) with at least:

```env
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_MODEL=claude-3-5-haiku-latest
ANTHROPIC_CONTINUATION_ROUNDS=2
```

4. Install frontend dependencies and run the UI

```bash
cd src
npm install
npm run dev
```

5. Start the backend

```bash
python backend/app.py
```

Example curl test (local backend running on port 8000)

```bash
curl -X POST "http://localhost:8000/analyze" \
	-F "file=@/path/to/10k.pdf" \
	-F "analysis_files[]=@/path/to/analysis1.pdf" \
	-F "analysis_files[]=@/path/to/analysis2.txt"
```

Outputs
- JSON job result: contains `analysis_verification` array with `findings` per claim and an aggregated `verification_summary`.
- PDF report: downloadable from `/download/<job_id>` when the PDF generation step completes; stored in `backend/generated_reports/`.

Design notes and limitations
- The verifier focuses on numeric correctness and explicitly avoids offering opinions or investment recommendations.
- Accuracy depends on extraction quality; if a PDF is scanned (image-only), extraction may be poor and many claims will be "Unclear".
- The Anthropic API is used for natural-language verification; network/API errors will surface as job errors.

If you'd like, I can also: run a sample analysis with a provided 10-K and analysis file, or add a short test harness to exercise `/analyze` from `scripts/`.

---
This README was updated to precisely describe the project's verification-first, numeric-focused behavior and how to run it locally.
