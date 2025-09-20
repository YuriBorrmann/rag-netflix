import os
import shutil
from qdrant_client import QdrantClient
from qdrant_client.http import models


class VectorDBManager:
    def __init__(self, collection_name="faq", vector_size=384, path="./backend/data/vector_db"):
        if os.path.exists(path):
            shutil.rmtree(path)  
        self.client = QdrantClient(path=path)

        self.collection_name = collection_name
        self.vector_size = vector_size

    def create_collection(self):
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=self.vector_size, distance=models.Distance.COSINE),
        )
        print(f"✅ Collection '{self.collection_name}' criada com {self.vector_size} dimensões.")
