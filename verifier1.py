import json
import os
import re
from dotenv import load_dotenv
from google import genai


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
        """Filters claims using numeric ID mapping and strict epistemic verification."""
        if not claims:
            return []

        # Assign numeric IDs to claims for robust tracking
        indexed_claims = [
            {
                "id": idx,
                "claim": item["claim"],
                "category": item.get("category", "General"),
            }
            for idx, item in enumerate(claims, 1)
        ]

        claims_json = json.dumps(indexed_claims, indent=2)

        prompt = f"""You are a strict scientific peer-reviewer and fact checker.

Audit each extracted claim against the raw source text to verify if the claim represents TRUE, VALIDATED SCIENTIFIC FACT according to the text.

AUDIT RULES:
1. REJECT ("verified": false) any claim that is a blog hype exaggeration, unverified rumor, or false speculation (e.g., "cracking RSA encryption in 3 seconds" or "created a wormhole in the sink").
2. REJECT ("verified": false) any claim that the source text explicitly refutes, clarifies as false, or states is impossible/unproven with current hardware.
3. APPROVE ("verified": true) ONLY claims that represent true, confirmed facts or actual experimental results achieved by the researchers.

Input Claims to Audit:
<claims>
{claims_json}
</claims>

Raw Source Document:
<source>
{source_text}
</source>

Return a JSON array of objects inside <verification> tags.
Each item MUST include:
- "id": integer (matching the claim input id)
- "verified": boolean
- "reason": string (short justification)
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        return self._filter_verified(response.text or "", claims)

    def _filter_verified(
        self, response_text: str, original_claims: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        match = re.search(
            r"<verification>\s*(.*?)\s*</verification>",
            response_text,
            flags=re.DOTALL,
        )
        raw_json = match.group(1).strip() if match else response_text.strip()

        raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json, flags=re.MULTILINE)
        raw_json = re.sub(r"\s*```$", "", raw_json, flags=re.MULTILINE)

        try:
            audit_results = json.loads(raw_json)
            # Map results by integer ID
            audit_map = {int(item["id"]): item for item in audit_results if "id" in item}

            verified_claims = []
            for idx, claim_obj in enumerate(original_claims, 1):
                audit_entry = audit_map.get(idx)

                if audit_entry and audit_entry.get("verified", False):
                    verified_claims.append(claim_obj)
                else:
                    reason = (
                        audit_entry.get("reason", "Failed verification")
                        if audit_entry
                        else "No audit record"
                    )
                    print(f" Claim Rejected by Verifier: '{claim_obj['claim']}'")
                    print(f"   └── Reason: {reason}")

            return verified_claims
        except Exception as exc:
            print(f" Verification parsing failed: {exc}")
            return []