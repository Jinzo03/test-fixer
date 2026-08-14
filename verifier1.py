import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types


class ClaimVerifier:
    """Verifier Agent: Fact-checks extracted claims against source context."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def verify_claims(
        self, source_text: str, claims: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        if not claims:
            return []

        indexed_claims = [
            {
                "id": idx,
                "claim": item["claim"],
                "category": item.get("category", "General"),
            }
            for idx, item in enumerate(claims, 1)
        ]

        system_instruction = """You are a ruthless scientific peer-reviewer and fact-checker.
Audit each claim against the source text to determine if it represents CONFIRMED, VALIDATED TRUTH according to the research authors.

STRICT AUDIT RULES:
1. REJECT ("verified": false) any claim stemming from media hype, unverified rumors, or blog speculation (e.g., "cracking RSA encryption in 3 seconds", "wormhole created in a sink").
2. REJECT ("verified": false) any claim that the text explicitly refutes, clarifies as false, or states is impossible with current prototype limits.
3. APPROVE ("verified": true) ONLY claims that represent verified, true facts or direct experimental results achieved by the researchers.
"""

        prompt = f"""Claims to Audit:
{json.dumps(indexed_claims, indent=2)}

Raw Source Document:
{source_text}
"""

        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id": {"type": "INTEGER"},
                    "verified": {"type": "BOOLEAN"},
                    "reason": {"type": "STRING"},
                },
                "required": ["id", "verified", "reason"],
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

        return self._filter_verified(response.text or "[]", claims)

    def _filter_verified(
        self, response_text: str, original_claims: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        try:
            audit_results = json.loads(response_text)
            audit_map = {int(item["id"]): item for item in audit_results if "id" in item}

            verified_claims = []
            print("\n--- 🛡️ Verifier Audit Detailed Report ---")

            for idx, claim_obj in enumerate(original_claims, 1):
                audit_entry = audit_map.get(idx)
                is_verified = audit_entry.get("verified", False) if audit_entry else False
                reason = audit_entry.get("reason", "No audit record") if audit_entry else "No audit record"

                if is_verified:
                    print(f" APPROVED [Claim #{idx}]: '{claim_obj['claim']}'")
                    print(f"   └── Reason: {reason}")
                    verified_claims.append(claim_obj)
                else:
                    print(f" REJECTED [Claim #{idx}]: '{claim_obj['claim']}'")
                    print(f"   └── Reason: {reason}")

            print("-------------------------------------------\n")
            return verified_claims
        except Exception as exc:
            print(f"⚠️ Verification parsing failed: {exc}")
            return []