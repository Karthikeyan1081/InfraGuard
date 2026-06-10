import logging
import os
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

class GeminiService:
    """Gemini chatbot wrapper using the google-genai client."""

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model_name = model
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY must be set to use Gemini chat.")

        self.client = genai.Client(api_key=self.api_key)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_output_tokens: int = 4096,
        instructions: Optional[str] = None,
    ) -> Dict[str, str]:
        system_text = None
        prompt_lines: List[str] = []

        for message in messages:
            role = message.get("role", "user").strip().lower()
            content = message.get("content", "").strip()
            if not content:
                continue
            if role == "system":
                system_text = content
                continue
            speaker = "User" if role == "user" else "Assistant" if role == "assistant" else role.capitalize()
            prompt_lines.append(f"{speaker}: {content}")

        prompt_text = "\n".join(prompt_lines)
        if not prompt_text:
            raise ValueError("At least one user or assistant message is required.")

        if instructions is None and system_text:
            instructions = system_text
            
        full_prompt = prompt_text
        if instructions:
            full_prompt = f"System: {instructions}\n\n" + full_prompt

        try:
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            print(f"DEBUG: Gemini chat request - model={self.model_name}, max_tokens={max_output_tokens}, full_prompt={full_prompt!r}")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=config
            )
            print(f"DEBUG: Gemini response: text={response.text!r}")
            return {"model": self.model_name, "output": response.text.strip()}
        except Exception as e:
            logging.exception("Gemini chat request failed")
            raise
