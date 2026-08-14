from actor import ResearchActor
from vector_store import SemanticMemory
from verifier1 import ClaimVerifier


class KnowledgeCurator:
    """Orchestrates document extraction, dual-agent verification, and vector storage."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.actor = ResearchActor(model_name=model_name)
        self.verifier = ClaimVerifier(model_name=model_name)
        self.vector_store = SemanticMemory()

    def ingest_document(self, text: str, source_name: str) -> int:
        print(f"\n Ingesting '{source_name}'...")

        # 1. Actor extracts atomic claims
        claims = self.actor.extract_claims(text, source=source_name)
        print(f" Actor extracted {len(claims)} claim(s).")

        # 2. Verifier audits extracted claims against raw source
        verified_claims = self.verifier.verify_claims(source_text=text, claims=claims)
        print(f" Verifier approved {len(verified_claims)} claim(s).")

        if not verified_claims:
            print(" No valid claims passed verification.")
            return 0

        # 3. Format verified claims into vector store chunks
        formatted_chunks = [
            {
                "source": claim["source"],
                "content": f"[{claim.get('category', 'General')}] {claim['claim']}",
            }
            for claim in verified_claims
        ]

        # 4. Commit to Semantic Vector Memory
        self.vector_store.add_documents(formatted_chunks)
        print(f" Committed {len(formatted_chunks)} verified claim(s) to Semantic Memory!")
        return len(formatted_chunks)

    def query_knowledge(self, question: str, top_k: int = 3) -> list[dict]:
        return self.vector_store.search(query=question, top_k=top_k)


if __name__ == "__main__":
    curator = KnowledgeCurator()

    sample_doc = """
    Recent trials in nuclear fusion at the National Ignition Facility achieved net energy gain (ignition).
    The lasers delivered 2.05 megajoules of energy, resulting in 3.15 megajoules of fusion energy output.
    Some media reports claimed this instantly solves commercial power generation, but commercial viability 
    requires repetition rates of 10 Hz, which remains decades away.
    """

    curator.ingest_document(text=sample_doc, source_name="fusion_report.txt")

    query = "What energy yield was achieved in fusion trials?"
    print(f"\n Querying Knowledge Store: '{query}'")
    results = curator.query_knowledge(query)

    for idx, res in enumerate(results, 1):
        print(f"\n[{idx}] Score: {res['similarity']:.4f} | Source: {res['source']}")
        print(f"    Content: {res['content']}")