"""
Mistral 7B Model Reader for Financial Document Analysis

This module loads and runs the Mistral 7B Instruct model to analyze
10-K financial documents and provide investment insights. 

Usage:
    python mistral_reader.py
    
Note:
    Set HF_TOKEN environment variable before running for faster downloads.
"""

from transformers import AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import login
import torch
import os


login()

# Check GPU availability
print(f"CUDA Available: {torch.cuda.is_available()}")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load model using transformers
print("Loading Mistral model...")
model_id = "mistralai/Mistral-7B-Instruct-v0.3"
tokenizer = AutoTokenizer.from_pretrained(
    model_id,
    trust_remote_code=True
)

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    dtype=torch.float16 if torch.cuda.is_available() else torch.float32
)
model.to(device)

def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

folder = "data/Qualcomm/extracted"
texts = []

for filename in os.listdir(folder):
    if filename.endswith(".txt"):
        path = os.path.join(folder, filename)
        texts.append(load_text(path))

section_text = "\n\n".join(texts)

# Limit text to first 4000 chars to avoid token overflow
section_text = section_text[:4000]

# Generate response
prompt = f"""Analyze the extracted information from the 10-K document and provide a brief TLDR with the bottom line up front for investors.

Document:
{section_text}

Summary:"""

messages = [
    {"role": "user", 
    "content": prompt}
]

inputs = tokenizer.apply_chat_template(
    messages,
    add_generation_prompt=True,
    return_dict=True, 
    return_tensors="pt"
).to(device)

with torch.no_grad():
    outputs = model.generate(
        input_ids=inputs["input_ids"],
        attention_mask=inputs.get("attention_mask"),
        max_new_tokens=500,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
    )

print(tokenizer.decode(
    outputs[0], 
    skip_special_tokens=True)
)
