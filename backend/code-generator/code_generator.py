import requests
from fastapi import FastAPI
from backend.shared.models import CodeGenRequest
import os
import re
import logging

app = FastAPI()

# Set up logging to logs/
os.makedirs("logs", exist_ok=True)
log_file = os.path.join("logs", "code-generator.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, mode='a')
    ]
)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

def generate_code_from_llm(subtask: str) -> str:

    prompt = (
        f"You are a senior Python developer. Write Python code to implement this subtask:\n"
        f"{subtask}\n"
        f"Respond with only valid Python code, no explanations."
    )

    logging.info(f"Generating code for subtask [: {subtask}]")

    response = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False})
    return response.json()["response"]

@app.post("/generate")
def generate_code(req: CodeGenRequest):
    folder_path = os.path.join("generated-code", req.folder)
    os.makedirs(folder_path, exist_ok=True)

    code = generate_code_from_llm(req.subtask)

    # Sanitize filename
    filename_base = re.sub(r'[^a-zA-Z0-9_]+', '_', req.subtask.lower())[:100]
    filename = f"{filename_base}.py"
    filepath = os.path.join(folder_path, filename)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w") as f:
        f.write(code)

    return {"status": "ok", "file": filepath}

