from sentence_transformers import SentenceTransformer


class Retriever:
    def __init__(self, db_manager, model_name="all-MiniLM-L6-v2"):
        self.db_manager = db_manager
        self.encoder = SentenceTransformer(model_name)

    def search(self, query, top_k=3, score=0.5):
        query_vector = self.encoder.encode([query])[0].tolist()

        results = self.db_manager.client.search(
            collection_name=self.db_manager.collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score
        )

        return [(hit.payload["text"], hit.score) for hit in results]
