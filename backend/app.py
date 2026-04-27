from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import csv
import importlib.util
import tempfile
import threading
import time
import re
from datetime import datetime
from pdf_generator import create_pdf_report

# Import extract_10k
extract_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'extract_10k.py')
spec = importlib.util.spec_from_file_location("extract_10k", extract_path)

def _missing_extract(*args, **kwargs):
    raise RuntimeError("extract_10k could not be loaded.")

extract_10k_sections = _missing_extract
if spec and spec.loader:
    extract_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extract_module)
    extract_10k_sections = extract_module.extract_10k_sections

# Import 10k_reader (same folder as app.py)
reader_path = os.path.join(os.path.dirname(__file__), '10k_reader.py')
spec2 = importlib.util.spec_from_file_location("10k_reader", reader_path)

def _missing_reader(*args, **kwargs):
    raise RuntimeError("10k_reader could not be loaded.")

generate_summary = _missing_reader
build_summary_prompt = _missing_reader
extract_uploaded_document_text = _missing_reader
build_rag_corpus = _missing_reader
verify_analysis_document = _missing_reader
summarize_verification_results = _missing_reader

if spec2 and spec2.loader:
    reader_module = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(reader_module)
    print("[STARTUP] Loading AI model... this may take a moment")
    try:
        reader_module.load_model()
        print("[STARTUP] ✓ AI model loaded successfully")
    except Exception as e:
        print(f"[STARTUP] ✗ Failed to load model: {e}")
    generate_summary = reader_module.generate_summary
    build_summary_prompt = getattr(reader_module, "build_summary_prompt", _missing_reader)
    extract_uploaded_document_text = getattr(reader_module, "extract_uploaded_document_text", _missing_reader)
    build_rag_corpus = getattr(reader_module, "build_rag_corpus", _missing_reader)
    verify_analysis_document = getattr(reader_module, "verify_analysis_document", _missing_reader)
    summarize_verification_results = getattr(reader_module, "summarize_verification_results", _missing_reader)

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

# Background job storage
jobs = {}
# PDF storage - maps job_id to PDF file path
pdf_storage = {}
pdf_output_dir = os.path.join(os.path.dirname(__file__), "generated_reports")
os.makedirs(pdf_output_dir, exist_ok=True)


def _build_financial_csv_context(output_folder):
    """Collect numeric-heavy snippets from extracted financial CSVs."""
    patterns = [
        "income_statement.csv",
        "consolidated_income_statement.csv",
        "balance_sheet.csv",
        "consolidated_balance_sheet.csv",
        "cash_flows.csv",
        "consolidated_cash_flows.csv",
    ]

    candidate_paths = []
    for name in patterns:
        candidate_paths.append(os.path.join(output_folder, name))

    sections = []
    for path in candidate_paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f if line.strip()]

            # Keep rows that likely contain numeric values.
            numeric_lines = [
                line for line in lines
                if re.search(r"\d", line)
            ]
            if not numeric_lines:
                continue

            snippet = "\n".join(numeric_lines[:80])
            sections.append(f"\n--- {os.path.basename(path)} ---\n{snippet}")
        except Exception as e:
            print(f"[financial-csv] Could not read {path}: {e}")

    if not sections:
        return ""

    return "\n\n[FINANCIAL TABLE EXCERPTS]\n" + "\n".join(sections)


def _parse_number(cell_value):
    """Parse a numeric table cell into float, handling commas and parentheses."""
    if cell_value is None:
        return None

    text = str(cell_value).strip()
    if not text:
        return None

    if text in {"-", "--", "N/A", "n/a", "na"}:
        return None

    negative = text.startswith("(") and text.endswith(")")
    text = text.replace("$", "").replace(",", "").replace("(", "").replace(")", "").replace("%", "").strip()

    # Keep only digits, decimal point, and minus sign.
    cleaned = re.sub(r"[^0-9.\-]", "", text)
    if not cleaned or cleaned in {"-", ".", "-."}:
        return None

    try:
        value = float(cleaned)
        return -value if negative else value
    except ValueError:
        return None


