import streamlit as st
import hashlib
from infraestrutura.ProcessoCrud import UtilitariosVisuais, GerenciadorBanco

# ==========================================
# CONFIGURAÇÃO GLOBAL DA PÁGINA
# ==========================================
# Favicon agora apontando diretamente para o arquivo físico na sua pasta Imagens
st.set_page_config(page_title="Gestão Financeira", page_icon="Imagens/FAVICON.png", layout="wide")

# ==========================================
# INICIALIZAÇÃO DE ESTADOS DE SESSÃO
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = ""
if "email_logado" not in st.session_state:
    st.session_state.email_logado = ""
if "perfil_logado" not in st.session_state:
    st.session_state.perfil_logado = ""

# ==========================================
# MÓDULO DE SEGURANÇA E AUTENTICAÇÃO
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

# ==========================================
# MÓDULO VISUAL - TELA DE LOGIN
# ==========================================
def tela_login():
    st.markdown(
        """
        <style>
            [data-testid="collapsedControl"] {display: none;}
            [data-testid="stSidebar"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([3, 4, 3])
    with c2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        
        # Padronização de Marca (Branding Integrado)
        html_marca_login = """
        <div style="display: flex; justify-content: center; align-items: center; gap: 12px; margin-bottom: 0px;">
            <span class="material-symbols-rounded" style="color: #20c997; font-size: 46px;">pie_chart</span>
            <span style="color: var(--cor-primaria); font-size: 38px; font-weight: 700; letter-spacing: 0.5px;">Gestão Financeira</span>
        </div>
        """
        st.markdown(html_marca_login, unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: var(--cor-texto); font-size: 16px; margin-top: 5px; margin-bottom: 30px;'>Acesso restrito e corporativo</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("<div style='padding: 10px 0;'></div>", unsafe_allow_html=True)
            email_login = st.text_input("E-mail corporativo:", key="log_email", placeholder="seu.email@empresa.com")
            senha_login = st.text_input("Sua senha:", type="password", key="log_senha")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Acessar o sistema", type="primary", use_container_width=True):
                if not email_login or not senha_login:
                    st.warning("Por favor, preencha o e-mail e a senha.")
                else:
                    if verificar_login(email_login, senha_login):
                        st.rerun()
                    else:
                        st.error("Credenciais incorretas ou usuário inativo.")

# ==========================================
# ROTEADOR CENTRAL E MENUS
# ==========================================
def iniciar_sistema():
    GerenciadorBanco.inicializar_banco()
    UtilitariosVisuais.aplicar_configuracoes_ui()
    
    if not st.session_state.autenticado:
        tela_login()
    else:
        # Apenas Logotipo e Sessão Ativa no topo
        html_sidebar_header = f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 25px; padding: 0 5px;">
            <span class="material-symbols-rounded" style="color: #20c997; font-size: 28px;">pie_chart</span>
            <span style="color: white; font-size: 22px; font-weight: 700; letter-spacing: 0.5px;">Gestão Financeira</span>
        </div>
        
        <div style='padding: 12px 15px; margin-bottom: 15px; background-color: rgba(0,0,0,0.15); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);'>
            <div style='color: #adb5bd; font-size: 12px; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px;'>Sessão ativa</div>
            <div style='color: white; font-size: 15px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{st.session_state.usuario_logado}</div>
            <div style='color: #20c997; font-size: 13px; font-weight: 500; margin-top: 2px;'>{st.session_state.perfil_logado}</div>
        </div>
        """
        st.sidebar.markdown(html_sidebar_header, unsafe_allow_html=True)
        
        # O botão Sair puro. O CSS modificado cuidará de mandá-lo para o rodapé.
        if st.sidebar.button("Sair do sistema", icon=":material/logout:", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.usuario_logado = ""
            st.session_state.email_logado = ""
            st.session_state.perfil_logado = ""
            st.rerun()

        # Controle de Acesso Baseado em Papéis (RBAC)
        paginas_basicas = [
            st.Page("modulos/Categoria.py", title="Categorias", icon=":material/folder:"),
            st.Page("modulos/Classificacao.py", title="Classificações", icon=":material/account_tree:"),
            st.Page("modulos/Evento.py", title="Eventos", icon=":material/sell:")
        ]
        
        dicionario_paginas = {"Cadastros Básicos": paginas_basicas}
        
        if st.session_state.perfil_logado == "Administrador":
            dicionario_paginas["Segurança"] = [st.Page("modulos/CadastroUsuario.py", title="Usuários do sistema", icon=":material/manage_accounts:")]

        roteador = st.navigation(dicionario_paginas)
        roteador.run()

if __name__ == "__main__":
    iniciar_sistema()