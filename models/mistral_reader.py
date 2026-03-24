from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

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
prompt = "Who is the first Czar of Russia?"
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

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    dtype=torch.float16, 
    device_map="auto"
)

# Generate response
outputs = model.generate(
    **inputs, 
    max_new_tokens=1000,
)

print(tokenizer.decode(
    outputs[0], 
    skip_special_tokens=True)
)
