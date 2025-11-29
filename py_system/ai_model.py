import os
from dotenv import load_dotenv
from groq import Groq

# Load .env file
load_dotenv()

# Get API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing! Add it in Railway Variables.")

# Initialize client
client = Groq(api_key=GROQ_API_KEY)


class AIModel:
    def __init__(self, model_text="llama-3.1-8b-instant", model_code="llama-3.1-70b-versatile"):
        self.model_text = model_text
        self.model_code = model_code

    def generate_text(self, prompt: str) -> str:
        response = client.chat.completions.create(
            model=self.model_text,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message["content"]

    def generate_code(self, prompt: str) -> str:
        code_prompt = f"Write clean and correct production-ready code:\n{prompt}"
        response = client.chat.completions.create(
            model=self.model_code,
            messages=[{"role": "user", "content": code_prompt}],
            temperature=0.4,
        )
        return response.choices[0].message["content"]

    def process(self, mode: str, prompt: str) -> str:
        if mode in ["chat", "text"]:
            return self.generate_text(prompt)
        if mode == "code":
            return self.generate_code(prompt)
        return "Invalid mode. Use 'chat', 'text', or 'code'."


# Optional test
if __name__ == "__main__":
    ai = AIModel()
    result = ai.process("chat", "Say hi")
    print(result)
