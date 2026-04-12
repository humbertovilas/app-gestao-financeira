import streamlit as st
import hashlib
from infraestrutura.ProcessoCrud import UtilitariosVisuais, GerenciadorBanco

# ==========================================
# CONFIGURAÇÃO E ESTADOS GLOBAIS
# ==========================================
st.set_page_config(page_title="Gestão Financeira", page_icon="Imagens/FAVICON.png", layout="wide")

if "autenticado" not in st.session_state: st.session_state.autenticado = False
if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = ""
if "email_logado" not in st.session_state: st.session_state.email_logado = ""
if "perfil_logado" not in st.session_state: st.session_state.perfil_logado = ""

# ==========================================
# MÓDULO DE SEGURANÇA E LOGOFF
# ==========================================
def gerar_hash_senha(senha):
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

def verificar_login(email, senha):
    senha_hash = gerar_hash_senha(senha)
    query = "SELECT id, nome, email, perfil FROM usuarios WHERE email = %s AND senha = %s AND ativo = TRUE"
    df = GerenciadorBanco.executar_query(query, (email, senha_hash))
    if not df.empty:
        st.session_state.autenticado = True
        st.session_state.usuario_logado = df.iloc[0]['nome']
        st.session_state.email_logado = df.iloc[0]['email']
        st.session_state.perfil_logado = df.iloc[0]['perfil']
        return True
    return False

def realizar_logoff():
    st.session_state.autenticado = False
    st.session_state.usuario_logado = ""
    st.session_state.email_logado = ""
    st.session_state.perfil_logado = ""
    st.rerun()