def _format_compact_currency(value, in_millions=True):
    """Format currency value for display. 
    in_millions=True: CSV values are in millions, multiply by 1M first
    """
    if value is None:
        return "N/A"

    # Convert from millions to actual dollars if needed
    if in_millions:
        value = value * 1_000_000
    
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:,.0f}"


def _format_eps(value):
    if value is None:
        return "N/A"
    return f"${value:.2f}"


def _format_yoy(current, prior):
    if current is None or prior is None:
        return ""
    if abs(prior) < 1e-9:
        return ""

    delta_pct = ((current - prior) / abs(prior)) * 100
    sign = "+" if delta_pct >= 0 else ""
    return f"{sign}{delta_pct:.1f}% YoY"


def _extract_row_values(row):
    numeric_values = []
    for cell in row[1:]:
        parsed = _parse_number(cell)
        if parsed is not None:
            numeric_values.append(parsed)
    return numeric_values


def _looks_like_label(row):
    return bool(row and str(row[0]).strip())


def _extract_cover_metrics(output_folder):
    """Pull first-page highlight metrics from extracted 10-K CSV tables."""
    metric_patterns = {
        "net_sales": [
            "net sales",
            "net revenues",
            "total net sales",
            "total net revenues",
            "total revenue",
            "total revenues",
            "revenue",
            "revenues",
        ],
        "net_income": ["net income", "net earnings", "net income attributable"],
        "eps": [
            "diluted eps",
            "eps diluted",
            "earnings per share diluted",
            "diluted earnings per share",
            "diluted net earnings per share",
            "diluted net income per share",
            "net earnings per share - diluted",
            "diluted",
        ],
        "free_cash_flow": ["free cash flow"],
        "operating_cash_flow": ["net cash provided by operating", "operating cash flow"],
        "capex": ["capital expenditures", "purchase of property", "additions to property"],
    }

    found = {key: [] for key in metric_patterns}
    csv_files = [
        os.path.join(output_folder, "income_statement.csv"),
        os.path.join(output_folder, "consolidated_income_statement.csv"),
        os.path.join(output_folder, "cash_flows.csv"),
        os.path.join(output_folder, "consolidated_cash_flows.csv"),
    ]

    for csv_path in csv_files:
        if not os.path.exists(csv_path):
            continue

        csv_name = os.path.basename(csv_path).lower()
        is_income_statement = "income_statement" in csv_name
        is_cash_flows = "cash_flows" in csv_name

        try:
            with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                for row in reader:
                    if not _looks_like_label(row):
                        continue

                    label = str(row[0]).strip().lower()
                    values = _extract_row_values(row)
                    if not values:
                        continue

                    for metric_name, patterns in metric_patterns.items():
                        # Restrict metrics to the most relevant statements.
                        if metric_name in {"net_sales", "net_income", "eps"} and not is_income_statement:
                            continue
                        if metric_name in {"free_cash_flow", "operating_cash_flow", "capex"} and not is_cash_flows:
                            continue

                        if any(pattern in label for pattern in patterns):
                            if metric_name == "eps" and "per share" not in label and "eps" not in label:
                                continue
                            if len(values) >= 2:
                                # Keep first valid match; income statements are typically ordered best-first.
                                if not found[metric_name]:
                                    found[metric_name] = values[:2]
                            elif len(values) == 1:
                                if not found[metric_name]:
                                    found[metric_name] = [values[0]]
        except Exception as e:
            print(f"[metrics] Could not parse {csv_path}: {e}")

    # If FCF is unavailable, derive it from OCF and Capex when possible.
    if not found["free_cash_flow"] and found["operating_cash_flow"] and found["capex"]:
        ocf_vals = found["operating_cash_flow"]
        capex_vals = found["capex"]
        if len(ocf_vals) >= 1 and len(capex_vals) >= 1:
            current_fcf = ocf_vals[0] - abs(capex_vals[0])
            if len(ocf_vals) >= 2 and len(capex_vals) >= 2:
                prior_fcf = ocf_vals[1] - abs(capex_vals[1])
                found["free_cash_flow"] = [current_fcf, prior_fcf]
            else:
                found["free_cash_flow"] = [current_fcf]

    def _current_prior(values):
        if not values:
            return None, None
        current = values[0]
        prior = values[1] if len(values) > 1 else None
        return current, prior

    sales_current, sales_prior = _current_prior(found["net_sales"])
    income_current, income_prior = _current_prior(found["net_income"])
    eps_current, eps_prior = _current_prior(found["eps"])
    fcf_current, fcf_prior = _current_prior(found["free_cash_flow"])

    # Build metrics list with Net Sales and EPS always first
    # Format currency with in_millions=True since CSV values are in millions
    metrics = [
        {
            "title": _format_compact_currency(sales_current, in_millions=True),
            "label": "Net Sales",
            "subtext": _format_yoy(sales_current, sales_prior),
        },
        {
            "title": _format_eps(eps_current),
            "label": "EPS (Diluted)",
            "subtext": f"vs {_format_eps(eps_prior)} prior yr" if eps_prior is not None else "",
        },
        {
            "title": _format_compact_currency(income_current, in_millions=True),
            "label": "Net Income",
            "subtext": _format_yoy(income_current, income_prior),
        },
        {
            "title": _format_compact_currency(fcf_current, in_millions=True),
            "label": "Free Cash Flow",
            "subtext": _format_yoy(fcf_current, fcf_prior),
        },
    ]
    
    return metrics

