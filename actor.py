import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types


class ResearchActor:
    """Actor Agent: Reads raw documents and extracts atomic research claims."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def extract_claims(self, text: str, source: str) -> list[dict[str, str]]:
        system_instruction = """You are a meticulous research analyst.
Extract all core factual assertions and claims from the document.

CRITICAL INSTRUCTION:
Extract the underlying direct assertions being made in the text (e.g., "The computer cracks 2048-bit RSA encryption in 3 seconds", "The prototype has 8 physical qubits", "A wormhole was created in the sink").
DO NOT extract meta-statements like "Tech blogs reported..." or "Rumors claimed...". Extract the direct statement being asserted or reported.
"""

        prompt = f"Source Document ({source}):\n{text}"

        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "claim": {"type": "STRING"},
                    "category": {"type": "STRING"},
                },
                "required": ["claim", "category"],
            },
        }

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )

        try:
            items = json.loads(response.text or "[]")
            for item in items:
                item["source"] = source
            return items
        except Exception:
            return []