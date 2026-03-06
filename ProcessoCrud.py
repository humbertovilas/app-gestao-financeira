import psycopg2
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import hashlib

class GerenciadorBanco:
    """Classe responsável por centralizar e blindar a comunicação com o PostgreSQL NeonDB."""
    
    @staticmethod
    @st.cache_resource(ttl=3600)
    def obter_conexao():
        return psycopg2.connect(st.secrets["DATABASE_URL"])

    @staticmethod
    @st.cache_resource
    def inicializar_banco():
        conn = GerenciadorBanco.obter_conexao()
        cursor = conn.cursor()
        
        # Criação das tabelas de negócio
        cursor.execute('''CREATE TABLE IF NOT EXISTS categorias 
                          (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, tipo TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS classificacoes 
                          (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, id_categoria INTEGER NOT NULL, 
                           FOREIGN KEY (id_categoria) REFERENCES categorias (id))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS eventos 
                          (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, id_classificacao INTEGER NOT NULL, 
                           FOREIGN KEY (id_classificacao) REFERENCES classificacoes (id))''')
        
        # Criação da tabela de controle de acesso (ERP)
        cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                          (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL, 
                           senha TEXT NOT NULL, perfil TEXT NOT NULL, ativo BOOLEAN DEFAULT TRUE)''')
        conn.commit()

        # Injeção da semente do Administrador Mestre (Seed)
        df_admin = pd.read_sql_query("SELECT count(id) as total FROM usuarios", conn)
        if df_admin.iloc[0]['total'] == 0:
            senha_padrao = hashlib.sha256("admin123".encode('utf-8')).hexdigest()
            cursor.execute("INSERT INTO usuarios (nome, email, senha, perfil, ativo) VALUES (%s, %s, %s, %s, %s)", 
                           ("Administrador Mestre", "admin@sistema.com.br", senha_padrao, "Administrador", True))
            conn.commit()

    @staticmethod
    def executar_query(query, params=(), is_select=True):
        """Método único de CRUD. Processa INSERTS, UPDATES, DELETES e SELECTS com auto-reconexão blindada."""
        try:
            conn = GerenciadorBanco.obter_conexao()
            if is_select:
                return pd.read_sql_query(query, conn, params=params)
            else:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
        except Exception:
            st.cache_resource.clear()
            conn = GerenciadorBanco.obter_conexao()
            if is_select:
                return pd.read_sql_query(query, conn, params=params)
            else:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()

class UtilitariosVisuais:
    """Classe responsável por gerir a injeção de CSS, ícones, estados e comportamentos de tela."""
    
    @staticmethod
    def aplicar_configuracoes_ui():
        import os
        caminho_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        caminho_css = os.path.join(caminho_raiz, "style.css")
        
        st.sidebar.markdown("<link href='https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0' rel='stylesheet'>", unsafe_allow_html=True)
        
        try:
            with open(caminho_css, encoding="utf-8") as f:
                st.sidebar.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        except Exception as e:
            st.sidebar.error(f"Erro Crítico: Arquivo style.css não encontrado na raiz. Detalhe: {e}")
            
        js_enter = """
        <script>
        const doc = window.parent.document;
        doc.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const active = doc.activeElement;
                if (active && (active.tagName === 'INPUT' || active.tagName === 'SELECT')) {
                    e.preventDefault(); 
                    const focusable = Array.from(doc.querySelectorAll('input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])'));
                    const index = focusable.indexOf(active);
                    if (index > -1 && index < focusable.length - 1) {
                        focusable[index + 1].focus();
                    }
                }
            }
        });
        </script>
        """
        components.html(js_enter, height=0, width=0)

    @staticmethod
    def inicializar_estados_modal():
        """Cria as variáveis globais para controlar o formulário e a limpeza de dados."""
        if "form_reset" not in st.session_state: st.session_state.form_reset = 0
        if "form_cleared" not in st.session_state: st.session_state.form_cleared = False
        if "msg_sucesso" not in st.session_state: st.session_state.msg_sucesso = False
        if "msg_erro" not in st.session_state: st.session_state.msg_erro = ""

    @staticmethod
    def preparar_modal():
        """Reseta os estados para garantir que a modal abra limpa sempre que clicada."""
        st.session_state.form_reset = st.session_state.get("form_reset", 0) + 1
        st.session_state.form_cleared = False
        st.session_state.msg_sucesso = False
        st.session_state.msg_erro = ""

    @staticmethod
    def exibir_mensagens():
        """Renderiza as mensagens dentro das modais. Sucesso e Erro (nativos) apagando em 2s."""
        exibiu_alerta = False

        if st.session_state.get("msg_sucesso"):
            st.success("Operação realizada com sucesso!", icon=":material/check_circle:")
            st.session_state.msg_sucesso = False
            exibiu_alerta = True
            
        if st.session_state.get("msg_erro"):
            st.error(st.session_state.msg_erro)
            st.session_state.msg_erro = ""
            exibiu_alerta = True

        if exibiu_alerta:
            js_alerta = """
            <script>
            const doc = window.parent.document;
            setTimeout(() => {
                const alertas = doc.querySelectorAll('[data-testid="stAlert"]');
                alertas.forEach(alerta => {
                    alerta.style.transition = 'opacity 0.5s ease';
                    alerta.style.opacity = '0';
                    setTimeout(() => alerta.style.display = 'none', 500);
                });
            }, 2000); // 2000 milissegundos = 2 segundos cravados
            </script>
            """
            components.html(js_alerta, height=0, width=0)