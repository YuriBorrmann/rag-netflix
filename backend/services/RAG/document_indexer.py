import uuid
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer


class DocumentIndexer:
    def __init__(self, db_manager, model_name="all-MiniLM-L6-v2"):
        self.db_manager = db_manager
        self.encoder = SentenceTransformer(model_name)

    def add_documents(self, texts):
        vectors = self.encoder.encode(texts, show_progress_bar=True).tolist()

        self.db_manager.client.upsert(
            collection_name=self.db_manager.collection_name,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vectors[i],
                    payload={"text": texts[i]}
                )
                for i in range(len(texts))
            ],
        )
        print(f"📥 {len(texts)} documentos indexados com sucesso.")
