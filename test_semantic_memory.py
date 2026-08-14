from vector_store import SemanticMemory

def main():
    store = SemanticMemory()

    print(" Ingesting sample research chunks into Semantic Memory...")
    sample_docs = [
        {
            "source": "quantum_paper.txt",
            "content": "Quantum error correction utilizes surface codes to shield qubits from environmental decoherence."
        },
        {
            "source": "ai_paper.txt",
            "content": "Transformer architectures rely on multi-head self-attention mechanisms to process sequential token representations."
        },
        {
            "source": "biology_paper.txt",
            "content": "CRISPR-Cas9 acts as molecular scissors targeting specific DNA sequences for genome editing."
        }
    ]

    store.add_documents(sample_docs)
    print(" Ingestion complete!")

    query = "How do neural networks process attention?"
    print(f"\n Querying: '{query}'")
    
    matches = store.search(query=query, top_k=2)
    for idx, match in enumerate(matches, 1):
        print(f"\nMatch #{idx} (Similarity: {match['similarity']:.4f})")
        print(f"Source: {match['source']}")
        print(f"Content: {match['content']}")

if __name__ == "__main__":
    main()