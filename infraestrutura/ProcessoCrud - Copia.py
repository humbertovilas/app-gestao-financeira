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
    def inicializar_banco():
        try:
            conn_setup = psycopg2.connect(st.secrets["DATABASE_URL"])
            conn_setup.autocommit = True
            cursor = conn_setup.cursor()
            
            cursor.execute('CREATE TABLE IF NOT EXISTS categorias (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, tipo TEXT NOT NULL)')
            cursor.execute('CREATE TABLE IF NOT EXISTS classificacoes (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, id_categoria INTEGER NOT NULL, FOREIGN KEY (id_categoria) REFERENCES categorias (id))')
            cursor.execute('ALTER TABLE classificacoes ADD COLUMN IF NOT EXISTS icone TEXT')
            cursor.execute('CREATE TABLE IF NOT EXISTS eventos (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, id_classificacao INTEGER NOT NULL, FOREIGN KEY (id_classificacao) REFERENCES classificacoes (id))')
            cursor.execute('CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, perfil TEXT NOT NULL, ativo BOOLEAN DEFAULT TRUE)')
            cursor.execute('CREATE TABLE IF NOT EXISTS fornecedores (id SERIAL PRIMARY KEY, nome TEXT NOT NULL)')

            cursor.execute('CREATE TABLE IF NOT EXISTS bancos (codigo VARCHAR(10) PRIMARY KEY, nome VARCHAR(150))')
            cursor.execute('CREATE TABLE IF NOT EXISTS contas_bancarias (id SERIAL PRIMARY KEY, numero_conta VARCHAR(20), agencia_codigo VARCHAR(20), agencia_nome VARCHAR(150), banco_codigo VARCHAR(10), endereco_agencia VARCHAR(250))')
            cursor.execute('CREATE TABLE IF NOT EXISTS cartoes_credito (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, limite_total NUMERIC(15,2) NOT NULL, dia_fechamento INTEGER NOT NULL, dia_vencimento INTEGER NOT NULL)')

            cursor.execute('''CREATE TABLE IF NOT EXISTS lancamentos 
                              (id SERIAL PRIMARY KEY, data_digitacao DATE DEFAULT CURRENT_DATE, data_vencimento DATE NOT NULL, 
                               data_efetivacao DATE, valor_previsto NUMERIC(15,2) NOT NULL, valor_realizado NUMERIC(15,2), 
                               id_evento INTEGER NOT NULL, id_classificacao INTEGER NOT NULL, parcela_atual INTEGER DEFAULT 1, 
                               total_parcelas INTEGER DEFAULT 1, status TEXT NOT NULL DEFAULT 'Pendente', observacao TEXT,
                               id_conta_bancaria INTEGER, id_cartao_credito INTEGER, data_compra DATE,
                               FOREIGN KEY (id_evento) REFERENCES eventos (id),
                               FOREIGN KEY (id_classificacao) REFERENCES classificacoes (id))''')
            
            cursor.execute('ALTER TABLE lancamentos ADD COLUMN IF NOT EXISTS id_fornecedor INTEGER REFERENCES fornecedores(id)')
            
            # --- NOVOS CAMPOS PARA EDIÇÃO EM CASCATA (FASE 1) ---
            cursor.execute('ALTER TABLE lancamentos ADD COLUMN IF NOT EXISTS codigo_parcelamento TEXT')
            cursor.execute('ALTER TABLE lancamentos ADD COLUMN IF NOT EXISTS intervalo INTEGER DEFAULT 30')

            # --- ÍNDICES DE ALTA PERFORMANCE (BLINDAGEM CONTRA LATÊNCIA) ---
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cat_nome ON categorias (nome)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cls_nome ON classificacoes (nome)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ev_nome ON eventos (nome)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_forn_nome ON fornecedores (nome)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lanc_vencimento ON lancamentos (data_vencimento)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lanc_cartao ON lancamentos (id_cartao_credito)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lanc_forn ON lancamentos (id_fornecedor)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lanc_cod_parc ON lancamentos (codigo_parcelamento)")
            
            cursor.execute("SELECT count(codigo) FROM bancos")
            if cursor.fetchone()[0] == 0:
                bancos = [('001','Banco do Brasil'),('104','Caixa'),('033','Santander'),('341','Itaú'),('237','Bradesco'),('260','Nubank')]
                for c, n in bancos: cursor.execute("INSERT INTO bancos (codigo, nome) VALUES (%s, %s)", (c, n))
            
            conn_setup.close()
        except Exception as e:
            st.error(f"Erro crítico ao inicializar banco de dados: {e}")

    @staticmethod
    def executar_query(query, params=(), is_select=True):
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
            return pd.read_sql_query(query, GerenciadorBanco.obter_conexao(), params=params) if is_select else None

    # ==========================================
    # NOVO MOTOR DE TRANSAÇÃO EM LOTE (ZERO LATÊNCIA)
    # ==========================================
    @staticmethod
    def executar_transacao_lote(lista_comandos):
        """ Executa múltiplos INSERTS ou UPDATES em uma única viagem ao banco de dados """
        conn = GerenciadorBanco.obter_conexao()
        try:
            cursor = conn.cursor()
            for query, params in lista_comandos:
                cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            conn.rollback() # Se uma parcela falhar, cancela todas para não quebrar a integridade
            st.cache_resource.clear()
            st.error(f"Erro na transação em lote: {e}")
            return False

