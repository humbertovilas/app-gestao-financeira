import streamlit as st
import streamlit.components.v1 as components
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
# LOGOTIPO SVG BLINDADO (Nunca falha)
# ==========================================
logo_svg = """
<svg width="36" height="36" viewBox="0 0 24 24" fill="#20c997" xmlns="http://www.w3.org/2000/svg" style="vertical-align: middle;">
    <path d="M11 2v9h9c-.5 5-5 9-9 9s-9-4.5-9-9 4-9 9-9zm2 0c4.5.5 8.5 4.5 9 9h-9V2z"/>
</svg>
"""

# ==========================================
# PÁGINAS CORE (LOGIN E HOME)
# ==========================================
def pagina_login():
    c1, c2, c3 = st.columns([3, 4, 3])
    with c2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        html_marca = f"""<div style="display: flex; justify-content: center; align-items: center; gap: 12px;">{logo_svg}<span style="color: #1a2a40; font-size: 38px; font-weight: 700;">Gestão Financeira</span></div>"""
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

# ==========================================
# MAPEAMENTO NATIVO DO ROTEADOR
# ==========================================
pg_login = st.Page(pagina_login, title="Login")
pg_home = st.Page(pagina_home, title="Página Inicial")
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
    
    c_logo, c_op, c_cad, c_tab, c_esp, c_usr = st.columns([2.5, 1.2, 1.2, 1.2, 2.5, 1.5], vertical_alignment="center")
    
    with c_logo:
        st.markdown(f"<div style='color: white; font-size: 20px; font-weight: 700; display:flex; align-items:center; gap:8px;'>{logo_svg} Gestão Financeira</div>", unsafe_allow_html=True)
        
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
            st.divider()
            if st.button("Sair do sistema"): realizar_logoff()

# ==========================================
# MOTOR DE INJEÇÃO JS (À PROVA DE FALHAS)
# ==========================================
def aplicar_estilos_forcados():
    components.html("""
    <script>
    setTimeout(() => {
        const doc = window.parent.document;
        
        // 1. INJETAR CSS GLOBAL NO TOPO DO NAVEGADOR
        if (!doc.getElementById('sistema-saas-css')) {
            const style = doc.createElement('style');
            style.id = 'sistema-saas-css';
            style.innerHTML = `
                /* Remover elementos nativos do Streamlit */
                [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="collapsedControl"] { display: none !important; }
                .block-container { padding-top: 1.5rem !important; max-width: 98% !important; }
                
                /* Estilo do Botão Verde Esmeralda (Login) */
                .btn-login-verde { background-color: #20c997 !important; border-color: #20c997 !important; color: #1a2a40 !important; font-weight: 700 !important; font-size: 16px !important; }
                .btn-login-verde:hover { background-color: #17a589 !important; border-color: #17a589 !important; color: #ffffff !important; }
                
                /* Estilo da Navbar Azul Marinho */
                .navbar-azul-marinho { background-color: #1a2a40 !important; padding: 10px 20px !important; border-radius: 8px !important; box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important; margin-bottom: 25px !important; align-items: center !important; }
                
                /* Botões Transparentes da Navbar */
                .btn-nav-transparente { background-color: transparent !important; border: none !important; color: #adb5bd !important; font-weight: 500 !important; font-size: 15px !important; box-shadow: none !important; }
                .btn-nav-transparente:hover { color: #20c997 !important; background-color: rgba(255,255,255,0.05) !important; }
                
                /* Nome de Usuário na Navbar (Branco) */
                .btn-nav-destaque { color: #ffffff !important; font-weight: 700 !important; }
                
                /* Caixas de Menu Suspenso (Dropdowns) */
                div[data-testid="stPopoverBody"] { background-color: #ffffff !important; border-radius: 8px !important; padding: 5px !important; border: 1px solid #eee !important; box-shadow: 0 8px 16px rgba(0,0,0,0.1) !important;}
                div[data-testid="stPopoverBody"] button { background-color: transparent !important; color: #1a2a40 !important; border: none !important; width: 100% !important; text-align: left !important; padding: 10px 15px !important; font-weight: 500 !important; box-shadow: none !important;}
                div[data-testid="stPopoverBody"] button:hover { background-color: #f8f9fa !important; color: #20c997 !important; font-weight: 600 !important;}
            `;
            doc.head.appendChild(style);
        }

        // 2. CAÇAR E PINTAR O BOTÃO DE LOGIN
        const botoes = doc.querySelectorAll('button');
        botoes.forEach(btn => {
            if (btn.innerText.includes('Acessar o sistema')) {
                btn.classList.add('btn-login-verde');
            }
        });

        // 3. CAÇAR E PINTAR A NAVBAR
        const blocosHorizontais = doc.querySelectorAll('div[data-testid="stHorizontalBlock"]');
        blocosHorizontais.forEach(bloco => {
            if (bloco.innerHTML.includes('Gestão Financeira') && bloco.innerHTML.includes('Operação')) {
                bloco.classList.add('navbar-azul-marinho');
                
                const navBtns = bloco.querySelectorAll('button');
                navBtns.forEach(btn => {
                    btn.classList.add('btn-nav-transparente');
                });
                
                // Pinta o último botão (Usuário) de branco
                if (navBtns.length > 0) {
                    navBtns[navBtns.length - 1].classList.add('btn-nav-destaque');
                }
            }
        });
    }, 100); // Executa 100ms após a tela carregar para garantir a aplicação
    </script>
    """, height=0, width=0)

# ==========================================
# ORQUESTRADOR CENTRAL
# ==========================================
def main():
    if not st.session_state.autenticado:
        nav = st.navigation([pg_login])
        nav.run()
    else:
        pages = [pg_home, pg_agenda, pg_cartoes, pg_forn, pg_ev, pg_cb, pg_cat, pg_cls, pg_bco, pg_perfil]
        if st.session_state.perfil_logado == "Administrador":
            pages.append(pg_usr)
        
        nav = st.navigation(pages)
        render_top_navbar()
        UtilitariosVisuais.aplicar_configuracoes_ui()
        nav.run()
        
    # Chama o motor visual indestrutível sempre no final do carregamento
    aplicar_estilos_forcados()

if __name__ == "__main__":
    if "banco_verificado" not in st.session_state:
        GerenciadorBanco.inicializar_banco()
        st.session_state.banco_verificado = True
    main()