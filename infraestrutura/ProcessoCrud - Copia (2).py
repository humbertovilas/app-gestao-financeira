# ==========================================
# MÓDULO: PROCESSOS CRUD E MOTOR DE DADOS
# OBJETIVO: Centralizar conexões, transações em lote e injeções de UI.
# ==========================================
import psycopg2
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import base64
import os

class GerenciadorBanco:
    @staticmethod
    def obter_conexao():
        """Estabelece conexão com o banco PostgreSQL (Neon DB)."""
        try:
            return psycopg2.connect(st.secrets["DATABASE_URL"])
        except Exception as e:
            st.error(f"Falha crítica de conexão com o banco de dados: {e}")
            return None

    @classmethod
    def inicializar_banco(cls):
        """Garante a existência das tabelas estruturais no Neon DB a ferro e fogo."""
        conn = cls.obter_conexao()
        if not conn: return
        try:
            conn.autocommit = True
            cursor = conn.cursor()
            queries = [
                "CREATE TABLE IF NOT EXISTS categorias (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, tipo TEXT NOT NULL);",
                "CREATE TABLE IF NOT EXISTS classificacoes (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, id_categoria INTEGER, icone TEXT);",
                "CREATE TABLE IF NOT EXISTS eventos (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, id_classificacao INTEGER);",
                "CREATE TABLE IF NOT EXISTS fornecedores (id SERIAL PRIMARY KEY, nome TEXT NOT NULL);",
                "CREATE TABLE IF NOT EXISTS bancos (codigo VARCHAR(10) PRIMARY KEY, nome VARCHAR(150));",
                "CREATE TABLE IF NOT EXISTS contas_bancarias (id SERIAL PRIMARY KEY, numero_conta VARCHAR(20), agencia_codigo VARCHAR(20), agencia_nome VARCHAR(150), banco_codigo VARCHAR(10), endereco_agencia VARCHAR(250));",
                "CREATE TABLE IF NOT EXISTS cartoes_credito (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, limite_total NUMERIC(15,2) NOT NULL, dia_fechamento INTEGER NOT NULL, dia_vencimento INTEGER NOT NULL);",
                "CREATE TABLE IF NOT EXISTS lancamentos (id SERIAL PRIMARY KEY, data_digitacao DATE DEFAULT CURRENT_DATE, data_vencimento DATE NOT NULL, data_efetivacao DATE, valor_previsto NUMERIC(15,2) NOT NULL, valor_realizado NUMERIC(15,2), id_evento INTEGER, id_classificacao INTEGER, parcela_atual INTEGER DEFAULT 1, total_parcelas INTEGER DEFAULT 1, status TEXT NOT NULL DEFAULT 'Pendente', observacao TEXT, id_conta_bancaria INTEGER, id_cartao_credito INTEGER, data_compra DATE, id_fornecedor INTEGER, codigo_parcelamento TEXT, intervalo INTEGER DEFAULT 30);"
            ]
            for q in queries:
                cursor.execute(q)
            cursor.close()
        except Exception as e:
            st.error(f"Erro na inicialização estrutural: {e}")
        finally:
            conn.close()

    @classmethod
    def executar_query(cls, query, params=None, is_select=True):
        """Motor centralizado de execução de queries usando Pandas para leitura."""
        conn = cls.obter_conexao()
        if not conn: return pd.DataFrame() if is_select else False
        try:
            if is_select:
                df = pd.read_sql(query, conn, params=params)
                return df
            else:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                cursor.close()
                return True
        except Exception as e:
            st.error(f"Erro ao executar query: {e}")
            if not is_select: conn.rollback()
            return pd.DataFrame() if is_select else False
        finally:
            conn.close()

    @classmethod
    def executar_transacao_lote(cls, queries_com_parametros: list) -> bool:
        """Executa múltiplas queries em um único Commit Atômico (Zero Latency Engine)."""
        conn = cls.obter_conexao()
        if not conn: return False
            
        try:
            cursor = conn.cursor()
            for query, params in queries_com_parametros:
                cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Rollback acionado. Erro na transação em lote: {e}")
            return False
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    @classmethod
    def buscar_fornecedores_dinamico(cls, termo_busca: str) -> list:
        """Motor de Lazy Loading para Fornecedores."""
        if not termo_busca: return []
        conn = cls.obter_conexao()
        if not conn: return []
        
        try:
            cursor = conn.cursor()
            query = "SELECT nome, id FROM fornecedores WHERE nome ILIKE %s ORDER BY nome LIMIT 15;"
            cursor.execute(query, (f'%{termo_busca}%',))
            resultados = cursor.fetchall()
            return [(linha[0], linha[1]) for linha in resultados]
        except Exception as e:
            st.error(f"Erro ao buscar fornecedores: {e}")
            return []
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

    @classmethod
    def buscar_eventos_dinamico(cls, termo_busca: str) -> list:
        """Motor de Lazy Loading para Eventos."""
        if not termo_busca: return []
        conn = cls.obter_conexao()
        if not conn: return []
        
        try:
            cursor = conn.cursor()
            query = "SELECT nome, id FROM eventos WHERE nome ILIKE %s ORDER BY nome LIMIT 15;"
            cursor.execute(query, (f'%{termo_busca}%',))
            resultados = cursor.fetchall()
            return [(linha[0], linha[1]) for linha in resultados]
        except Exception as e:
            st.error(f"Erro ao buscar eventos: {e}")
            return []
        finally:
            if 'cursor' in locals() and cursor: cursor.close()
            if conn: conn.close()

class UtilitariosVisuais:
    @staticmethod
    def aplicar_configuracoes_ui():
        """Aplica configurações baseadas no CSS e JS global."""
        UtilitariosVisuais.injetar_motor_visual()

    @staticmethod
    def injetar_motor_visual():
        """Motor JavaScript (MutationObserver) para padronização global de UI."""
        js_code = """
        <script>
        const observer = new MutationObserver((mutations) => {
            const buttons = window.parent.document.querySelectorAll('button');
            buttons.forEach(btn => {
                const txt = btn.innerText.trim();
                if(['Salvar', 'Confirmar', 'Inserir', 'Atualizar'].includes(txt)) {
                    btn.style.backgroundColor = '#20c997';
                    btn.style.color = 'white';
                    btn.style.border = 'none';
                }
                if(['Filtrar', 'Pesquisar'].includes(txt)) {
                    btn.style.backgroundColor = '#1a2a40';
                    btn.style.color = 'white';
                    btn.style.border = 'none';
                }
            });
        });
        observer.observe(window.parent.document.body, {childList: true, subtree: true});
        </script>
        """
        components.html(js_code, height=0, width=0)

    @staticmethod
    def inicializar_estados_modal():
        """Inicia as variáveis de controle global para modais e limpezas."""
        if 'form_reset' not in st.session_state: st.session_state.form_reset = 0
        if 'msg_erro' not in st.session_state: st.session_state.msg_erro = ""

    @staticmethod
    def obter_imagem_base64(caminho):
        """Lê um arquivo de imagem físico e converte para base64 HTML."""
        if os.path.exists(caminho):
            with open(caminho, "rb") as f:
                return base64.b64encode(f.read()).decode()
        return None