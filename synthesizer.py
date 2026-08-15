import os
from dotenv import load_dotenv
from google import genai
from vector_store import SemanticMemory


class ResearchSynthesizer:
    """Synthesizer Agent: Generates grounded research briefs from verified vector context."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.memory = SemanticMemory()

    def answer_question(self, question: str, min_similarity: float = 0.5) -> str:
        # Retrieve verified claims from vector store
        results = self.memory.search(query=question, top_k=5)
        
        # Filter retrieved context by similarity threshold
        valid_matches = [r for r in results if r.get("similarity", 0) >= min_similarity]

        if not valid_matches:
            return " Insufficient verified facts in memory to answer this question."

        # Build context block with source attributions
        context_lines = []
        for match in valid_matches:
            context_lines.append(
                f"- Source [{match['source']}]: {match['content']} (Relevance Score: {match['similarity']:.4f})"
            )
        context_str = "\n".join(context_lines)

        prompt = f"""You are an elite research synthesizer. 

Answering Question: "{question}"

RETIREVED VERIFIED CONTEXT FROM SEMANTIC MEMORY:
{context_str}

STRICT RESPONSE RULES:
1. Base your answer SOLELY on the verified facts provided above. Do NOT introduce outside knowledge.
2. Include direct source attributions in square brackets (e.g., [Source: filename.txt]).
3. End your response with a Confidence Rating (High/Medium/Low) based on the quality and similarity score of the context.
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        return response.text or "Error generating synthesis."


if __name__ == "__main__":
    synthesizer = ResearchSynthesizer()

    test_queries = [
        "What specific improvements were achieved in quantum computing experiments?",
        "How fast can quantum computers crack RSA encryption?",
    ]

    for query in test_queries:
        print(f"\n==================================================")
        print(f" User Question: '{query}'")
        print(f"==================================================")
        answer = synthesizer.answer_question(query)
        print(answer)