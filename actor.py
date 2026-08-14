import json
import os
import re
from dotenv import load_dotenv
from google import genai


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
        prompt = f"""You are a meticulous research analyst.

Extract all core facts, findings, and atomic scientific/factual assertions from the text below.

INSTRUCTIONS:
1. Extract the underlying factual assertions being made (e.g., "The prototype has 8 physical qubits").
2. DO NOT extract meta-statements about media coverage or rumors (e.g., DO NOT extract "Blogs reported that..." or "Rumors claimed that..."). Instead, extract the direct claim being made (e.g., "The quantum computer can crack 2048-bit RSA encryption in 3 seconds").

Return the findings as a JSON list wrapped inside <claims> tags.
Each JSON object must contain two keys:
- "claim": A single standalone fact or assertion.
- "category": The domain (e.g., "AI", "Quantum Computing", "Biology").

Source Document ({source}):
<document>
{text}
</document>
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        return self._parse_claims(response.text or "", source)

    def _parse_claims(self, text: str, source: str) -> list[dict[str, str]]:
        match = re.search(r"<claims>\s*(.*?)\s*</claims>", text, flags=re.DOTALL)
        raw_json = match.group(1).strip() if match else text.strip()

        raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json, flags=re.MULTILINE)
        raw_json = re.sub(r"\s*```$", "", raw_json, flags=re.MULTILINE)

        try:
            items = json.loads(raw_json)
            for item in items:
                item["source"] = source
            return items
        except Exception:
            return []