class UtilitariosVisuais:
    @staticmethod
    def aplicar_configuracoes_ui():
        caminho_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        caminho_css = os.path.join(caminho_raiz, "style.css")
        
        css_global = """
        <link href='https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0' rel='stylesheet'>
        <style>
            button[data-testid="baseButton-primary"] {
                background-color: #20c997 !important;
                border-color: #20c997 !important;
                color: #1a2a40 !important;
                font-weight: 700 !important;
            }
            button[data-testid="baseButton-primary"]:hover {
                background-color: #17a589 !important;
                border-color: #17a589 !important;
                color: #ffffff !important;
            }
            .btn-global-filtrar {
                background-color: #1a2a40 !important;
                border-color: #1a2a40 !important;
                color: #ffffff !important;
                font-weight: 700 !important;
            }
            .btn-global-filtrar:hover {
                background-color: #2c3e50 !important;
                border-color: #2c3e50 !important;
                color: #20c997 !important;
            }
        </style>
        """
        st.markdown(css_global, unsafe_allow_html=True)
        try:
            with open(caminho_css, encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        except Exception: pass

        motor_botoes_js = """
        <script>
        setTimeout(() => {
            const doc = window.parent.document;
            const observer = new MutationObserver(() => {
                const botoes = doc.querySelectorAll('button');
                botoes.forEach(btn => {
                    const texto = btn.innerText || "";
                    if ((texto.includes('Inserir') || texto.includes('Salvar') || texto.includes('Atualizar') || texto.includes('Alterar') || texto.includes('Confirmar')) && !btn.hasAttribute('data-painted-green')) {
                        btn.setAttribute('data-painted-green', 'true');
                        btn.style.setProperty('background-color', '#20c997', 'important');
                        btn.style.setProperty('border-color', '#20c997', 'important');
                        btn.style.setProperty('color', '#1a2a40', 'important');
                        btn.style.setProperty('font-weight', '700', 'important');
                        
                        btn.addEventListener('mouseenter', () => {
                            btn.style.setProperty('background-color', '#17a589', 'important');
                            btn.style.setProperty('border-color', '#17a589', 'important');
                            btn.style.setProperty('color', '#ffffff', 'important');
                        });
                        btn.addEventListener('mouseleave', () => {
                            btn.style.setProperty('background-color', '#20c997', 'important');
                            btn.style.setProperty('border-color', '#20c997', 'important');
                            btn.style.setProperty('color', '#1a2a40', 'important');
                        });
                    }
                    
                    if (texto.includes('Filtrar') && !btn.hasAttribute('data-painted-navy')) {
                        btn.setAttribute('data-painted-navy', 'true');
                        btn.style.setProperty('background-color', '#1a2a40', 'important');
                        btn.style.setProperty('border-color', '#1a2a40', 'important');
                        btn.style.setProperty('color', '#ffffff', 'important');
                        btn.style.setProperty('font-weight', '700', 'important');
                        
                        btn.addEventListener('mouseenter', () => {
                            btn.style.setProperty('background-color', '#2c3e50', 'important');
                            btn.style.setProperty('border-color', '#2c3e50', 'important');
                            btn.style.setProperty('color', '#20c997', 'important');
                        });
                        btn.addEventListener('mouseleave', () => {
                            btn.style.setProperty('background-color', '#1a2a40', 'important');
                            btn.style.setProperty('border-color', '#1a2a40', 'important');
                            btn.style.setProperty('color', '#ffffff', 'important');
                        });
                    }
                });
            });
            observer.observe(doc.body, { childList: true, subtree: true });
        }, 50);
        </script>
        """
        components.html(motor_botoes_js, height=0, width=0)
            
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