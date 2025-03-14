import streamlit as st
import datetime
import os
import time
import PyPDF2
import random
import json
import google.generativeai as genai
# Fix the import statement - remove GoogleSearch which isn't available in the library
from google.generativeai.types import Tool
import openai

# Chaves das APIs ####(MANTENHA DO JEITO QUE ESTÃO)####
GOOGLE_API_KEY = "AIzaSyC03_RHBNHP11_8KpvKkGsVHXQOb7HZ1h0" # Substitua com sua chave real
MARITACA_API_KEY = "115990119488967327768_d98ac05a62c31fb7" # Substitua com sua chave real

# Configuração da API Maritaca
client = openai.OpenAI(
    api_key=MARITACA_API_KEY,
    base_url="https://chat.maritaca.ai/api",
)

st.set_page_config(
    page_title="GB Intelligence",  # Novo nome do aplicativo
    page_icon="💬",  # Ícone mais apropriado para um sistema inteligente
    layout="wide",
    initial_sidebar_state="expanded",
    theme="dark",  # Tema escuro para melhorar a leitura
)

# Add this near the top after st.set_page_config
custom_css = """
<style>
    .main {
        background-color: #f9f9f9;
    }
    .stApp {
        max-width: 100%;
        margin: 0 auto;
    }
    /* Adicionar estilo para o título do GB Intelligence */
    .title-area h1 {
        color: #2c3e50;  /* Cor mais corporativa */
        font-weight: 700;
        border-bottom: 2px solid #3498db;
        padding-bottom: 8px;
    }
    /* Resto do CSS permanece igual */
    .chat-container {
        border-radius: 10px;
        background-color: white;
        padding: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .chat-message-user {
        background-color: #e6f7ff;
        border-radius: 15px;
        padding: 10px 15px;
        margin: 5px 0;
        border-left: 4px solid #1890ff;
    }
    .chat-message-bot {
        background-color: #f6f6f6;
        border-radius: 15px;
        padding: 10px 15px;
        margin: 5px 0;
        border-left: 4px solid #52c41a;
    }
    .message-actions {
        opacity: 0.6;
    }
    .message-actions:hover {
        opacity: 1;
    }
    .stButton>button {
        border-radius: 20px;
    }
    .title-area {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
    }
    .title-area h1 {
        margin: 0;
    }
    .pdf-analysis-area {
        background-color: #f0f8ff;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    /* Added for better responsive layout */
    .st-emotion-cache-18ni7ap {
        max-width: 100%;
    }
    .st-emotion-cache-1kyxreq {
        justify-content: space-between;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

if "message_history" not in st.session_state:
    st.session_state.message_history = []
if "pdf_content" not in st.session_state:
    st.session_state.pdf_content = ""
if "chat_history_file" not in st.session_state:
    st.session_state.chat_history_file = "chat_history.json"
if "gemini_model" not in st.session_state:
    st.session_state.gemini_model = None
if "is_thinking" not in st.session_state:
    st.session_state.is_thinking = False
if "log_file" not in st.session_state:
    st.session_state.log_file = None
if "font_family" not in st.session_state:
    st.session_state.font_family = "Roboto"
if "font_size" not in st.session_state:
    st.session_state.font_size = 14
if "max_tokens" not in st.session_state:
    st.session_state.max_tokens = 1000
if "tone_var" not in st.session_state:
    st.session_state.tone_var = "Amigável"
if "model_var" not in st.session_state:
    st.session_state.model_var = "gemini-2.0-flash"

if "pdf_analysis_result" not in st.session_state:
    st.session_state.pdf_analysis_result = None # Inicializa com None
if "pdf_comparison_result" not in st.session_state:
    st.session_state.pdf_comparison_result = None # Inicializa com None
if "pdf_multi_analysis_result" not in st.session_state:
    st.session_state.pdf_multi_analysis_result = None # Inicializa com None

if "editing_message_index" not in st.session_state:
    st.session_state.editing_message_index = None
if "edit_message_content" not in st.session_state:
    st.session_state.edit_message_content = ""

tones = {
    "Conciso": "Seja breve e direto ao ponto em suas respostas.",
    "Criativo": "Seja criativo e use linguagem imaginativa em suas respostas.",
    "Formal": "Use um tom formal e profissional em suas respostas.",
    "Amigável": "Adote um tom amigável e casual em suas respostas.",
    "Explicativo": "Forneça respostas detalhadas com exemplos e explicações.",
}

models = {
    "gemini-2.0-flash": "Google Gemini 2.0 Flash - IA mais recente do Google",
    "gemini-2.0-flash-lite": "Google Gemini 2.0 Flash Lite - IA versão lite do Google",
    "sabiazinho-3": "Maritaca IA - Rápido para atividades do dia a dia",
    "sabia-3": "Maritaca IA - Mais moderno, ótimo para atividades complexas",
}
max_input_chars = 1000
char_count = 0

def display_message(sender, message, message_type, index=None, is_pdf_analysis=False):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_tone = st.session_state.tone_var
    current_model = st.session_state.model_var

    # Generate unique identifiers using combination of message and position in history
    message_position = len(st.session_state.message_history) if message_type == "user" else "bot" + str(len(st.session_state.message_history))
    unique_id = f"{message_type}_{message_position}_{hash(message) % 10000}"

    if message_type == "user":
        with st.chat_message("user"):
            col1, col2, col3 = st.columns([0.85, 0.075, 0.075])
            
            # Check if this message is being edited
            is_editing = (st.session_state.editing_message_index is not None and 
                         index is not None and 
                         st.session_state.editing_message_index == index)
                
            with col1:
                if is_editing:
                    # Show text area for editing directly in the message
                    edited_message = st.text_area(
                        "Edite sua mensagem:",
                        value=message,
                        key=f"edit_inline_{unique_id}",
                        height=100
                    )
                    
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("Salvar", key=f"save_{unique_id}"):
                            # Update the message in history
                            st.session_state.message_history[index]["content"] = edited_message
                            
                            # Check if there's an AI response to this message that needs to be updated
                            if index + 1 < len(st.session_state.message_history) and st.session_state.message_history[index + 1]["role"] == "assistant":
                                # Remove the old AI response
                                st.session_state.message_history.pop(index + 1)
                                
                            # Get new AI response for the edited message
                            # The response is already added to history inside get_ai_response
                            get_ai_response(edited_message)
                            
                            save_chat_history()
                            st.session_state.editing_message_index = None
                            st.rerun()
                    with col_cancel:
                        if st.button("Cancelar", key=f"cancel_{unique_id}"):
                            st.session_state.editing_message_index = None
                            st.rerun()
                else:
                    st.write(f"**Você:** {message}")
            
            if not is_editing:
                with col2:
                    # Fix: Simplified button handling without trying to set its state
                    edit_key = f"edit_msg_{unique_id}"
                    if st.button("✏️", key=edit_key, help="Editar mensagem"):
                        st.session_state.editing_message_index = index
                        st.rerun()
                with col3:
                    # Fix: Also update this button's key to be more explicit
                    regen_key = f"regen_msg_{unique_id}"
                    if st.button("🔄", key=regen_key, help="Gerar nova resposta"):
                        # Check if there's an AI response to this message that needs to be updated
                        if index + 1 < len(st.session_state.message_history) and st.session_state.message_history[index + 1]["role"] == "assistant":
                            # Remove the old AI response
                            st.session_state.message_history.pop(index + 1)
                        
                        # Get new AI response
                        ai_response = get_ai_response(message)
                        if ai_response:
                            save_chat_history()
                        st.rerun()

    elif message_type == "bot":
        with st.chat_message("assistant"):
            # Improved rendering for bot messages to properly handle markdown code blocks
            bot_name = get_bot_name()
            st.markdown(f"**{bot_name}:**", unsafe_allow_html=True)
            st.markdown(message, unsafe_allow_html=False)  # Use st.markdown to properly render markdown
            
            # Adicionar os resultados de análise de PDF ao histórico também
            # Modificado: removida a condição para não adicionar mensagens de análise de PDF
            # Check if this is a new message (not already in history)
            is_new_message = True
            for existing_msg in st.session_state.message_history:
                if existing_msg.get("role") == "assistant" and existing_msg.get("content") == message:
                    is_new_message = False
                    break
            
            if is_new_message:
                # Se for uma análise de PDF, adiciona com uma tag especial
                if is_pdf_analysis:
                    st.session_state.message_history.append(
                        {"role": "assistant", "content": message, "is_pdf_analysis": True}
                    )
                else:
                    st.session_state.message_history.append({"role": "assistant", "content": message})
                save_chat_history()

    elif message_type == "system":
        st.warning(f"**Sistema:** {message}")

def get_bot_name():
    selected_model = st.session_state.model_var
    if selected_model.startswith("gemini"):
        return "Gemini"
    else:
        return "Maritaca IA"

def get_ai_response(message):
    selected_model = st.session_state.model_var
    if selected_model.startswith("gemini"):
        return get_gemini_response(message)
    else:
        return get_maritaca_response(message)

def get_gemini_response(message):
    try:
        current_model_name = st.session_state.model_var

        if st.session_state.gemini_model is None:
            genai.configure(api_key=GOOGLE_API_KEY)
            st.session_state.gemini_model = genai.GenerativeModel(current_model_name)

        prompt_prefix = tones[st.session_state.tone_var]
        context_info = ""

        # Sempre incluir o contexto do PDF se disponível
        if st.session_state.pdf_content:
            context_info = (
                "Você analisou um documento PDF. A seguir, a conversa deve levar em consideração o"
                f" conteúdo do PDF para responder às perguntas. Conteúdo do PDF (limitado): {st.session_state.pdf_content[:4000]} ... "
            )

        # Converte histórico de mensagens para o formato esperado pelo Gemini
        chat_history = []
        for msg in st.session_state.message_history[-20:]:  # Limita para as últimas 20 mensagens
            role = "user" if msg["role"] == "user" else "model"
            chat_history.append({"role": role, "parts": [msg["content"]]})

        # Adiciona o contexto do sistema e do PDF no início da conversa
        # Modificado: sempre adicionar o contexto do PDF, mesmo se houver mensagens
        system_message = f"{prompt_prefix} {context_info}".strip()
        if system_message and not chat_history:
            chat_history.append({"role": "user", "parts": [f"Instruções do sistema: {system_message}"]})
            chat_history.append({"role": "model", "parts": ["Entendido, seguirei essas instruções."]})
        elif system_message:  # Adiciona contexto mesmo se houver mensagens
            chat_history.insert(0, {"role": "user", "parts": [f"Instruções do sistema: {system_message}"]})
            chat_history.insert(1, {"role": "model", "parts": ["Entendido, seguirei essas instruções."]})

        # Adiciona a mensagem atual do usuário
        chat_history.append({"role": "user", "parts": [message]})
        
        # Geração padrão sem pesquisa web
        response = st.session_state.gemini_model.generate_content(chat_history)

        if hasattr(response, "text"):
            answer = response.text
        else:
            answer = "Resposta não suportada"

        st.session_state.message_history.append({"role": "assistant", "content": answer})
        save_chat_history()
        return answer

    except Exception as e:
        st.error(f"Ocorreu um erro com o Gemini: {str(e)}")
        return None

def get_maritaca_response(message):
    try:
        max_tokens = int(st.session_state.max_tokens)

        current_tone = st.session_state.tone_var
        current_model = st.session_state.model_var
        
        # Adicionar contexto do PDF para o Maritaca também
        system_prompt = tones[current_tone]
        if st.session_state.pdf_content:
            system_prompt += (
                "\nVocê analisou um documento PDF. A seguir, a conversa deve levar em consideração o"
                f" conteúdo do PDF para responder às perguntas. Conteúdo do PDF (limitado): {st.session_state.pdf_content[:4000]}"
            )
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(st.session_state.message_history[-20:])  # Envia as últimas 20 mensagens do histórico
        messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model=current_model,
            messages=messages,
            max_tokens=max_tokens,
        )
        answer = response.choices[0].message.content

        st.session_state.message_history.append({"role": "assistant", "content": answer})
        save_chat_history()  # Salva o histórico após receber a resposta
        return answer
    except Exception as e:
        st.error(f"Ocorreu um erro: {str(e)}")
        return None

def analyze_pdf_get_response(file_path):
    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            pdf_content = ""
            # Limit to first 20 pages to prevent API overload
            for page_num in range(min(20, len(reader.pages))):
                pdf_content += reader.pages[page_num].extract_text() or ""
            
            # Store full content for context - but limit it
            st.session_state.pdf_content = pdf_content[:20000]
            
            # Improve analysis with better prompting
            file_name = os.path.basename(file_path)
            total_pages = len(reader.pages)
            
            analysis_prompt = (
                f"{tones[st.session_state.tone_var]} Você é um especialista em análise de documentos. "
                f"Analise este documento PDF de {total_pages} páginas chamado '{file_name}' e forneça: "
                f"1. Um resumo executivo do conteúdo (máx. 3 parágrafos)\n"
                f"2. Os principais pontos ou conclusões do documento (tópicos)\n"
                f"3. Identificação de informações importantes como datas, valores monetários, e termos técnicos relevantes\n"
                f"4. Se for um documento contábil ou financeiro, identifique valores, períodos fiscais, e obrigações\n"
                f"Conteúdo do documento: {pdf_content[:10000]}"
            )

        # Use direct API calls instead of get_ai_response to avoid adding to history
        if st.session_state.model_var.startswith("gemini"):
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(st.session_state.model_var)
            response = model.generate_content(analysis_prompt)
            response_text = response.text if hasattr(response, "text") else "Resposta não suportada"
        else:
            messages = [{"role": "system", "content": tones[st.session_state.tone_var]}]
            messages.append({"role": "user", "content": analysis_prompt})
            response = client.chat.completions.create(
                model=st.session_state.model_var,
                messages=messages,
                max_tokens=int(st.session_state.max_tokens),
            )
            response_text = response.choices[0].message.content
            
        return response_text

    except Exception as e:
        st.error(f"Erro ao analisar PDF: {str(e)}")
        return f"Erro ao analisar PDF: {str(e)}"

def compare_pdfs_get_response(file_paths):
    try:
        pdf_contents = []
        filenames = []
        for file_path in file_paths:
            filenames.append(os.path.basename(file_path))
            content = ""
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                # Limit to first 10 pages per PDF
                for page_num in range(min(10, len(reader.pages))):
                    content += reader.pages[page_num].extract_text() or ""
            pdf_contents.append(content[:8000])  # Limit PDF content more

        current_tone = st.session_state.tone_var
        comparison_prompt = (
            f"{tones[current_tone]} Compare os seguintes dois documentos PDF, destacando semelhanças e"
            " diferenças, e fornecendo um resumo comparativo. Documento 1:"
            f" {filenames[0]} Conteúdo: {pdf_contents[0]} Documento 2: {filenames[1]} Conteúdo:"
            f" {pdf_contents[1]}"
        )
        print("Debug: compare_pdfs_get_response - Antes da resposta da IA")
        
        # Use direct API calls instead of get_ai_response
        if st.session_state.model_var.startswith("gemini"):
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(st.session_state.model_var)
            response = model.generate_content(comparison_prompt)
            response_text = response.text if hasattr(response, "text") else "Resposta não suportada"
        else:
            messages = [{"role": "system", "content": tones[st.session_state.tone_var]}]
            messages.append({"role": "user", "content": comparison_prompt})
            response = client.chat.completions.create(
                model=st.session_state.model_var,
                messages=messages,
                max_tokens=int(st.session_state.max_tokens),
            )
            response_text = response.choices[0].message.content
            
        print("Debug: compare_pdfs_get_response - Depois da resposta da IA")
        return response_text

    except Exception as e:
        st.error(f"Erro ao comparar PDFs: {str(e)}")
        return f"Erro ao comparar PDFs: {str(e)}"

def analyze_multiple_pdfs_content_get_response(file_paths):
    try:
        pdf_contents = []
        filenames = []
        
        # Limit to first 5 PDFs to prevent API overload
        file_paths = file_paths[:5]
        
        for file_path in file_paths:
            filenames.append(os.path.basename(file_path))
            content = ""
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                # Limit to first 5 pages per PDF
                for page_num in range(min(5, len(reader.pages))):
                    content += reader.pages[page_num].extract_text() or ""
            # Limit content size per PDF
            pdf_contents.append(content[:5000])

        current_tone = st.session_state.tone_var
        multi_analysis_prompt = (
            f"{tones[current_tone]} Analise os seguintes {len(file_paths)} documentos PDF e forneça um resumo geral, "
            "identificando temas comuns, diferenças importantes e insights gerais. Documentos: "
        )
        
        # Add each document with limited content
        for i, (name, content) in enumerate(zip(filenames, pdf_contents)):
            multi_analysis_prompt += f"\n\nDocumento {i+1}: {name}\nResumo do conteúdo: {content[:3000]}..."

        print("Debug: analyze_multiple_pdfs_content_get_response - Antes da resposta da IA")
        
        # Use a direct approach instead of get_ai_response to avoid adding to history
        if st.session_state.model_var.startswith("gemini"):
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(st.session_state.model_var)
            response = model.generate_content(multi_analysis_prompt)
            response_text = response.text if hasattr(response, "text") else "Resposta não suportada"
        else:
            messages = [{"role": "system", "content": tones[st.session_state.tone_var]}]
            messages.append({"role": "user", "content": multi_analysis_prompt})
            response = client.chat.completions.create(
                model=st.session_state.model_var,
                messages=messages,
                max_tokens=int(st.session_state.max_tokens),
            )
            response_text = response.choices[0].message.content
            
        print("Debug: analyze_multiple_pdfs_content_get_response - Depois da resposta da IA")
        return response_text

    except Exception as e:
        st.error(f"Erro ao analisar PDFs: {str(e)}")
        return f"Erro ao analisar PDFs: {str(e)}"


def new_conversation():
    st.session_state.message_history = []
    st.session_state.pdf_content = "" # Limpa pdf_content na nova conversa
    save_chat_history()
    display_message("Sistema", "Nova conversa iniciada.", "system")

def export_insights():
    full_chat_text = ""
    for message in st.session_state.message_history:
        role = message["role"]
        content = message["content"]
        if role == "user":
            full_chat_text += f"Você: {content}\n\n"
        elif role == "assistant":
            full_chat_text += f"{get_bot_name()}: {content}\n\n"

    if full_chat_text:
        st.download_button(
            label="Download Conversa",
            data=full_chat_text,
            file_name="chat_insights.txt",
            mime="text/plain",
        )
    else:
        st.warning("Nenhuma conversa para exportar.")

def load_chat_history():
    try:
        if os.path.exists(st.session_state.chat_history_file):
            with open(st.session_state.chat_history_file, "r", encoding="utf-8") as f:
                st.session_state.message_history = json.load(f)
            print("Histórico de chat carregado.")
    except Exception as e:
        print(f"Erro ao carregar histórico de chat: {e}")

def save_chat_history():
    try:
        with open(st.session_state.chat_history_file, "w", encoding="utf-8") as f:
            json.dump(st.session_state.message_history, f, ensure_ascii=False, indent=2)
        print("Histórico de chat salvo.")
    except Exception as e:
        print(f"Erro ao salvar histórico de chat: {e}")

load_chat_history()

# --- LAYOUT TOP AREA ---
st.markdown('<div class="title-area">', unsafe_allow_html=True)
col_title, col_actions = st.columns([6, 4])  # Changed column ratio for better spacing
with col_title:
    st.title("💬 GB Intelligence")  # Novo nome com ícone representativo
with col_actions:
    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if st.button("Nova Conversa", use_container_width=True):
            new_conversation()
            st.session_state.pdf_content = ""
            st.rerun()
    with action_col2:
        if st.button("Exportar", use_container_width=True):
            export_insights()
st.markdown('</div>', unsafe_allow_html=True)

# Replace the sidebar code with this organized version using expanders
with st.sidebar:
    st.header("GB Intelligence - Menu")  # Atualizado com o novo nome
    
    # Chat Settings Expander
    with st.expander("⚙️ Configurações do Chat", expanded=False):
        st.subheader("Tom da Conversa")
        tone_var = st.selectbox("Selecione o Tom:", list(tones.keys()), index=list(tones.keys()).index(st.session_state.tone_var))
        st.session_state.tone_var = tone_var
        st.write(f"**Descrição do Tom:** {tones[st.session_state.tone_var]}")

        st.subheader("Modelo de IA")
        model_var = st.selectbox("Selecione o Modelo:", list(models.keys()), index=list(models.keys()).index(st.session_state.model_var))
        st.session_state.model_var = model_var
        st.write(f"**Descrição do Modelo:** {models[st.session_state.model_var]}")
        
        st.subheader("Tokens")
        max_tokens_input = st.number_input("Máximo de Tokens:", value=st.session_state.max_tokens, min_value=100, step=100)
        st.session_state.max_tokens = max_tokens_input

    # Appearance Settings Expander
    with st.expander("🎨 Aparência", expanded=False):
        st.subheader("Fonte")
        font_family_var = st.selectbox("Família da Fonte:", ["Arial", "Helvetica", "Times New Roman", "Courier", "Verdana", "Roboto"], index=["Arial", "Helvetica", "Times New Roman", "Courier", "Verdana", "Roboto"].index(st.session_state.font_family))
        st.session_state.font_family = font_family_var
        font_size_var = st.selectbox("Tamanho da Fonte:", ["10", "12", "14", "16", "18", "20"], index=["10", "12", "14", "16", "18", "20"].index(str(st.session_state.font_size)))
        st.session_state.font_size = int(font_size_var)

    # PDF Analysis Expander (highlighted)
    with st.expander("📄 Análise de PDFs", expanded=False):
        st.markdown("### 📊 Análise de PDF Individual")
        pdf_file = st.file_uploader("Anexar PDF para análise:", type=["pdf"], key="sidebar_pdf_upload")
        if pdf_file:
            if st.button("Analisar PDF", key="sidebar_analisar_pdf_btn", use_container_width=True):
                with st.spinner('Analisando PDF...'):
                    temp_file_path = f"temp_{pdf_file.name}"
                    with open(temp_file_path, "wb") as f:
                        f.write(pdf_file.read())
                    st.session_state.pdf_analysis_result = analyze_pdf_get_response(temp_file_path)
                    os.remove(temp_file_path)
                    st.rerun()

        st.markdown("### 🔍 Comparação de PDFs")
        pdf_files_compare = st.file_uploader("Anexar 2 PDFs para comparar:", type=["pdf"], accept_multiple_files=True, key="sidebar_pdf_compare_uploader")
        if len(pdf_files_compare) == 2:
            if st.button("Comparar PDFs", key="sidebar_comparar_pdf_btn", use_container_width=True):
                with st.spinner('Comparando PDFs...'):
                    temp_file_paths = []
                    for pdf_file in pdf_files_compare:
                        temp_file_path = f"temp_{pdf_file.name}"
                        with open(temp_file_path, "wb") as f:
                            f.write(pdf_file.read())
                        temp_file_paths.append(temp_file_path)
                    st.session_state.pdf_comparison_result = compare_pdfs_get_response(temp_file_paths)
                    for path in temp_file_paths:
                        os.remove(path)
                    st.rerun()

        st.markdown("### 📚 Análise Múltipla")
        pdf_files_analyze_multiple = st.file_uploader("Anexar PDFs (máx 10):", type=["pdf"], accept_multiple_files=True, key="sidebar_pdf_multi_uploader")
        if pdf_files_analyze_multiple and len(pdf_files_analyze_multiple) <= 10:
            if st.button("Analisar Múltiplos PDFs", key="sidebar_analisar_multi_pdf_btn", use_container_width=True):
                with st.spinner('Analisando Múltiplos PDFs...'):
                    temp_file_paths = []
                    for pdf_file in pdf_files_analyze_multiple:
                        temp_file_path = f"temp_{pdf_file.name}"
                        with open(temp_file_path, "wb") as f:
                            f.write(pdf_file.read())
                        temp_file_paths.append(temp_file_path)
                    st.session_state.pdf_multi_analysis_result = analyze_multiple_pdfs_content_get_response(temp_file_paths)
                    for path in temp_file_paths:
                        os.remove(path)
                    st.rerun()
        elif pdf_files_analyze_multiple and len(pdf_files_analyze_multiple) > 10:
            st.warning("Selecione no máximo 10 arquivos PDF para análise múltipla.", icon="⚠️")

# Exibir histórico do chat e resultados da análise de PDF NA ÁREA PRINCIPAL
for index, msg in enumerate(st.session_state.message_history): # Index parameter is no longer used, enumerate still needed
    role = msg["role"]
    content = msg["content"]
    if role == "user":
        display_message("Você", content, "user", index)  # Add index to make IDs unique
    elif role == "assistant":
        display_message(get_bot_name(), content, "bot", index)  # Add index to make IDs unique
    elif role == "system":
        display_message("Sistema", content, "system", index)  # Add index to make IDs unique

# PRINT DEBUG ANTES DO DISPLAY_MESSAGE NA AREA PRINCIPAL
if st.session_state.pdf_analysis_result: # Verifica se NÃO é None
    print("Debug: Área Principal - Antes do display_message - pdf_analysis_result") # PRINT DEBUG
    # Adicionar um prefixo para identificar claramente que isso é uma análise de PDF
    prefixed_result = "### 📊 ANÁLISE DO PDF:\n\n" + st.session_state.pdf_analysis_result
    display_message(get_bot_name(), prefixed_result, "bot", is_pdf_analysis=True)
    # Não limpar o resultado, apenas manter uma cópia no histórico se precisar
    st.session_state.pdf_analysis_result = None

# Exibe o resultado da comparação de PDFs se existir NOVO resultado no session_state
if st.session_state.pdf_comparison_result: # Verifica se NÃO é None
    print("Debug: Área Principal - Antes do display_message - pdf_comparison_result") # PRINT DEBUG
    # Adicionar um prefixo para identificar claramente que isso é uma comparação de PDFs
    prefixed_result = "### 🔍 COMPARAÇÃO DE PDFs:\n\n" + st.session_state.pdf_comparison_result
    display_message(get_bot_name(), prefixed_result, "bot", is_pdf_analysis=True)
    st.session_state.pdf_comparison_result = None

# Exibe o resultado da análise múltipla de PDFs se existir NOVO resultado no session_state
if st.session_state.pdf_multi_analysis_result: # Verifica se NÃO é None
    print("Debug: Área Principal - Antes do display_message - pdf_multi_analysis_result") # PRINT DEBUG
    # Adicionar um prefixo para identificar claramente que isso é uma análise múltipla
    prefixed_result = "### 📚 ANÁLISE DE MÚLTIPLOS PDFs:\n\n" + st.session_state.pdf_multi_analysis_result
    display_message(get_bot_name(), prefixed_result, "bot", is_pdf_analysis=True)
    st.session_state.pdf_multi_analysis_result = None


# Adicione o botão toggle perto do campo de entrada
if prompt := st.chat_input("Digite sua mensagem aqui..."):
    if prompt and len(prompt) <= max_input_chars:
        display_message("Você", prompt, "user")
        st.session_state.message_history.append({"role": "user", "content": prompt})
        save_chat_history()

        with st.spinner(f'Pensando como {get_bot_name()}...'):
            ai_response = get_ai_response(prompt)
            if ai_response:
                display_message(get_bot_name(), ai_response, "bot")
    elif len(prompt) > max_input_chars:
        st.warning(f"Sua mensagem excede o limite de {max_input_chars} caracteres.")