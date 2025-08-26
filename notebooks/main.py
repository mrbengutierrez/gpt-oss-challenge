import requests
import json

def run_prompt(prompt: str, model: str = "gpt-oss:20b"):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False   # set True if you want streaming responses
    }

    response = requests.post(url, json=payload)
    response.raise_for_status()

    data = response.json()
    return data["response"]

if __name__ == "__main__":
    prompt = "Explain quantum computing in simple terms."
    answer = run_prompt(prompt)
    print("Model response:\n", answer)
