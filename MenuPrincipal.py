import streamlit as st
import os
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

# ==========================================
# CONFIGURAÇÃO GLOBAL DO SISTEMA (CÉREBRO)
# ==========================================
caminho_favicon = os.path.join("Imagens", "favicon.png")
if not os.path.exists(caminho_favicon):
    caminho_favicon = os.path.join("IMAGENS", "favicon.png")

st.set_page_config(
    page_title="Gestão Financeira",
    page_icon=caminho_favicon if os.path.exists(caminho_favicon) else None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. INJEÇÃO DO MOTOR VISUAL BLINDADO
UtilitariosVisuais.aplicar_configuracoes_ui()

# 2. INICIALIZAR O BANCO DE DADOS
try:
    GerenciadorBanco.inicializar_banco()
except Exception as e:
    st.error(f"Erro Crítico de Conexão com o Banco de Dados: {e}")
    st.stop()

# ==========================================
# LOGOTIPO (Ficará no topo graças ao Flexbox do CSS)
# ==========================================
st.sidebar.markdown("""
    <div style='display: flex; align-items: center; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 15px;'>
        <span class='material-symbols-rounded' style='color: #20c997; margin-right: 10px; font-size: 32px;'>pie_chart</span>
        <span style='color: white; font-size: 20px; font-weight: 700; letter-spacing: 0.5px;'>Gestão Financeira</span>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# ROTEAMENTO NATIVO DE ALTA PERFORMANCE
# ==========================================
paginas = {
    "Cadastros Básicos": [
        st.Page("modulos/Categoria.py", title="Categorias", icon=":material/folder:"),
        st.Page("modulos/Classificacao.py", title="Classificações", icon=":material/account_tree:"),
        st.Page("modulos/Evento.py", title="Eventos", icon=":material/sell:")
    ]
}

roteador = st.navigation(paginas)
roteador.run()