# ==========================================
# PÁGINAS CORE (LOGIN E HOME)
# ==========================================
def pagina_login():
    st.markdown("""<style>[data-testid="stSidebar"], [data-testid="collapsedControl"] {display: none !important;}</style>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3, 4, 3])
    with c2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        html_marca = """<div style="display: flex; justify-content: center; align-items: center; gap: 12px;"><span class="material-symbols-rounded" style="color: #20c997; font-size: 46px;">pie_chart</span><span style="color: #1a2a40; font-size: 38px; font-weight: 700;">Gestão Financeira</span></div>"""
        st.markdown(html_marca, unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6c757d; font-size: 16px; margin-bottom: 30px;'>Acesso restrito e corporativo</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("<div style='padding: 5px 0;'></div>", unsafe_allow_html=True)
            email_login = st.text_input("E-mail corporativo:", key="log_email", placeholder="seu.email@empresa.com")
            senha_login = st.text_input("Sua senha:", type="password", key="log_senha")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Acessar o sistema", type="primary", use_container_width=True):
                if not email_login or not senha_login: st.warning("Preencha e-mail e senha.")
                elif verificar_login(email_login, senha_login): st.rerun()
                else: st.error("Credenciais incorretas ou inativas.")

def pagina_home():
    primeiro_nome = st.session_state.usuario_logado.split()[0] if st.session_state.usuario_logado else ""
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        st.markdown(f"<h1 style='text-align: center; color: #1a2a40;'>Olá, {primeiro_nome}!</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: #6c757d; font-weight: 400;'>Bem-vindo ao seu painel de Gestão Financeira.</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #adb5bd; margin-top: 15px;'>O sistema está pronto. Utilize o <b>menu superior</b> para navegar.</p>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 40px 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
        
        ca, cb = st.columns(2)
        with ca: st.markdown("<div style='text-align: center; padding: 15px; border: 1px solid #dee2e6; border-radius: 8px;'><span class='material-symbols-rounded' style='font-size: 46px; color: #20c997;'>calendar_month</span><br><b style='font-size: 18px; color: #1a2a40;'>Agenda Financeira</b></div>", unsafe_allow_html=True)
        with cb: st.markdown("<div style='text-align: center; padding: 15px; border: 1px solid #dee2e6; border-radius: 8px;'><span class='material-symbols-rounded' style='font-size: 46px; color: #20c997;'>credit_card</span><br><b style='font-size: 18px; color: #1a2a40;'>Cartões de Crédito</b></div>", unsafe_allow_html=True)

# ==========================================
# MAPEAMENTO NATIVO DO ROTEADOR (ST.PAGE)
# ==========================================
pg_login = st.Page(pagina_login, title="Login", default=True)
pg_home = st.Page(pagina_home, title="Página Inicial", default=True)
pg_agenda = st.Page("modulos/AgendaFinanceira.py", title="Agenda financeira")
pg_cartoes = st.Page("modulos/CartaoCredito.py", title="Cartões de crédito")
pg_forn = st.Page("modulos/CadastroFornecedor.py", title="Fornecedores")
pg_ev = st.Page("modulos/Evento.py", title="Eventos")
pg_cb = st.Page("modulos/ContaBancaria.py", title="Contas bancárias")
pg_cat = st.Page("modulos/Categoria.py", title="Categorias")
pg_cls = st.Page("modulos/Classificacao.py", title="Classificações")
pg_bco = st.Page("modulos/Banco.py", title="Bancos")
pg_perfil = st.Page("modulos/MeuPerfil.py", title="Meu perfil")
pg_usr = st.Page("modulos/CadastroUsuario.py", title="Gestão de usuários")

# ==========================================
# NAVBAR TOP CUSTOMIZADA
# ==========================================
def render_top_navbar():
    primeiro_nome = st.session_state.usuario_logado.split()[0] if st.session_state.usuario_logado else "Usuário"
    
    css = """
    <style>
    /* 1. Remove barra lateral completamente */
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    
    /* 2. Ajuste de espaço central */
    .main .block-container { padding-top: 2rem !important; max-width: 98% !important; }
    
    /* 3. Estilo da Navbar Escura (Atacando o primeiro container nativo) */
    .main .block-container > div[data-testid="stVerticalBlock"] > div:first-child > div[data-testid="stHorizontalBlock"] {
        background-color: #1a2a40;
        padding: 8px 20px;
        border-radius: 8px;
        align-items: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 25px;
    }
    
    /* 4. Estilo dos botões mestres na barra */
    .main .block-container > div[data-testid="stVerticalBlock"] > div:first-child > div[data-testid="stHorizontalBlock"] button {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #adb5bd !important;
        font-weight: 500 !important;
        font-size: 15px !important;
    }
    .main .block-container > div[data-testid="stVerticalBlock"] > div:first-child > div[data-testid="stHorizontalBlock"] button:hover {
        color: #20c997 !important;
        background-color: rgba(255,255,255,0.05) !important;
    }
    
    /* 5. Cor branca para o nome de usuário */
    .main .block-container > div[data-testid="stVerticalBlock"] > div:first-child > div[data-testid="stHorizontalBlock"] div[data-testid="column"]:last-child button {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* 6. Itens dentro da janela Dropdown */
    div[data-testid="stPopoverBody"] button {
        border: none !important;
        background-color: transparent !important;
        color: #343a40 !important;
        text-align: left !important;
        width: 100% !important;
        justify-content: flex-start !important;
        padding: 10px 15px !important;
        box-shadow: none !important;
        font-size: 14px !important;
    }
    div[data-testid="stPopoverBody"] button:hover {
        background-color: #f8f9fa !important;
        color: #20c997 !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    
    # Construção das Colunas da Barra Superior
    c_logo, c_op, c_cad, c_tab, c_esp, c_usr = st.columns([2.5, 1.2, 1.2, 1.2, 2.5, 1.5], vertical_alignment="center")
    
    with c_logo:
        st.markdown("<div style='color: white; font-size: 20px; font-weight: 700; padding-top: 5px;'><span class='material-symbols-rounded' style='color: #20c997; vertical-align: bottom;'>pie_chart</span> Gestão Financeira</div>", unsafe_allow_html=True)
        
    with c_op:
        with st.popover("Operação ▾", use_container_width=True):
            if st.button("Agenda financeira"): st.switch_page(pg_agenda)
            if st.button("Cartões de crédito"): st.switch_page(pg_cartoes)
            
    with c_cad:
        with st.popover("Cadastros ▾", use_container_width=True):
            if st.button("Fornecedores"): st.switch_page(pg_forn)
            if st.button("Eventos"): st.switch_page(pg_ev)
            if st.button("Contas bancárias"): st.switch_page(pg_cb)
            
    with c_tab:
        with st.popover("Tabelas ▾", use_container_width=True):
            if st.button("Categorias"): st.switch_page(pg_cat)
            if st.button("Classificações"): st.switch_page(pg_cls)
            if st.button("Bancos"): st.switch_page(pg_bco)
            
    with c_usr:
        with st.popover(f"👤 {primeiro_nome} ▾", use_container_width=True):
            if st.button("Página inicial"): st.switch_page(pg_home)
            if st.button("Meu perfil"): st.switch_page(pg_perfil)
            if st.session_state.perfil_logado == "Administrador":
                if st.button("Gestão de usuários"): st.switch_page(pg_usr)
            st.divider() # Linha divisória
            if st.button("Sair do sistema"): realizar_logoff()

# ==========================================
# ORQUESTRADOR CENTRAL
# ==========================================
def main():
    if not st.session_state.autenticado:
        # Modo Deslogado
        nav = st.navigation([pg_login])
        nav.run()
    else:
        # Modo Logado - Monta todas as páginas disponíveis
        pages = [pg_home, pg_agenda, pg_cartoes, pg_forn, pg_ev, pg_cb, pg_cat, pg_cls, pg_bco, pg_perfil]
        if st.session_state.perfil_logado == "Administrador":
            pages.append(pg_usr)
        
        # O Motor nativo assume o roteamento real
        nav = st.navigation(pages)
        
        # Desenha a Navbar no topo de qualquer página
        render_top_navbar()
        UtilitariosVisuais.aplicar_configuracoes_ui()
        
        # Executa o conteúdo da página selecionada (Sem erros de Pandas!)
        nav.run()

if __name__ == "__main__":
    if "banco_verificado" not in st.session_state:
        GerenciadorBanco.inicializar_banco()
        st.session_state.banco_verificado = True
    main()