from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationMixin
import torch
import os
import importlib.util

# Import your existing extraction script
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
extract_10k_path = os.path.join(project_root, "scripts", "extract_10k.py")
spec = importlib.util.spec_from_file_location("extract_10k", extract_10k_path)
if spec and spec.loader:
    extract_10k_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extract_10k_module)
    extract_10k_sections = extract_10k_module.extract_10k_sections

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

# Load Mistral once on startup
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_id = "mistralai/Mistral-7B-Instruct-v0.3"
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
model: GenerationMixin = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"
)

def run_mistral(text, section_name):
    prompt = f"""Summarize this {section_name} section from a 10-K for investors. Be concise.

{text[:3000]}

Summary:"""
    messages = [{"role": "user", "content": prompt}]
    inputs = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True,
        return_dict=True, return_tensors="pt"
    ).to(device)
    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs.get("attention_mask"),
            max_new_tokens=300,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
        )
    return tokenizer.decode(outputs[0], skip_special_tokens=True).split("Summary:")[-1].strip()

@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("file")
    company = request.form.get("company", "Company")

    if not file:
        return jsonify({"error": "No file provided"}), 400

    # 1. Save uploaded PDF
    pdf_path = "data/uploaded/10k.pdf"
    output_folder = "data/uploaded/extracted"
    os.makedirs("data/uploaded", exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)
    file.save(pdf_path)

    # 2. Run extraction
    extract_10k_sections(pdf_path, output_folder)

    # 3. Read extracted text files
    sections_map = {
        "Business Overview": "businessOverview.txt",
        "Risk Factors":      "riskFactors.txt",
        "MD&A":              "managementDiscussion.txt",
        "Financials":        "incomeStatements.txt",
    }

    sections = []
    all_text = ""

    for title, filename in sections_map.items():
        path = os.path.join(output_folder, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            summary = run_mistral(text, title)
            sections.append({"title": title, "summary": summary})
            all_text += f"\n\n{title}:\n{summary}"
        else:
            sections.append({"title": title, "summary": "Section not found in document."})

    # 4. Generate BLUF + narrative
    bluf = run_mistral(all_text, "BLUF bottom line up front investor summary")
    narrative = run_mistral(all_text, "storytelling investor narrative connecting all sections")

    return jsonify({
        "companyName": company,
        "fiscalYear": "2024",
        "bluf": bluf,
        "narrative": narrative,
        "sections": sections
    })

if __name__ == "__main__":
    app.run(port=8000, debug=True)