from transformers import AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import login
import torch
from concurrent.futures import ThreadPoolExecutor, as_completed

login()

print(f"CUDA Available: {torch.cuda.is_available()}")

model_id = "mistralai/Mistral-7B-Instruct-v0.3"
tokenizer = None
model = None

def load_model():
    global tokenizer, model
    print("Loading Mistral model...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    ).to(device)
    print("Model loaded.")

def generate_summary(text, section_name):
    if tokenizer is None or model is None:
        load_model()

    prompt = f"""Analyze this {section_name} section from a 10-K and provide a brief TLDR with the bottom line up front for investors.

Document:
{text[:2000]}

Summary:"""

    messages = [{"role": "user", "content": prompt}]
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt"
    )

    # Move inputs to same device as model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(  # type: ignore
            input_ids=inputs["input_ids"],
            attention_mask=inputs.get("attention_mask"),
            max_new_tokens=100,
            temperature=0.5,
            top_p=0.7,
            do_sample=True,
            early_stopping=True,
            repetition_penalty=1.2,
            use_cache=True,
        )

    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return result.split("Summary:")[-1].strip()

def generate_bluf(all_summaries):
    return generate_summary(all_summaries, "BLUF bottom line up front investor")

def generate_narrative(all_summaries):
    return generate_summary(all_summaries, "storytelling investor narrative connecting all sections")