@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("file")
    analysis_files = request.files.getlist("analysis_files")
    company = request.form.get("company", "Company")

    if not file:
        return jsonify({"error": "No file provided"}), 400

    # Read file content immediately while request context is active
    file_content = file.read()
    filename = file.filename or "10k.pdf"

    analysis_payload = []
    for analysis_file in analysis_files:
        if not analysis_file or not analysis_file.filename:
            continue
        analysis_payload.append({
            "filename": analysis_file.filename,
            "content": analysis_file.read(),
        })

    # Create job ID
    job_id = f"{company}_{datetime.now().timestamp()}"
    jobs[job_id] = {"status": "starting", "progress": 0, "result": None, "error": None}

    # Run analysis in background thread
    thread = threading.Thread(
        target=_analyze_async,
        args=(job_id, file_content, filename, company, analysis_payload),
        daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id, "status": "started"})

@app.route("/job/<job_id>", methods=["GET"])
def get_job_status(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]
    response = {
        "status": job["status"],
        "progress": job["progress"],
    }

    if job["result"]:
        response["result"] = job["result"]
    if job["error"]:
        response["error"] = job["error"]

    return jsonify(response)

@app.route("/download/<job_id>", methods=["GET"])
def download_pdf(job_id):
    if job_id not in pdf_storage:
        return jsonify({"error": "PDF not found"}), 404
    
    pdf_path = pdf_storage[job_id]
    if not os.path.exists(pdf_path):
        return jsonify({"error": "PDF file not found"}), 404
    
    return send_file(pdf_path, as_attachment=True, download_name=f"{job_id}.pdf")

