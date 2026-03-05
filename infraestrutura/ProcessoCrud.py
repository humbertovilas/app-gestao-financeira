import psycopg2
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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
        cursor.execute('''CREATE TABLE IF NOT EXISTS categorias 
                          (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, tipo TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS classificacoes 
                          (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, id_categoria INTEGER NOT NULL, 
                           FOREIGN KEY (id_categoria) REFERENCES categorias (id))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS eventos 
                          (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, id_classificacao INTEGER NOT NULL, 
                           FOREIGN KEY (id_classificacao) REFERENCES classificacoes (id))''')
        conn.commit()

    @staticmethod
    def executar_query(query, params=(), is_select=True):
        """Método único de CRUD. Processa INSERTS, UPDATES, DELETES e SELECTS com auto-reconexão."""
        try:
            conn = GerenciadorBanco.obter_conexao()
            if is_select:
                return pd.read_sql_query(query, conn, params=params)
            else:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
        except psycopg2.OperationalError:
            # Reconexão silenciosa caso o banco adormeça
            st.cache_resource.clear()
            conn = GerenciadorBanco.obter_conexao()
            if is_select:
                return pd.read_sql_query(query, conn, params=params)
            else:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()

class UtilitariosVisuais:
    """Classe responsável por gerir a injeção de CSS, ícones e comportamentos de tela."""
    
    @staticmethod
    def aplicar_configuracoes_ui():
        import os
        
        # 1. Caminho Absoluto Blindado (Acha o arquivo independente da pasta onde é chamado)
        caminho_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        caminho_css = os.path.join(caminho_raiz, "style.css")
        
        # 2. Injeta a fonte de Ícones na Sidebar (Para não ser apagada pelo roteador)
        st.sidebar.markdown("<link href='https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0' rel='stylesheet'>", unsafe_allow_html=True)
        
        # 3. Injeta o CSS inteiro na Sidebar garantindo a estilização persistente
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
    def ocultar_alerta_3s():
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
        }, 3000);
        </script>
        """
        components.html(js_alerta, height=0, width=0)