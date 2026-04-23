from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import importlib.util
import tempfile
import threading
import time
from datetime import datetime

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
generate_bluf = _missing_reader
generate_narrative = _missing_reader

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
    generate_bluf = reader_module.generate_bluf
    generate_narrative = reader_module.generate_narrative

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

# Background job storage
jobs = {}

@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("file")
    company = request.form.get("company", "Company")

    if not file:
        return jsonify({"error": "No file provided"}), 400

    # Create job ID
    job_id = f"{company}_{datetime.now().timestamp()}"
    jobs[job_id] = {"status": "starting", "progress": 0, "result": None, "error": None}

    # Run analysis in background thread
    thread = threading.Thread(
        target=_analyze_async,
        args=(job_id, file, company),
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

def _analyze_async(job_id, file, company):
    """Run analysis in background and update job status"""
    try:
        jobs[job_id]["status"] = "extracting"
        jobs[job_id]["progress"] = 10

        # Use temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "10k.pdf")
            output_folder = os.path.join(tmpdir, "extracted")
            os.makedirs(output_folder, exist_ok=True)

            file.save(pdf_path)

            # Step 1 — extract sections from uploaded file
            print(f"[{job_id}] Extracting sections...")
            extract_10k_sections(pdf_path, output_folder)
            jobs[job_id]["progress"] = 30

            # Step 2 — summarize each section
            print(f"[{job_id}] Generating summaries...")
            jobs[job_id]["status"] = "summarizing"
            
            sections_map = {
                "Business Overview": "businessOverview.txt",
                "Risk Factors":      "riskFactors.txt",
                "MD&A":              "managementDiscussion.txt",
                "Financials":        "incomeStatements.txt",
            }

            sections = []
            all_text = ""

            for idx, (title, fname) in enumerate(sections_map.items()):
                path = os.path.join(output_folder, fname)
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                    print(f"[{job_id}] Summarizing {title}...")
                    summary = generate_summary(text, title)
                    sections.append({"title": title, "summary": summary})
                    all_text += f"\n\n{title}:\n{summary}"
                else:
                    sections.append({"title": title, "summary": "Section not found."})
                
                jobs[job_id]["progress"] = 30 + (idx + 1) * 12

            # Step 3 — generate BLUF + narrative
            print(f"[{job_id}] Generating BLUF and narrative...")
            jobs[job_id]["status"] = "generating"
            jobs[job_id]["progress"] = 75
            
            bluf = generate_bluf(all_text)
            jobs[job_id]["progress"] = 85
            
            narrative = generate_narrative(all_text)
            jobs[job_id]["progress"] = 95

            # Success
            result = {
                "companyName": company,
                "fiscalYear": "2024",
                "bluf": bluf,
                "narrative": narrative,
                "sections": sections
            }

            jobs[job_id]["result"] = result
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["progress"] = 100

            print(f"[{job_id}] ✓ Analysis complete")

    except Exception as e:
        print(f"[{job_id}] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)

if __name__ == "__main__":
    app.run(port=8000, debug=False)