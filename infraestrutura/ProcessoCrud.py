import psycopg2
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import hashlib
import os
import time
import base64

# ==========================================
# GERENCIADOR DE BANCO DE DADOS
# ==========================================
class GerenciadorBanco:
    @staticmethod
    @st.cache_resource(ttl=3600, show_spinner=False)
    def obter_conexao():
        return psycopg2.connect(st.secrets["DATABASE_URL"])

    @staticmethod
    @st.cache_resource(show_spinner=False)
    def inicializar_banco():
        def executar_criacao_tabelas(conexao):
            cursor = conexao.cursor()
            
            # 1. TABELAS DE AUXÍLIO
            cursor.execute('CREATE TABLE IF NOT EXISTS categorias (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, tipo TEXT NOT NULL)')
            cursor.execute('CREATE TABLE IF NOT EXISTS classificacoes (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, id_categoria INTEGER NOT NULL, FOREIGN KEY (id_categoria) REFERENCES categorias (id))')
            cursor.execute('ALTER TABLE classificacoes ADD COLUMN IF NOT EXISTS icone TEXT')
            cursor.execute('CREATE TABLE IF NOT EXISTS eventos (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, id_classificacao INTEGER NOT NULL, FOREIGN KEY (id_classificacao) REFERENCES classificacoes (id))')
            cursor.execute('CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, perfil TEXT NOT NULL, ativo BOOLEAN DEFAULT TRUE)')

            # 2. TABELAS BANCÁRIAS
            cursor.execute('CREATE TABLE IF NOT EXISTS bancos (codigo VARCHAR(10) PRIMARY KEY, nome VARCHAR(150))')
            cursor.execute('CREATE TABLE IF NOT EXISTS contas_bancarias (id SERIAL PRIMARY KEY, numero_conta VARCHAR(20), agencia_codigo VARCHAR(20), agencia_nome VARCHAR(150), banco_codigo VARCHAR(10), endereco_agencia VARCHAR(250))')

            # 3. TABELA DE CARTÕES DE CRÉDITO
            cursor.execute('CREATE TABLE IF NOT EXISTS cartoes_credito (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, limite_total NUMERIC(15,2) NOT NULL, dia_fechamento INTEGER NOT NULL, dia_vencimento INTEGER NOT NULL)')

            # 4. TABELA DE LANÇAMENTOS
            cursor.execute('''CREATE TABLE IF NOT EXISTS lancamentos 
                              (id SERIAL PRIMARY KEY, data_digitacao DATE DEFAULT CURRENT_DATE, data_vencimento DATE NOT NULL, 
                               data_efetivacao DATE, valor_previsto NUMERIC(15,2) NOT NULL, valor_realizado NUMERIC(15,2), 
                               id_evento INTEGER NOT NULL, id_classificacao INTEGER NOT NULL, parcela_atual INTEGER DEFAULT 1, 
                               total_parcelas INTEGER DEFAULT 1, status TEXT NOT NULL DEFAULT 'Pendente', observacao TEXT,
                               id_conta_bancaria INTEGER, id_cartao_credito INTEGER, data_compra DATE,
                               FOREIGN KEY (id_evento) REFERENCES eventos (id),
                               FOREIGN KEY (id_classificacao) REFERENCES classificacoes (id))''')

            # 5. ÍNDICES DE ALTA PERFORMANCE
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cat_nome ON categorias (nome)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cls_nome ON classificacoes (nome)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ev_nome ON eventos (nome)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lanc_vencimento ON lancamentos (data_vencimento)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lanc_cartao ON lancamentos (id_cartao_credito)")

            conexao.commit()
            
            # CARGA DE BANCOS INICIAIS
            cursor.execute("SELECT count(codigo) as total FROM bancos")
            if cursor.fetchone()[0] == 0:
                bancos = [('001','Banco do Brasil'),('104','Caixa'),('033','Santander'),('341','Itaú'),('237','Bradesco'),('260','Nubank')]
                for c, n in bancos: cursor.execute("INSERT INTO bancos (codigo, nome) VALUES (%s, %s)", (c, n))
                conexao.commit()

        try:
            conn = GerenciadorBanco.obter_conexao()
            executar_criacao_tabelas(conn)
        except Exception:
            st.cache_resource.clear()
            executar_criacao_tabelas(GerenciadorBanco.obter_conexao())

    @staticmethod
    def executar_query(query, params=(), is_select=True):
        try:
            conn = GerenciadorBanco.obter_conexao()
            if is_select: return pd.read_sql_query(query, conn, params=params)
            else:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
        except Exception:
            st.cache_resource.clear()
            return pd.read_sql_query(query, GerenciadorBanco.obter_conexao(), params=params) if is_select else None

class UtilitariosVisuais:
    @staticmethod
    def aplicar_configuracoes_ui():
        caminho_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        caminho_css = os.path.join(caminho_raiz, "style.css")
        st.sidebar.markdown("<link href='https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0' rel='stylesheet'>", unsafe_allow_html=True)
        try:
            with open(caminho_css, encoding="utf-8") as f:
                st.sidebar.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        except Exception: pass
            
    @staticmethod
    def inicializar_estados_modal():
        if "form_reset" not in st.session_state: st.session_state.form_reset = 0
        if "msg_sucesso" not in st.session_state: st.session_state.msg_sucesso = False

    @staticmethod
    @st.cache_data(show_spinner=False, max_entries=100)
    def obter_imagem_base64(caminho_relativo):
        caminho_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        caminho_absoluto = os.path.join(caminho_raiz, caminho_relativo)
        try:
            if os.path.exists(caminho_absoluto):
                with open(caminho_absoluto, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode()
        except Exception: pass
        return ""