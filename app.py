import streamlit as st
from backend.services.input import InputService
from streamlit.runtime.scriptrunner import get_script_run_ctx

def get_streamlit_session_id():
    """
    Retrieves the unique session ID for the current Streamlit session.
    """
    ctx = get_script_run_ctx()
    if ctx is not None:
        return ctx.session_id
    return None


st.set_page_config(page_title="NexFlix", page_icon="💬")
st.title("💬 NexFlix - FAQ da Netflix")
st.markdown("Faça perguntas sobre a Netflix e obtenha respostas rápidas!")

# Inicializa serviço com cache (só roda uma vez)
@st.cache_resource(show_spinner=True)
def get_service():
    return InputService()

# Carregando o serviço
if "service" not in st.session_state:
    with st.spinner("Carregando base de conhecimento..."):
        st.session_state.service = get_service()
        st.session_state.messages = []

service = st.session_state.service

# Função para formatar scores de forma compacta
def format_scores(references):
    if not references:
        return ""
    
    scores = []
    for i, ref in enumerate(references, 1):
        if isinstance(ref, tuple) and len(ref) >= 2:
            scores.append(f"{ref[1]:.2f}")
    
    if scores:
        return " | ".join([f"Ref {i}: {score}" for i, score in enumerate(scores, 1)])
    return ""

# Renderiza histórico de mensagens
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Se for uma mensagem do assistente e tiver referências
        if msg["role"] == "assistant" and "references" in msg and msg["references"]:
            # Mostra os scores de forma compacta
            scores_text = format_scores(msg["references"])
            if scores_text:
                st.caption(f"📊 {scores_text}")
            
            # Expander principal para todas as referências
            with st.expander("📚 Ver referências"):
                # Cada referência em seu próprio expander
                for i, ref in enumerate(msg["references"], 1):
                    if isinstance(ref, tuple) and len(ref) >= 2:
                        ref_content = ref[0]
                        score = ref[1]
                        expander_title = f"Referência {i} (Score: {score:.2f})"
                        
                        with st.expander(expander_title):
                            st.markdown(ref_content)
                    else:
                        # Fallback para referências no formato inesperado
                        expander_title = f"Referência {i}"
                        
                        with st.expander(expander_title):
                            st.markdown(str(ref))

# Input do usuário (só libera depois do carregamento)
if 'user_waiting' not in st.session_state:
    st.session_state.user_waiting = False

if question := st.chat_input(placeholder="Digite aqui sua pergunta", disabled=st.session_state.user_waiting) or st.session_state.user_waiting:
    # Exibe mensagem do usuário
    if not st.session_state.user_waiting:
        with st.chat_message("user"):
            st.session_state.user_waiting = True
            st.markdown(question)
            st.supptext = question
            user_message = {
                "role": "user", 
                "content": question,
            }
            st.session_state.messages.append(user_message)
            st.rerun()

    # Gera resposta com bloqueio (spinner visível)
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            response = service.process_question(st.supptext, st.session_state.messages, get_streamlit_session_id(), 5, 0.5)
        
        answer = response["answer"]
        references = response.get("references", [])  # Captura as referências
        
        st.markdown(answer)
        
        # Mostra os scores de forma compacta
        if references:
            scores_text = format_scores(references)
            if scores_text:
                st.caption(f"📊 {scores_text}")
            
            # Expander principal para todas as referências
            with st.expander("📚 Ver referências"):
                # Cada referência em seu próprio expander
                for i, ref in enumerate(references, 1):
                    if isinstance(ref, tuple) and len(ref) >= 2:
                        ref_content = ref[0]
                        score = ref[1]
                        expander_title = f"Referência {i} (Score: {score:.2f})"
                        
                        with st.expander(expander_title):
                            st.markdown(ref_content)
                    else:
                        # Fallback para referências no formato inesperado
                        expander_title = f"Referência {i}"
                        
                        with st.expander(expander_title):
                            st.markdown(str(ref))
        
        # Salva a mensagem completa com referências no session_state
        st.session_state.messages.append({
            "role": "assistant", 
            "content": answer,
            "references": references
        })
        st.session_state.user_waiting = False
        st.rerun()