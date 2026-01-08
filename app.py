import streamlit as st
import google.generativeai as genai
import os
import time
import docx
import PyPDF2
import pandas as pd
from io import BytesIO

# --- 1. CONFIGURAÇÃO DE SEGURANÇA E PROTOCOLO (TECHNOBOLT LEGAL) ---
st.set_page_config(
    page_title="TechnoBolt Legal - Inteligência Jurídica",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. GESTÃO DE ESTADO (MANTENDO USUÁRIOS E LOGIN) ---
chaves_sessao = {
    'logged_in': False,
    'user_atual': None,
    'uso_sessao': {},
    'mostrar_resultado': False,
    'resultado_ia': "",
    'titulo_resultado': "",
    'login_time': time.time()
}

for chave, valor in chaves_sessao.items():
    if chave not in st.session_state:
        st.session_state[chave] = valor

# --- 3. MOTOR DE EXTRAÇÃO DE DOCUMENTOS (PROCESSAMENTO DE ARQUIVOS) ---
def extrair_texto_pdf(arquivo):
    try:
        pdf_reader = PyPDF2.PdfReader(arquivo)
        texto = ""
        for page in pdf_reader.pages:
            content = page.extract_text()
            if content: texto += content + "\n"
        return texto
    except:
        return "[Erro na extração de PDF]"

def extrair_texto_docx(arquivo):
    try:
        doc = docx.Document(arquivo)
        return "\n".join([p.text for p in doc.paragraphs])
    except:
        return "[Erro na extração de DOCX]"

def preparar_anexo_ia(arquivo):
    if arquivo is None: return ""
    if arquivo.type == "application/pdf":
        return extrair_texto_pdf(arquivo)
    elif arquivo.name.endswith('.docx'):
        return extrair_texto_docx(arquivo)
    else:
        return arquivo.read().decode(errors='ignore')

# --- 4. MOTOR DE INTELIGÊNCIA COM FAILOVER PENTACAMADA (MOTORES ORIGINAIS) ---
MODEL_FAILOVER_LIST = [
    "models/gemini-3-flash-preview", 
    "models/gemini-2.5-flash", 
    "models/gemini-2.0-flash", 
    "models/gemini-2.0-flash-lite", 
    "models/gemini-flash-latest"
]

def call_technobolt_legal_ai(prompt, attachments=None, system_context="default"):
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key: genai.configure(api_key=api_key)
    
    dna_context = "SISTEMA: TechnoBolt Legal | PÚBLICO: Escritórios de Advocacia | TOM: Formal, Analítico e Preciso.\n\n"

    contexts = {
        "prazos": "Aja como Controller Jurídico sênior. Analise a intimação: identifique o Ato, as datas e calcule o prazo fatal em dias úteis (CPC/15). Gere tabela com Evento, Prazo, Data Fatal e Artigo da Lei.",
        "analisador": "Aja como Advogado Estrategista. Analise petições e provas buscando contradições fáticas e inconsistências de nexo causal. Liste 'Pontos de Ataque' por relevância.",
        "jurisprudencia": "Analista de Precedentes e Jurimetria. Analise o caso e o perfil do julgador. Busque a 'Ratio Decidendi' favorável, cite 3 acórdãos espelho e sugira estratégia de convencimento.",
        "contratos": "Especialista em Compliance e LGPD. Analise contratos em busca de multas abusivas, renovação automática e conformidade de dados. Gere tabela comparativa de riscos e sugestões.",
        "analytics": "Cientista de Dados Jurídicos. Categorize processos, calcule ticket médio e identifique comarcas de alto risco para a estratégia do escritório.",
        "default": "Você é o Motor TechnoBolt Legal focado em alta performance jurídica."
    }

    final_sys_instr = dna_context + contexts.get(system_context, contexts["default"])

    for model_name in MODEL_FAILOVER_LIST:
        try:
            model = genai.GenerativeModel(model_name, system_instruction=final_sys_instr)
            payload = [prompt] + attachments if attachments else prompt
            response = model.generate_content(payload)
            return response.text, model_name
        except:
            continue
    return "⚠️ Motores de IA Offline. Contate o suporte.", "OFFLINE"

# --- 5. DESIGN SYSTEM (ESTÉTICA JURÍDICA DARK) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    html, body, [data-testid="stAppViewContainer"] { background-color: #0f172a !important; font-family: 'Inter', sans-serif !important; color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #1e293b !important; }
    .main-card {
        background: #1e293b; border: 1px solid #334155; border-radius: 20px;
        padding: 35px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); margin-bottom: 25px;
    }
    .hero-title {
        font-size: 38px; font-weight: 800; text-align: center;
        background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    .stButton > button {
        width: 100%; border-radius: 12px; height: 3.5em; font-weight: 700;
        background: #3b82f6 !important; color: white !important; border: none !important;
        text-transform: uppercase; letter-spacing: 1px; transition: 0.3s;
    }
    .stButton > button:hover { background: #2563eb !important; transform: translateY(-2px); }
</style>
""", unsafe_allow_html=True)

# --- 6. TELA DE LOGIN (USUÁRIOS ORIGINAIS) ---
if not st.session_state.logged_in:
    st.markdown("<div style='height: 12vh;'></div>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown("<h1 class='hero-title'>TECHNOBOLT LEGAL</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#94a3b8; margin-bottom:30px;'>INTELIGÊNCIA JURÍDICA DE ALTA PERFORMANCE</p>", unsafe_allow_html=True)
        
        user_id = st.text_input("Credencial", placeholder="Usuário")
        user_key = st.text_input("Chave", type="password", placeholder="Senha")

        if st.button("CONECTAR"):
            banco_users = {
                "admin": "admin",
                "anderson.bezerra": "teste@2025", 
                "fabricio.felix": "teste@2025", 
                "jackson.antonio": "teste@2025", 
                "luiza.trovao": "teste@2025"
            }
            if user_id in banco_users and banco_users[user_id] == user_key:
                st.session_state.logged_in = True
                st.session_state.user_atual = user_id
                st.session_state.login_time = time.time()
                st.rerun()
    st.stop()

# --- 7. DASHBOARD E NAVEGAÇÃO ---
with st.sidebar:
    st.markdown(f"**USUÁRIO:** `{st.session_state.user_atual.upper()}`")
    st.markdown("---")
    menu = [
        "🏠 Dashboard de Comando",
        "📅 Auditor de Prazos",
        "🔍 Analisador de Petições",
        "⚖️ Dossiê Jurisprudencial",
        "📝 Revisor de Contratos (Massa)",
        "📊 Legal Analytics"
    ]
    escolha = st.radio("Seletor de Módulo", menu)
    
    if st.button("🚪 Sair"):
        st.session_state.logged_in = False
        st.rerun()

# --- 8. MÓDULOS OPERACIONAIS ---

# --- DASHBOARD CENTRAL ---
if "Dashboard" in escolha:
    st.markdown('<div class="main-card"><h1>🏛️ Command Center</h1><p>MONITORIA JURÍDICA E ESTRATÉGIA DE LITÍGIO</p></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Riscos de Prazo", "0", "Estável")
    c2.metric("Auditorias/Mês", "342", "+15%")
    c3.metric("Win Rate Médio", "81%", "Alta Performance")

# --- 1. AUDITOR DE PRAZOS ---
elif "Auditor de Prazos" in escolha:
    st.markdown('<div class="main-card"><h2>📅 Auditor de Prazos e Intimações</h2><p>Identificação de atos e contagem automática em dias úteis.</p></div>', unsafe_allow_html=True)
    texto_pub = st.text_area("Cole a publicação ou intimação bruta aqui:", height=200)
    if st.button("CALCULAR PRAZO FATAL"):
        with st.spinner("Analisando publicação conforme CPC/15..."):
            res, _ = call_technobolt_legal_ai(f"Analise esta publicação:\n{texto_pub}", system_context="prazos")
            st.session_state.update({'titulo_resultado': "Cálculo de Prazo Processual", 'resultado_ia': res, 'mostrar_resultado': True})
            st.rerun()

# --- 2. ANALISADOR DE PETIÇÕES ---
elif "Analisador de Petições" in escolha:
    st.markdown('<div class="main-card"><h2>🔍 Analisador de Petições e Provas</h2><p>Busca de contradições fáticas e validação de argumentos.</p></div>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a: pet_file = st.file_uploader("Suba a Petição (PDF/DOCX)", type=['pdf', 'docx'])
    with col_b: prv_file = st.file_uploader("Suba as Provas (PDF)", type=['pdf'])
    
    if pet_file and st.button("INICIAR RAIO-X"):
        with st.spinner("Cruzando petição com acervo probatório..."):
            t1 = preparar_anexo_ia(pet_file)
            t2 = preparar_anexo_ia(prv_file) if prv_file else "Sem provas."
            prompt = f"PETIÇÃO:\n{t1}\n\nPROVAS:\n{t2}"
            res, _ = call_technobolt_legal_ai(prompt, system_context="analisador")
            st.session_state.update({'titulo_resultado': "Relatório de Vulnerabilidades", 'resultado_ia': res, 'mostrar_resultado': True})
            st.rerun()

# --- 3. DOSSIÊ JURISPRUDENCIAL ---
elif "Dossiê Jurisprudencial" in escolha:
    st.markdown('<div class="main-card"><h2>⚖️ Dossiê Jurisprudencial</h2><p>Busca semântica e estratégia baseada no perfil do magistrado.</p></div>', unsafe_allow_html=True)
    caso = st.text_area("Descreva o caso concreto:")
    juiz = st.text_input("Nome do Magistrado ou Tribunal:")
    if st.button("GERAR ESTRATÉGIA"):
        prompt = f"Caso: {caso}\nMagistrado: {juiz if juiz else 'Não informado'}"
        res, _ = call_technobolt_legal_ai(prompt, system_context="jurisprudencia")
        st.session_state.update({'titulo_resultado': "Dossiê de Precedentes", 'resultado_ia': res, 'mostrar_resultado': True})
        st.rerun()

# --- 4. REVISOR DE CONTRATOS ---
elif "Revisor de Contratos" in escolha:
    st.markdown('<div class="main-card"><h2>📝 Revisor de Contratos (Massa)</h2><p>Auditoria de múltiplos documentos para compliance e LGPD.</p></div>', unsafe_allow_html=True)
    arquivos = st.file_uploader("Upload de Contratos", accept_multiple_files=True, type=['pdf', 'docx'])
    if arquivos and st.button("INICIAR AUDITORIA"):
        all_res = []
        bar = st.progress(0)
        for i, arq in enumerate(arquivos):
            txt = preparar_anexo_ia(arq)
            res, _ = call_technobolt_legal_ai(f"Contrato: {arq.name}\n{txt}", system_context="contratos")
            all_res.append(f"### Arquivo: {arq.name}\n{res}\n---")
            bar.progress((i + 1) / len(arquivos))
        st.session_state.update({'titulo_resultado': "Relatório de Risco Contratual", 'resultado_ia': "\n".join(all_res), 'mostrar_resultado': True})
        st.rerun()

# --- 5. LEGAL ANALYTICS ---
elif "Legal Analytics" in escolha:
    st.markdown('<div class="main-card"><h2>📊 Legal Analytics</h2><p>Análise de probabilidade e estatísticas processuais.</p></div>', unsafe_allow_html=True)
    dados = st.text_area("Insira dados brutos de processos (ou cole tabela):")
    if st.button("GERAR INSIGHTS"):
        res, _ = call_technobolt_legal_ai(dados, system_context="analytics")
        st.session_state.update({'titulo_resultado': "Análise Jurimetrista", 'resultado_ia': res, 'mostrar_resultado': True})
        st.rerun()

# --- 9. RESULTADO CENTRALIZADO ---
if st.session_state.mostrar_resultado:
    st.markdown("---")
    st.markdown(f"""
        <div class="main-card" style="border-left: 5px solid #3b82f6;">
            <h2 style="color: #60a5fa; margin-bottom: 20px;">{st.session_state.titulo_resultado}</h2>
            <div style="background: #0f172a; padding: 25px; border-radius: 12px; white-space: pre-wrap; color: #cbd5e1; font-size: 15px;">
                {st.session_state.resultado_ia}
            </div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("✖️ FECHAR RESULTADO"):
        st.session_state.mostrar_resultado = False
        st.rerun()

st.caption(f"TechnoBolt Legal © 2026 | Operador: {st.session_state.user_atual.upper()}")
