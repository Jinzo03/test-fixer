from curator import KnowledgeCurator


def main():
    curator = KnowledgeCurator()
    
    # Wipe old test vectors so we get a clean run
    curator.vector_store.clear()

    adversarial_doc = """
    In a groundbreaking paper published by QuantumTech Labs, researchers demonstrated a 15% increase 
    in qubit coherence time using niobium-based superconducting circuits at 15 millikelvin. 
    
    Sensationalist tech blogs immediately reported that this quantum computer can now instantly crack 
    all 2048-bit RSA encryption globally within 3 seconds. However, the lead author explicitly clarified 
    that breaking RSA requires millions of logical qubits, whereas their prototype currently operates with only 8 physical qubits.
    
    Additionally, unverified online rumors claimed the researchers accidentally created a stable wormhole in the laboratory sink during testing.
    """

    print("==================================================")
    print(" STRESS TEST: Ingesting Adversarial Document...")
    print("==================================================")

    accepted_count = curator.ingest_document(
        text=adversarial_doc, source_name="adversarial_tech_news.txt"
    )

    print("\n--------------------------------------------------")
    print(f" Final Pipeline Status: {accepted_count} claim(s) added to memory.")
    print("--------------------------------------------------")

    query = "How much did qubit coherence improve?"
    print(f"\n Querying Knowledge Store: '{query}'")
    results = curator.query_knowledge(query, top_k=2)

    for idx, res in enumerate(results, 1):
        print(f"\n[{idx}] Score: {res['similarity']:.4f} | Source: {res['source']}")
        print(f"    Content: {res['content']}")


if __name__ == "__main__":
    main()