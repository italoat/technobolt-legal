import streamlit as st
import google.generativeai as genai
import os
import time
import docx
import PyPDF2
import pandas as pd
from io import BytesIO
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# --- 1. CONFIGURAÇÃO DE SEGURANÇA E PROTOCOLO ---
st.set_page_config(
    page_title="TechnoBolt Legal - Juris Intelligence",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. GESTÃO DE ESTADO (INICIALIZAÇÃO BLINDADA) ---
chaves_sessao = {
    'logged_in': False,
    'user_atual': None,
    'perfil_cliente': {
        "nome_empresa": "TechnoBolt Legal",
        "setor": "Escritórios de Advocacia de Elite",
        "tom_voz": "Formal, Analítico e Preciso"
    },
    'uso_sessao': {},
    'mostrar_resultado': False,
    'resultado_ia': "",
    'titulo_resultado': "",
    'login_time': time.time()
}

for chave, valor in chaves_sessao.items():
    if chave not in st.session_state:
        st.session_state[chave] = valor

# --- 3. SISTEMA DE AUDITORIA E EXTRAÇÃO ---
def registrar_evento(funcao):
    if 'uso_sessao' not in st.session_state: st.session_state.uso_sessao = {}
    st.session_state.uso_sessao[funcao] = st.session_state.uso_sessao.get(funcao, 0) + 1

def extrair_texto_pdf(arquivo):
    try:
        pdf_reader = PyPDF2.PdfReader(arquivo)
        texto = ""
        for page in pdf_reader.pages:
            content = page.extract_text()
            if content: texto += content + "\n"
        return texto
    except: return "[Erro na extração de PDF]"

def extrair_texto_docx(arquivo):
    try:
        doc = docx.Document(arquivo)
        return "\n".join([p.text for p in doc.paragraphs])
    except: return "[Erro na extração de DOCX]"

def preparar_anexo_ia(arquivo):
    if arquivo is None: return ""
    if arquivo.type == "application/pdf": return extrair_texto_pdf(arquivo)
    elif arquivo.name.endswith('.docx'): return extrair_texto_docx(arquivo)
    else: return arquivo.read().decode(errors='ignore')

# --- 4. MOTOR DE INTELIGÊNCIA COM FAILOVER PENTACAMADA ---
MODEL_FAILOVER_LIST = [
    "models/gemini-3-flash-preview", 
    "models/gemini-2.5-flash", 
    "models/gemini-2.0-flash", 
    "models/gemini-2.0-flash-lite", 
    "models/gemini-flash-latest"
]

def call_technobolt_ai(prompt, attachments=None, system_context="default"):
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key: genai.configure(api_key=api_key)
    
    dna_context = f"SISTEMA: TechnoBolt Legal | PÚBLICO: Escritórios de Advocacia | TOM: Formal e Preciso.\n\n"

    contexts = {
        "prazos": "Você é um Controller Jurídico sênior. Analise a intimação: identifique o Ato, as datas e calcule o prazo fatal em dias úteis (CPC/15). Gere tabela com Evento, Prazo, Data Fatal e Artigo da Lei.",
        "analisador": "Aja como Advogado Estrategista em litígios complexos. Analise petições e provas buscando contradições fáticas e inconsistências de nexo causal. Liste 'Pontos de Ataque' por relevância.",
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
        except: continue
    return "⚠️ Motores de IA Offline.", "OFFLINE"

# --- 5. DESIGN SYSTEM (ESTÉTICA HUB ORIGINAL COM RESULTADO DARK) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [data-testid="stAppViewContainer"] { background-color: #f8fafc !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { display: none !important; }
    header, footer { visibility: hidden !important; }
    .main-card {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 24px;
        padding: 45px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.04); margin-bottom: 30px;
    }
    .result-card-dark {
        background: #1e293b !important; border: 1px solid #334155; border-radius: 24px;
        padding: 45px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2); margin-bottom: 30px;
        color: #f1f5f9 !important;
    }
    .hero-title {
        font-size: 42px; font-weight: 800; text-align: center;
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        letter-spacing: -2px; margin-bottom: 10px;
    }
    .stButton > button {
        width: 100%; border-radius: 14px; height: 3.8em; font-weight: 700;
        background: #1e40af !important; color: white !important; border: none !important;
        text-transform: uppercase; letter-spacing: 1.5px; transition: 0.4s;
    }
    .stButton > button:hover { background: #1e3a8a !important; transform: translateY(-2px); }
    .status-badge {
        padding: 6px 18px; border-radius: 50px; background: #eff6ff; 
        color: #1e40af; font-size: 12px; font-weight: 700; border: 1px solid #dbeafe;
    }
</style>
""", unsafe_allow_html=True)

# --- 6. TELA DE LOGIN ---
if not st.session_state.logged_in:
    st.markdown("<div style='height: 12vh;'></div>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1.4, 1])
    with col_login:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown("<h1 class='hero-title'>TECHNOBOLT</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#64748b; margin-bottom:40px;'>LEGAL SYSTEM - INTELIGÊNCIA JURÍDICA</p>", unsafe_allow_html=True)
        user_id = st.text_input("Credencial", placeholder="Usuário")
        user_key = st.text_input("Chave", type="password", placeholder="Senha")
        if st.button("CONECTAR"):
            banco_users = {"admin": "admin", "anderson.bezerra": "teste@2025", "fabricio.felix": "teste@2025", "jackson.antonio": "teste@2025", "luiza.trovao": "teste@2025"}
            if user_id in banco_users and banco_users[user_id] == user_key:
                st.session_state.logged_in, st.session_state.user_atual, st.session_state.login_time = True, user_id, time.time()
                st.rerun()
    st.stop()

# --- 7. CABEÇALHO ---
st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
h1, h2 = st.columns([4, 1.2])
with h1: st.markdown(f"**ADVOGADO:** <span class='status-badge'>{st.session_state.user_atual.upper()}</span>", unsafe_allow_html=True)
with h2: 
    if st.button("🚪 Sair do Hub"): 
        st.session_state.logged_in = False
        st.rerun()

menu = ["🏠 Dashboard", "📅 Auditor de Prazos", "🔍 Analisador de Petições", "⚖️ Jurisprudência", "📝 Revisor de Contratos", "📊 Legal Analytics"]
escolha = st.selectbox("Seletor de Módulo", menu, label_visibility="collapsed")
st.markdown("<hr style='margin: 10px 0 35px 0; border: 0.5px solid #e2e8f0;'>", unsafe_allow_html=True)

# --- 8. MÓDULOS OPERACIONAIS ---

if "Dashboard" in escolha:
    st.markdown('<div class="main-card"><h1>Legal Command Center</h1><p>MONITORIA DE RISCO E EFICIÊNCIA PROCESSUAL</p></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Failover Status", "Active", "Redundância 5/5")
    c2.metric("Sessão", st.session_state.user_atual.split('.')[0].upper(), "Protegida")
    c3.metric("Win Rate", "84%", "Consolidado")

elif "Auditor de Prazos" in escolha:
    st.markdown('<div class="main-card"><h2>📅 Auditor de Prazos</h2><p>Identificação de atos e contagem automática em dias úteis.</p></div>', unsafe_allow_html=True)
    txt = st.text_area("Texto da Publicação ou Intimação:", height=200)
    if st.button("CALCULAR PRAZO FATAL"):
        registrar_evento("Auditoria Prazos")
        with st.spinner("Analisando publicação..."):
            res, _ = call_technobolt_ai(f"Analise esta publicação:\n{txt}", system_context="prazos")
            st.session_state.update({'titulo_resultado': "Relatório de Prazo Processual", 'resultado_ia': res, 'mostrar_resultado': True})
            st.rerun()

elif "Analisador de Petições" in escolha:
    st.markdown('<div class="main-card"><h2>🔍 Analisador de Petições e Provas</h2><p>Busca de contradições fáticas e validação de argumentos.</p></div>', unsafe_allow_html=True)
    f1 = st.file_uploader("Suba a Petição (PDF/DOCX)", type=['pdf', 'docx'])
    f2 = st.file_uploader("Suba as Provas (PDF)", type=['pdf'])
    if f1 and st.button("EXECUTAR RAIO-X"):
        registrar_evento("Análise Tática")
        with st.spinner("Cruzando dados..."):
            t1, t2 = preparar_anexo_ia(f1), preparar_anexo_ia(f2) if f2 else "Sem provas."
            res, _ = call_technobolt_ai(f"Petição: {t1}\nProvas: {t2}", system_context="analisador")
            st.session_state.update({'titulo_resultado': "Dossiê de Vulnerabilidades", 'resultado_ia': res, 'mostrar_resultado': True})
            st.rerun()

elif "Jurisprudência" in escolha:
    st.markdown('<div class="main-card"><h2>⚖️ Dossiê de Jurisprudência Semântica</h2><p>Busca de precedentes e estratégia por magistrado.</p></div>', unsafe_allow_html=True)
    caso = st.text_area("Descreva o caso concreto:")
    juiz = st.text_input("Nome do Juiz ou Relator (Opcional):")
    if st.button("GERAR ESTRATÉGIA"):
        registrar_evento("Busca Jurisprudencial")
        res, _ = call_technobolt_ai(f"Caso: {caso}\nJulgador: {juiz}", system_context="jurisprudencia")
        st.session_state.update({'titulo_resultado': "Estratégia de Precedentes", 'resultado_ia': res, 'mostrar_resultado': True})
        st.rerun()

elif "Revisor de Contratos" in escolha:
    st.markdown('<div class="main-card"><h2>📝 Revisor de Contratos (Massa)</h2><p>Auditoria simultânea de conformidade e riscos.</p></div>', unsafe_allow_html=True)
    files = st.file_uploader("Upload de Contratos", accept_multiple_files=True, type=['pdf', 'docx'])
    if files and st.button("INICIAR AUDITORIA"):
        registrar_evento("Auditoria Contratos")
        results, bar = [], st.progress(0)
        for i, f in enumerate(files):
            res, _ = call_technobolt_ai(preparar_anexo_ia(f), system_context="contratos")
            results.append(f"### Arquivo: {f.name}\n{res}\n---")
            bar.progress((i + 1) / len(files))
        st.session_state.update({'titulo_resultado': "Relatório de Risco Contratual", 'resultado_ia': "\n".join(results), 'mostrar_resultado': True})
        st.rerun()

elif "Legal Analytics" in escolha:
    st.markdown('<div class="main-card"><h2>📊 Legal Analytics</h2><p>Jurimetria e estatísticas estratégicas.</p></div>', unsafe_allow_html=True)
    dados = st.text_area("Cole os dados brutos ou tabela de processos:")
    if st.button("GERAR INSIGHTS"):
        registrar_evento("Analytics Jurídico")
        res, _ = call_technobolt_ai(dados, system_context="analytics")
        st.session_state.update({'titulo_resultado': "Análise Jurimetrista", 'resultado_ia': res, 'mostrar_resultado': True})
        st.rerun()

# --- 9. RESULTADO (CARD ESCURO CENTRALIZADO) ---
if st.session_state.get('mostrar_resultado'):
    st.markdown("---")
    _, col_central, _ = st.columns([1, 8, 1])
    with col_central:
        st.markdown(f"""
            <div class="result-card-dark">
                <h2 style="color: #60a5fa; margin-bottom: 20px;">{st.session_state.titulo_resultado}</h2>
                <div style="white-space: pre-wrap; line-height: 1.6; font-size: 15px; color: #cbd5e1;">
                    {st.session_state.resultado_ia}
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("✖️ LIMPAR E FECHAR"):
            st.session_state.mostrar_resultado = False
            st.rerun()

st.caption(f"TechnoBolt Legal © 2026 | Juris Intel v2.0 | Operador: {st.session_state.user_atual.upper()}")
