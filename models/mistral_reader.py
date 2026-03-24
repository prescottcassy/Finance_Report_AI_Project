"""
Mistral 7B Model Reader for Financial Document Analysis

This module loads and runs the Mistral 7B Instruct model to analyze
10-K financial documents and provide investment insights. It uses GPU
acceleration (CUDA) when available and requires HF_TOKEN environment
variable for faster model access.

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

# Load model using transformers (no xformers needed)
print("Loading Mistral model...")
model_id = "mistralai/Mistral-7B-Instruct-v0.3"
tokenizer = AutoTokenizer.from_pretrained(
    model_id,
    trust_remote_code=True
)

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    dtype=torch.float16, 
    device_map="auto"
)

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

# Generate response
prompt = "Did this company perform well last year? What are the key risks and opportunities for investors based on this 10-K report? Provide a concise summary with actionable insights."
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

outputs = model.generate(
    **inputs, 
    max_new_tokens=1000,
)

print(tokenizer.decode(
    outputs[0], 
    skip_special_tokens=True)
)