def _analyze_async(job_id, file_content, filename, company, analysis_files=None):
    """Run analysis in background and update job status"""
    start_time = time.time()
    try:
        if not analysis_files:
            raise ValueError("At least one analysis document must be uploaded for verification")

        jobs[job_id]["status"] = "extracting"
        jobs[job_id]["progress"] = 10

        # Use temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, filename)
            output_folder = os.path.join(tmpdir, "extracted")
            os.makedirs(output_folder, exist_ok=True)

            # Write file content to disk
            write_start = time.time()
            with open(pdf_path, "wb") as f:
                f.write(file_content)
            print(f"[{job_id}] File write: {time.time() - write_start:.2f}s")

            # Step 1 — extract sections from uploaded file
            extract_start = time.time()
            print(f"[{job_id}] Starting extraction...")
            try:
                extract_10k_sections(pdf_path, output_folder)
                print(f"[{job_id}] Extraction complete: {time.time() - extract_start:.2f}s")
            except Exception as e:
                print(f"[{job_id}] ✗ Extraction error: {e}")
                import traceback
                traceback.print_exc()
                raise
            jobs[job_id]["progress"] = 30
            print(f"[{job_id}] Building 10-K retrieval corpus...")
            jobs[job_id]["status"] = "verifying"

            sections_map = {
                "Business Overview": "businessOverview.txt",
                "Risk Factors": "riskFactors.txt",
                "MD&A": "managementDiscussion.txt",
                "Financials": "incomeStatements.txt",
            }

            rag_documents = []
            for title, fname in sections_map.items():
                path = os.path.join(output_folder, fname)
                if not os.path.exists(path):
                    continue

                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()

                if title == "Financials":
                    csv_context = _build_financial_csv_context(output_folder)
                    if csv_context:
                        text = text + "\n\n" + csv_context

                rag_documents.append({"source": title, "text": text})

            rag_corpus = build_rag_corpus(rag_documents)
            jobs[job_id]["progress"] = 45

            verification_results = []
            verification_sections = []
            analysis_dir = os.path.join(tmpdir, "analysis")
            os.makedirs(analysis_dir, exist_ok=True)

            print(f"[{job_id}] Verifying uploaded analysis documents with RAG...")
            for index, analysis_file in enumerate(analysis_files, start=1):
                analysis_name = os.path.basename(analysis_file.get("filename") or f"analysis_{index}")
                analysis_path = os.path.join(analysis_dir, analysis_name)
                with open(analysis_path, "wb") as analysis_handle:
                    analysis_handle.write(analysis_file.get("content", b""))

                try:
                    analysis_text = extract_uploaded_document_text(analysis_path)
                except Exception as e:
                    verification_results.append({
                        "file_name": analysis_name,
                        "overall_status": "needs_review",
                        "findings": [{
                            "claim": "Document extraction failed.",
                            "verdict": "Unclear",
                            "reason": str(e),
                            "evidence": "",
                            "sources": [],
                        }],
                    })
                    continue

                result = verify_analysis_document(analysis_name, analysis_text, rag_corpus, company)
                verification_results.append(result)
                verification_sections.append({
                    "title": analysis_name,
                    "summary": summarize_verification_results([result]),
                    "prompt": "Comparison of uploaded analysis against 10-K evidence",
                })

                jobs[job_id]["progress"] = min(85, 45 + int((index / len(analysis_files)) * 35))

            jobs[job_id]["progress"] = 90

            # Step 3 — generate PDF verification report
            print(f"[{job_id}] Generating PDF report...")
            pdf_start = time.time()
            try:
                safe_company = "".join(ch for ch in company if ch.isalnum() or ch in (" ", "_", "-")).strip().replace(" ", "_") or "report"
                pdf_path = os.path.join(pdf_output_dir, f"{safe_company}_{job_id}.pdf")
                create_pdf_report(
                    company,
                    "2024",
                    "",
                    "",
                    verification_sections,
                    pdf_path,
                    financial_metrics=None,
                    report_type="verification",
                )
                # Store PDF path for download
                pdf_storage[job_id] = pdf_path
                print(f"[{job_id}] PDF generation: {time.time() - pdf_start:.2f}s")
            except Exception as e:
                print(f"[{job_id}] ⚠ PDF generation failed (non-critical): {e}")

            # Success
            result = {
                "companyName": company,
                "fiscalYear": "2024",
                "verification_summary": summarize_verification_results(verification_results),
                "sections": verification_sections,
                "analysis_verification": verification_results,
                "mode": "verification",
                "pdf_available": job_id in pdf_storage
            }

            jobs[job_id]["result"] = result
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["progress"] = 100

            total_time = time.time() - start_time
            print(f"[{job_id}] ✓ Analysis complete in {total_time:.2f}s")

    except Exception as e:
        print(f"[{job_id}] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)

if __name__ == "__main__":
    app.run(port=8000, debug=False)
