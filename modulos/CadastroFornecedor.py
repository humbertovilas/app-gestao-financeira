import streamlit as st
import pandas as pd
import time
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

# ==========================================
# 1. CONFIGURAÇÕES E ESTADOS DE SESSÃO
# ==========================================
UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

if 'modal_forn_ativa' not in st.session_state: st.session_state.modal_forn_ativa = None
if 'modal_forn_id' not in st.session_state: st.session_state.modal_forn_id = None
if 'modal_forn_dados' not in st.session_state: st.session_state.modal_forn_dados = None
if 'show_filtros_forn' not in st.session_state: st.session_state.show_filtros_forn = False
if 'f_forn_busca' not in st.session_state: st.session_state.f_forn_busca = ""
if 'modal_del_id_forn' not in st.session_state: st.session_state.modal_del_id_forn = None
if 'modal_del_nome_forn' not in st.session_state: st.session_state.modal_del_nome_forn = None

# ==========================================
# 2. FUNÇÕES DE APOIO E CONSULTAS
# ==========================================
@st.cache_data(show_spinner=False, ttl=600)
def carregar_dados():
    return GerenciadorBanco.executar_query("SELECT id, nome FROM fornecedores ORDER BY nome ASC")

def callback_salvar_fornecedor(acao="inserir", id_forn_orig=None):
    fr_id = st.session_state.get("form_reset", 0)
    nome = st.session_state.get(f"forn_nome_{fr_id}", "").strip()

    if not nome:
        st.session_state.msg_erro = "O nome do fornecedor é obrigatório."
        return

    # Verificação de duplicidade
    df_check = GerenciadorBanco.executar_query("SELECT id FROM fornecedores WHERE nome ILIKE %s AND id != %s", (nome, id_forn_orig if id_forn_orig else 0))
    if not df_check.empty:
        st.session_state.msg_erro = "Já existe um fornecedor com este nome."
        return

    if acao == "inserir":
        GerenciadorBanco.executar_query("INSERT INTO fornecedores (nome) VALUES (%s)", (nome,), is_select=False)
        st.session_state.msg_sucesso_cont = True # Flag para inserção contínua (não fecha a modal)
    else:
        GerenciadorBanco.executar_query("UPDATE fornecedores SET nome = %s WHERE id = %s", (nome, id_forn_orig), is_select=False)
        st.session_state.msg_sucesso = True
        st.session_state.modal_forn_ativa = None # Edição fecha a modal normalmente

    st.cache_data.clear()
    st.session_state.form_reset += 1

# ==========================================
# 3. MODAIS DE INTERAÇÃO
# ==========================================
@st.dialog(":material/store: Fornecedor", width="small")
def modal_formulario(acao="inserir", id_forn=None, dados_pre=None):
    fr_id = st.session_state.get("form_reset", 0)
    
    if f"forn_nome_{fr_id}" not in st.session_state:
        st.session_state[f"forn_nome_{fr_id}"] = dados_pre['nome'] if dados_pre is not None else ""

    st.text_input("Nome do fornecedor:", key=f"forn_nome_{fr_id}")

    st.markdown("<br>", unsafe_allow_html=True)
    b_sal, b_fec = st.columns(2)
    with b_sal:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_salvar_fornecedor, args=(acao, id_forn))
    with b_fec:
        if st.button("Fechar", type="secondary", use_container_width=True): 
            st.session_state.modal_forn_ativa = None
            st.rerun()

    # Tratamento de sucesso para Inserção Contínua vs Edição
    if st.session_state.get("msg_sucesso_cont"):
        st.toast("Fornecedor cadastrado com sucesso! Pode inserir o próximo.", icon="✅")
        time.sleep(1.5)
        st.session_state.msg_sucesso_cont = False
        st.rerun()
    elif st.session_state.get("msg_sucesso"):
        st.toast("Fornecedor atualizado com sucesso!", icon="✅")
        time.sleep(1.5)
        st.session_state.msg_sucesso = False
        st.rerun()
    elif st.session_state.get("msg_erro"):
        st.toast(st.session_state.msg_erro, icon="❌")
        st.session_state.msg_erro = ""

