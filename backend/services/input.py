from .start_rag import StartRAG
from .RAG.retriever import Retriever
from .LLM.core import LLMCore
import pandas as pd
from datetime import datetime
from .logger.logger import SimpleLogger

logger = SimpleLogger()

class InputService:
    def __init__(self):
        self.rag = StartRAG()
        self.retriever = Retriever(self.rag.get_db())
        self.llm = LLMCore()
        self.log_historychat = "backend/data/history/"
        return
    
    def log_conversation(self, question, session_id, response, log_dir):
        log_file = f"{log_dir}chat_history_{session_id}.csv"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        df = pd.DataFrame([{
            'timestamp': [timestamp],
            "session_id": session_id,
            "question": question,
            "answer": response["answer"],
            "references": response.get("references", [])
        }])
        try:
            df_existing = pd.read_csv(log_file)
            df = pd.concat([df_existing, df], ignore_index=True)
        except FileNotFoundError:
            pass
        df.to_csv(log_file, index=False)
        return
    
    def process_question(self, question, memory, session_id, top_k=5, score=0.3):
        logger.info(f"Iniciando processamento de pergunta - Sessão: {session_id}")
        logger.debug(f"Pergunta: {question}")
        try:
            logger.info("Buscando documentos relevantes...")
            hits = self.retriever.search(question, top_k=top_k, score=score)
            logger.info(f"Encontrados {len(hits)} documentos com score > {score}")
            
            if not hits:
                logger.warning("Nenhum documento relevante encontrado para a pergunta")
            
            logger.info("Gerando resposta com LLM...")
            response = self.llm.generate_response(question, memory, hits)
            logger.info("Resposta gerada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao processar pergunta: {str(e)}", exc_info=True)
            raise

        try:
            # Registrar a conversa no histórico
            self.log_conversation(question, session_id, response, self.log_historychat)
            logger.info("Conversa registrada no histórico")
        except Exception as e:
            logger.error(f"Erro ao registrar conversa no histórico: {str(e)}", exc_info=True)
        
        return response