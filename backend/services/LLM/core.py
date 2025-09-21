from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from typing import List, Tuple
from langchain.schema import HumanMessage

load_dotenv()

class LLMCore:
    def __init__(self):
        self.model =  ChatGoogleGenerativeAI(
            model="models/gemma-3-27b-it",
            google_api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
            temperature=0.2
        )
        return
    def _build_gemini_prompt(self, question: str, memory_text:str, context: str) -> str:
        """
        Build a prompt optimized for Google Gemini models.
        
        Args:
            question (str): User's question
            memory (List): Conversation history
            context (str): Context text
            
        Returns:
            str: Formatted prompt optimized for Google Gemini
        """
        return f"""
### System
Você é um assistente especializado em responder perguntas sobre a NetFlix, sua base de conhecimento é fornecida em DOCUMENTOS.
Os documentos são trechos de FAQs da NetFlix, e você deve usar *SOMENTE OS DOCUMENTOS* para responder às perguntas dos usuários.

Siga essas instruções cuidadosamente:
1. Caso não haja informações suficientes nos documentos para responder a pergunta, você deve pedir para o usuário reformular a pergunta. Você deve sempre reforçar que pode responder perguntas relacionadas à NetFlix.
2. Sua única fonte de verdade são os documentos fornecidos.     
3. Use a seção MEMORY apenas como referência de contexto/fatos.
4. NÃO REPITA palavra-por-palavra o conteúdo da seção MEMORY, especialmente saudações ou respostas anteriores do assistant.
5. Você pode colocar links presentes nos documentos como URLs clicáveis para complementar sua resposta.
6. Não fale sobre os documentos para o usuário, apenas use-os para responder a pergunta.

### DOCUMENTS
DOCUMENTOS:
{context}

### MEMORY
{memory_text}

### USER
Human: {question}
        """
    def generate_response(self, question: str, memory: List, context_chunks: List[Tuple[str, float]]) -> dict:
        context = "\n\n".join([chunk for (chunk,score) in context_chunks])
        short_memory = memory[-7:-1] if len(memory) > 7 else (memory[:-1] if len(memory) > 1 else [])
        if context:
            docs = context.split("\n\n")
            documents_str = "\n".join([f"Documento {i+1}: {doc}" for i, doc in enumerate(docs)])
        else:
            documents_str = "Nenhum documento encontrado."
        memory_text = ''.join([f"{('User' if m['role']=='user' else 'Assistant')}: {m['content']}\n" for m in memory])
        prompt = self._build_gemini_prompt(question, memory_text, documents_str)
        print("Prompt para Gemini:\n", prompt)
        # Generate response using Google Gemini
        messages = [HumanMessage(content=prompt)]
        response = self.model.invoke(messages)
        response_text = response.content
        
        # Extract references (original chunk texts)
        references = context_chunks
        
        return {
            "answer": response_text.strip(),
            "references": references
        }