@st.dialog(":material/delete: Excluir fornecedor", width="small")
def modal_exclusao(id_forn, nome_forn):
    st.error(f"Deseja excluir o fornecedor: **{nome_forn}**?")
    
    # Proteção de chave estrangeira (Integridade Referencial)
    df_vinc = GerenciadorBanco.executar_query("SELECT id FROM lancamentos WHERE id_fornecedor = %s LIMIT 1", (id_forn,))
    pode_excluir = df_vinc.empty if df_vinc is not None else True

    if not pode_excluir:
        st.warning("Este fornecedor não pode ser excluído pois possui lançamentos vinculados a ele na Agenda Financeira.")
        if st.button("Fechar", type="secondary", use_container_width=True): 
            st.session_state.modal_del_id_forn = None; st.rerun()
    else:
        b_conf, b_canc = st.columns(2)
        with b_conf:
            if st.button("Confirmar", type="primary", use_container_width=True):
                GerenciadorBanco.executar_query("DELETE FROM fornecedores WHERE id = %s", (id_forn,), is_select=False)
                st.cache_data.clear()
                st.session_state.msg_sucesso = True
                st.session_state.modal_del_id_forn = None
                st.rerun()
        with b_canc:
            if st.button("Fechar", type="secondary", use_container_width=True): 
                st.session_state.modal_del_id_forn = None; st.rerun()

# ==========================================
# 4. RENDERIZAÇÃO DA INTERFACE PRINCIPAL
# ==========================================
c_tit, c_fil, c_ins, c_mar = st.columns([5, 1.5, 1.5, 3])
with c_tit: 
    st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>store</span> Fornecedores</h3>", unsafe_allow_html=True)
with c_fil:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True): 
        st.session_state.show_filtros_forn = not st.session_state.show_filtros_forn
        st.rerun()
with c_ins:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True):
        st.session_state.modal_del_id_forn = None
        st.session_state.modal_forn_ativa = "inserir"
        st.session_state.modal_forn_id = None
        st.session_state.modal_forn_dados = None
        st.rerun()

# Painel de Filtros Padronizado
if st.session_state.show_filtros_forn:
    with st.container(border=True):
        st.text_input("Buscar fornecedor pelo nome:", placeholder="Digite o nome para pesquisar...", key="f_forn_busca_input")
        st.session_state.f_forn_busca = st.session_state.f_forn_busca_input

df = carregar_dados()

if df is not None and not df.empty and st.session_state.f_forn_busca:
    df = df[df['nome'].str.contains(st.session_state.f_forn_busca, case=False)]

st.markdown('''<div class="cabecalho-grid"><div style="display: flex;"><div style="flex: 6.0;">Nome do fornecedor</div><div style="flex: 1.0; text-align: center;">Ações</div></div></div>''', unsafe_allow_html=True)

if df is not None and not df.empty:
    for _, row in df.iterrows():
        c = st.columns([6.0, 0.5, 0.5], vertical_alignment="center")
        c[0].markdown(f"<span style='font-weight: 600;'>{row['nome']}</span>", unsafe_allow_html=True)
        
        if c[1].button(" ", icon=":material/edit:", key=f"ed_forn_{row['id']}", use_container_width=True):
            st.session_state.modal_forn_ativa, st.session_state.modal_forn_id, st.session_state.modal_forn_dados = "editar", row['id'], row; st.rerun()
        if c[2].button(" ", icon=":material/delete:", key=f"del_forn_{row['id']}", use_container_width=True):
            st.session_state.modal_del_id_forn = row['id']; st.session_state.modal_del_nome_forn = row['nome']; st.rerun()
        st.markdown("<hr style='margin: 5px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
else:
    st.info("Nenhum fornecedor encontrado.")

# MOTOR CENTRAL DE RENDERIZAÇÃO DE MODAIS
if st.session_state.modal_forn_ativa: modal_formulario(st.session_state.modal_forn_ativa, st.session_state.modal_forn_id, st.session_state.modal_forn_dados)
elif st.session_state.modal_del_id_forn is not None: modal_exclusao(st.session_state.modal_del_id_forn, st.session_state.modal_del_nome_forn)