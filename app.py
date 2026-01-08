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
    page_title="TechnoBolt IA - Legal Hub",
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
        "tom_voz": "Formal, Analítico, Técnico e Preciso"
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

# --- 3. SISTEMA DE AUDITORIA E LOGOUT ---
def enviar_notificacao_email(assunto, corpo):
    sg_key = os.environ.get("SENDGRID_API_KEY") 
    message = Mail(
        from_email='technoboltconsultoria@gmail.com',
        to_emails='technoboltconsultoria@gmail.com',
        subject=assunto,
        plain_text_content=corpo)
    try:
        sg = SendGridAPIClient(sg_key)
        sg.send(message)
        return True
    except:
        return False

def protocol_logout():
    if st.session_state.get('logged_in'):
        tempo = round((time.time() - st.session_state.get('login_time', time.time())) / 60, 2)
        relatorio = f"LOGOUT TECHNOBOLT LEGAL\nOperador: {st.session_state.user_atual}\nTempo: {tempo} min\nAções: {st.session_state.uso_sessao}"
        enviar_notificacao_email(f"Sessão Encerrada - {st.session_state.user_atual}", relatorio)
    st.session_state.logged_in = False
    st.session_state.user_atual = None
    st.session_state.uso_sessao = {}
    st.rerun()

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
    
    p = st.session_state.perfil_cliente
    dna_context = f"DNA SISTEMA: {p['nome_empresa']} | SETOR: {p['setor']} | TOM: {p['tom_voz']}\n\n"

    contexts = {
        "prazos": """Você é um Controller Jurídico de alto nível, especialista em prazos processuais e normas do CPC/15, CPP e CLT. Sua tarefa é analisar o texto da intimação fornecida. 
        Protocolo de Análise:
        1. Identifique o Ato Processual (ex: Sentença, Acórdão, Despacho de Mero Expediente).
        2. Identifique a Data de Publicação e a Data de Ciência.
        3. Determine o Tipo de Prazo (ex: Recurso Apelação, Embargos, Manifestação sobre Provas).
        4. Contagem de Dias: Considere apenas dias úteis conforme a legislação atual, alertando sobre feriados nacionais.
        5. Saída Esperada: Gere uma tabela contendo: Evento, Prazo em Dias, Data Estimada de Protocolo e Fundamento Legal (Artigo da Lei).""",
        
        "analisador": """Aja como um Advogado Estrategista com foco em litígios complexos. Analise os documentos anexados (Petições e Provas) buscando inconsistências.
        Protocolo de Auditoria:
        1. Contradições Internas: Verifique se o que foi alegado nos fatos coincide com os pedidos e com os documentos anexados.
        2. Validação de Provas: O print de WhatsApp ou extrato bancário realmente prova o que o texto afirma? Aponte 'falhas de nexo causal'.
        3. Teoria do Adversário: Identifique o argumento central da contraparte e sugira 3 contra-argumentos baseados nas falhas encontradas.
        4. Saída: Um relatório de 'Pontos de Ataque' dividido por relevância (Alta, Média, Baixa).""",
        
        "jurisprudencia": """Você é um Analista de Precedentes e Jurimetria. Sua missão é estruturar uma tese vencedora.
        Protocolo de Busca:
        1. Analise o Caso Concreto enviado pelo usuário.
        2. Busque por Ratio Decidendi (razão de decidir) em casos análogos, priorizando tribunais superiores (STJ/STF).
        3. Perfil do Julgador: Se um magistrado for citado, analise como ele costuma decidir sobre o tema (conservador, progressista, garantista).
        4. Saída: Forneça o resumo de 3 acórdãos 'espelho', destaque as palavras-chave que o juiz gosta de ler e sugira a melhor estratégia de convencimento.""",
        
        "contratos": """Você é um Especialista em Direito Contratual e Compliance/LGPD. Analise o lote de contratos em busca de riscos invisíveis.
        Critérios de Revisão:
        1. Cláusulas de Saída: Identifique multas de rescisão abusivas ou renovações automáticas sem aviso.
        2. Privacidade: Verifique se há cláusula específica de LGPD e se está adequada ao tratamento de dados da empresa.
        3. Equilíbrio Econômico: Busque por índices de reajuste obsoletos ou desequilíbrio entre as partes.
        4. Saída: Gere uma tabela comparativa: [Nome do Arquivo] | [Nível de Risco 1-10] | [Cláusula Crítica] | [Sugestão de Redação].""",
        
        "analytics": """Aja como um Cientista de Dados especializado no mercado jurídico brasileiro. Sua tarefa é limpar e categorizar dados brutos de processos.
        Objetivo de Análise:
        1. Categorize os processos por Objeto (ex: Danos Morais, Trabalhista, Tributário).
        2. Identifique o Ticket Médio das condenações ou pedidos.
        3. Mapa de Calor: Identifique em quais comarcas ou varas o escritório tem pior desempenho.
        4. Conclusão Estratégica: Informe onde vale a pena propor acordo imediato para evitar custos de sucumbência.""",
        
        "default": "Você é o Motor TechnoBolt focado em escritórios de advocacia de elite. Respostas técnicas e estruturadas."
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

# --- 5. DESIGN SYSTEM (DARK MODE ABSOLUTO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* 1. FUNDO GLOBAL PRETO E FONTES BRANCAS */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { 
        background-color: #000000 !important; 
        font-family: 'Inter', sans-serif !important; 
        color: #ffffff !important;
    }

    h1, h2, h3, h4, p, label, span, div, .stMarkdown { color: #ffffff !important; }
    [data-testid="stSidebar"] { display: none !important; }
    header, footer { visibility: hidden !important; }
    .login-header {
        text-align: center;
        width: 100%;
        margin-bottom: 40px;
    }
    .login-logo-blue {
        font-size: 52px; font-weight: 800;
        color: #3b82f6 !important; 
        letter-spacing: -2px;
        display: block;
    }
    
    /* 2. BARRA DE SERVIÇOS (SELECTBOX) - REFINAMENTO TOTAL */
    /* Fundo da caixa fechada */
    div[data-baseweb="select"] > div {
        background-color: #1a1a1a !important;
        border: 1px solid #333333 !important;
        border-radius: 12px !important;
        color: #ffffff !important;
    }

    /* Menu suspenso quando aberto (remover branco) */
    div[data-baseweb="popover"] > div,
    div[role="listbox"],
    ul[role="listbox"] {
        background-color: #1a1a1a !important;
        border: 1px solid #333333 !important;
        color: #ffffff !important;
    }

    /* Itens individuais da lista */
    li[role="option"] {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        transition: 0.2s;
    }

    /* Item selecionado ou hover */
    li[role="option"]:hover, 
    li[data-baseweb="typeahead-highlighted"] {
        background-color: #3b82f6 !important;
        color: #ffffff !important;
    }

    /* 3. FILE UPLOADER (REMOVER BRANCO E AJUSTAR BOTÃO) */
    [data-testid="stFileUploader"] {
        background-color: #1a1a1a !important;
        border: 1px dashed #404040 !important;
        border-radius: 15px !important;
        padding: 10px;
    }

    /* Botão 'Browse files' */
    [data-testid="stFileUploader"] button {
        background-color: #333333 !important;
        color: #ffffff !important;
        border: 1px solid #444444 !important;
        border-radius: 8px !important;
    }

    [data-testid="stFileUploader"] button:hover {
        background-color: #3b82f6 !important;
        border-color: #ffffff !important;
    }

    /* Área interna do uploader */
    [data-testid="stFileUploader"] section {
        background-color: #1a1a1a !important;
    }

    /* 4. CARDS E CONTAINERS */
    .main-card {
        background-color: #1a1a1a !important; 
        border: 1px solid #333333; 
        border-radius: 20px;
        padding: 40px; 
        margin-bottom: 25px;
    }

    /* 5. CARD DE RESULTADO UNIFICADO */
   .result-card-unificado {
        background-color: #1a1a1a !important;
        border: 1px solid #333333;
        border-radius: 20px;
        padding: 35px;
        margin-top: 20px;
        color: #ffffff !important;
        width: 100%;
        display: block;
        overflow: visible; /* Permite que o card cresça com o texto */
    }
    
    .result-title {
        color: #3b82f6 !important;
        font-weight: 800;
        font-size: 28px;
        margin-bottom: 20px;
        border-bottom: 1px solid #333333;
        padding-bottom: 15px;
    }
    /* 6. BOTÕES GERAIS */
    .stButton > button {
        width: 100%; border-radius: 10px; height: 3.5em; font-weight: 700;
        background-color: #1a1a1a !important; color: #ffffff !important; 
        border: 1px solid #333333 !important; transition: 0.3s;
    }
    .stButton > button:hover { background-color: #3b82f6 !important; border-color: #ffffff !important; }

    /* Ajuste para inputs de texto e área de texto */
    div[data-baseweb="input"] > div, 
    div[data-baseweb="textarea"] > div {
        background-color: #1a1a1a !important;
        border: 1px solid #333333 !important;
        color: #ffffff !important;
    }
    
    input, textarea {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 6. TELA DE LOGIN ---
if not st.session_state.logged_in:
    st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown('<div class="login-header"><span class="login-logo-blue">Technobolt</span></div>', unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#888;'>LEGAL HUB - JURIS INTELLIGENCE</p>", unsafe_allow_html=True)
        u_id = st.text_input("Operador", placeholder="Usuário")
        u_key = st.text_input("Chave", type="password", placeholder="Senha")
        if st.button("CONECTAR AO HUB"):
            banco = {"admin": "admin", "anderson.bezerra": "teste@2025", "fabricio.felix": "teste@2025", "jackson.antonio": "teste@2025", "luiza.trovao": "teste@2025"}
            if u_id in banco and banco[u_id] == u_key:
                st.session_state.logged_in, st.session_state.user_atual, st.session_state.login_time = True, u_id, time.time()
                enviar_notificacao_email("Login Hub", f"Advogado {u_id} acessou.")
                st.rerun()
    st.stop()

# --- 7. CABEÇALHO ---
st.markdown('<div class="hero-container"><span class="hero-title-blue">Technobolt</span></div>', unsafe_allow_html=True)
c1, c2 = st.columns([4, 1])
with c1: st.write(f"💼 Operador: **{st.session_state.user_atual.upper()}**")
with c2: 
    if st.button("🚪 Sair"): protocol_logout()

menu = ["🏠 Dashboard", "📅 Auditor de Prazos", "🔍 Analisador de Petições", "⚖️ Jurisprudência", "📝 Revisor de Contratos", "📊 Legal Analytics"]
escolha = st.selectbox("Seletor de Módulo", menu, label_visibility="collapsed")
st.markdown("<hr style='border-color: #333; margin-bottom:30px;'>", unsafe_allow_html=True)

# --- 8. MÓDULOS OPERACIONAIS ---

if "🏠 Dashboard" in escolha:
    st.markdown('<div class="main-card"><h2>Command Center</h2><p>MONITORIA DE RISCO E EFICIÊNCIA</p></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Failover Status", "Active", "5/5")
    c2.metric("Sessão", st.session_state.user_atual.split('.')[0].upper(), "Protegida")
    c3.metric("Win Rate", "84%", "Consolidado")

elif "📅 Auditor de Prazos" in escolha:
    st.markdown('<div class="main-card"><h2>Auditor de Prazos</h2><p>Contagem automática em dias úteis (CPC/15).</p></div>', unsafe_allow_html=True)
    txt = st.text_area("Texto da Publicação:", height=200)
    if st.button("CALCULAR PRAZO FATAL") and txt:
        registrar_evento("Prazos")
        with st.spinner("Analisando..."):
            res, _ = call_technobolt_ai(txt, system_context="prazos")
            st.session_state.update({'titulo_resultado': "Relatório de Prazo", 'resultado_ia': res, 'mostrar_resultado': True})
            st.rerun()

elif "🔍 Analisador de Petições" in escolha:
    st.markdown('<div class="main-card"><h2>Analisador de Petições</h2><p>Busca de contradições fáticas e vulnerabilidades.</p></div>', unsafe_allow_html=True)
    f1 = st.file_uploader("Petição (PDF/DOCX)", type=['pdf', 'docx'])
    f2 = st.file_uploader("Provas (PDF)", type=['pdf'])
    if f1 and st.button("EXECUTAR RAIO-X"):
        registrar_evento("Análise Tática")
        with st.spinner("Cruzando dados..."):
            t1, t2 = preparar_anexo_ia(f1), preparar_anexo_ia(f2) if f2 else "Sem provas."
            res, _ = call_technobolt_ai(f"Petição: {t1}\nProvas: {t2}", system_context="analisador")
            st.session_state.update({'titulo_resultado': "Dossiê de Vulnerabilidades", 'resultado_ia': res, 'mostrar_resultado': True})
            st.rerun()

elif "⚖️ Jurisprudência" in escolha:
    st.markdown('<div class="main-card"><h2>Jurisprudência Semântica</h2><p>Estratégia baseada em precedentes e julgador.</p></div>', unsafe_allow_html=True)
    caso = st.text_area("Descreva o caso concreto:")
    juiz = st.text_input("Nome do Magistrado (Opcional):")
    if st.button("GERAR ESTRATÉGIA") and caso:
        registrar_evento("Jurisprudência")
        res, _ = call_technobolt_ai(f"Caso: {caso}\nJuiz: {juiz}", system_context="jurisprudencia")
        st.session_state.update({'titulo_resultado': "Estratégia de Precedentes", 'resultado_ia': res, 'mostrar_resultado': True})
        st.rerun()

elif "📝 Revisor de Contratos" in escolha:
    st.markdown('<div class="main-card"><h2>Revisor de Contratos</h2><p>Auditoria simultânea de riscos e compliance.</p></div>', unsafe_allow_html=True)
    files = st.file_uploader("Upload de Contratos", accept_multiple_files=True, type=['pdf', 'docx'])
    if files and st.button("INICIAR AUDITORIA"):
        registrar_evento("Contratos")
        res_list, bar = [], st.progress(0)
        for i, f in enumerate(files):
            r, _ = call_technobolt_ai(preparar_anexo_ia(f), system_context="contratos")
            res_list.append(f"### Arquivo: {f.name}\n{r}")
            bar.progress((i + 1) / len(files))
        st.session_state.update({'titulo_resultado': "Auditoria de Compliance", 'resultado_ia': "\n\n---\n\n".join(res_list), 'mostrar_resultado': True})
        st.rerun()
elif "📊 Legal Analytics" in escolha:
    elif "📊 Legal Analytics" in escolha:
    st.markdown('<div class="main-card"><h2>📊 Legal Analytics</h2><p>Jurimetria e estatísticas estratégicas de processos.</p></div>', unsafe_allow_html=True)
    dados = st.text_area("Cole os dados brutos ou tabela de processos:", height=200, placeholder="Ex: Processo 001 - Vara Cível - R$ 10.000...")
    if st.button("GERAR INSIGHTS JURIMÉTRICOS"):
        if dados:
            registrar_evento("Analytics")
            with st.spinner("Processando Big Data Jurídico..."):
                res, _ = call_technobolt_ai(dados, system_context="analytics")
                st.session_state.update({
                    'titulo_resultado': "Análise Jurimetrista", 
                    'resultado_ia': res, 
                    'mostrar_resultado': True
                })
                st.rerun()
        else:
            st.warning("Por favor, insira dados para análise.")

# --- 9. RESULTADO UNIFICADO ---
if st.session_state.get('mostrar_resultado'):
    st.markdown("---")
    _, col_res, _ = st.columns([0.1, 11.8, 0.1])
    with col_res:
        # O container força o Streamlit a agrupar os elementos dentro do card
        with st.container():
            # Abertura do card e título
            st.markdown(f"""
                <div class="result-card-unificado">
                    <div class="result-title">Technobolt - {st.session_state.titulo_resultado}</div>
                    <div style="color: #ffffff; min-height: 50px;">
            """, unsafe_allow_html=True)
            
            # Conteúdo da IA renderizado dinamicamente dentro das DIVs
            st.markdown(st.session_state.resultado_ia)
            
            # Fechamento das DIVs
            st.markdown("""
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        # Botão de fechar posicionado abaixo do card
        st.write("")
        if st.button("✖️ LIMPAR E FECHAR RELATÓRIO"):
            st.session_state.mostrar_resultado = False
            st.rerun()
            
st.caption(f"TechnoBolt Solutions © 2026 | Operador: {st.session_state.user_atual.upper()}")
