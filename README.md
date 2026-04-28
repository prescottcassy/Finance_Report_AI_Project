# RAG-based Structure for Finance in AI Class
Verify numeric claims in analysis documents against an SEC 10‑K.

Features
- Extracts text and financial tables and builds a RAG corpus.
- Verifies numeric claims and returns structured verdicts: Supported / Partially / Unsupported / Unclear.
- Optional PDF report with per-claim findings and evidence.

Quick start
1. Create a venv and install deps:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# set ANTHROPIC_API_KEY in env or .env
```
2. Start backend:
```bash
python backend/app.py
```

Optional: start the frontend (dev server):
```bash
cd src
npm install
npm run dev
```
3. POST `/analyze` with `file` (10‑K) and `analysis_files[]`; download PDF via `/download/<job_id>`.

Notes
- Focuses only on numeric correctness and removes common metadata lines.
- Scanned PDFs may yield "Unclear" findings due to extraction quality.

Files: `scripts/extract_10k.py`, `backend/10k_reader.py`, `backend/pdf_generator.py`.
