from .RAG.vector_db_manager import VectorDBManager
from .RAG.document_indexer import DocumentIndexer
from .logger.logger import SimpleLogger

logger = SimpleLogger()

class StartRAG:
    def __init__(self):
        logger.info("Iniciando inicialização do RAG system...")
        
        try:
            logger.info("Lendo arquivo FAQ...")
            with open("backend/data/raw_data/faq_complete.txt", "r", encoding="utf-8") as f:
                text = f.read()
            logger.info(f"Arquivo FAQ lido com sucesso ({len(text)} caracteres)")
            
            # 2. Criar chunks de 500 palavras (com overlap de 50)
            logger.info("Criando chunks de texto...")
            chunks = self.chunk_text_by_words(text, 500, 50)
            logger.info(f"📑 Total de chunks gerados: {len(chunks)}")
            
            # 3. Inicializar DB
            logger.info("Inicializando banco de dados vetorial...")
            self.db = VectorDBManager(collection_name="faq", vector_size=384)  # modo embedded
            logger.info("Criando collection no banco de dados...")
            self.db.create_collection()
            logger.info("Collection criada com sucesso")
            
            # 4. Indexar documentos
            logger.info("Iniciando indexação de documentos...")
            self.indexer = DocumentIndexer(self.db)
            logger.info("Adicionando documentos ao índice...")
            self.indexer.add_documents(chunks)
            logger.info("Documentos indexados com sucesso")
            
            logger.info("✅ Sistema RAG inicializado com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro durante inicialização do RAG: {str(e)}", exc_info=True)
            raise
    
    def chunk_text_by_words(self, text, chunk_size, overlap):
        """Divide texto em chunks de 'chunk_size' palavras, com sobreposição de 'overlap'."""
        words = text.split()
        chunks = []
        start = 0

        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start += chunk_size - overlap

        return chunks
    
    def get_db(self):
        return self.db
    def get_indexer(self):
        return self.indexer
    def close_db(self):
        self.db.client.close()
        return

