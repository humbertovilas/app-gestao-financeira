import streamlit as st
import pandas as pd
import time
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

# ==========================================
# 1. CONFIGURAÇÕES E ESTADOS DE SESSÃO
# ==========================================
UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

if 'modal_cat_ativa' not in st.session_state: st.session_state.modal_cat_ativa = None
if 'modal_cat_id' not in st.session_state: st.session_state.modal_cat_id = None
if 'modal_cat_dados' not in st.session_state: st.session_state.modal_cat_dados = None
if 'show_filtros_cat' not in st.session_state: st.session_state.show_filtros_cat = False
if 'f_cat_busca' not in st.session_state: st.session_state.f_cat_busca = ""

# ==========================================
# 2. FUNÇÕES DE APOIO E CONSULTAS
# ==========================================
@st.cache_data(show_spinner=False, ttl=3600)
def carregar_dados():
    return GerenciadorBanco.executar_query("SELECT id, nome, tipo FROM categorias ORDER BY nome ASC")

def callback_salvar_categoria(acao="inserir", id_cat=None):
    fr_id = st.session_state.get("form_reset")
    nome = st.session_state.get(f"cat_nome_{fr_id}", "").strip()
    tipo = st.session_state.get(f"cat_tipo_{fr_id}", "Despesa")
    
    if not nome:
        st.session_state.msg_erro = "O nome da categoria é obrigatório."
        return

    if acao == "editar" and id_cat:
        GerenciadorBanco.executar_query("UPDATE categorias SET nome = %s, tipo = %s WHERE id = %s", (nome, tipo, id_cat), is_select=False)
    else:
        GerenciadorBanco.executar_query("INSERT INTO categorias (nome, tipo) VALUES (%s, %s)", (nome, tipo), is_select=False)

    st.cache_data.clear()
    st.session_state.msg_sucesso = True
    st.session_state.modal_cat_ativa = None
    st.session_state.form_reset += 1

def callback_exclusao_direta(id_cat):
    GerenciadorBanco.executar_query("DELETE FROM categorias WHERE id = %s", (id_cat,), is_select=False)
    st.cache_data.clear()
    st.session_state.msg_sucesso = True
    st.session_state.form_reset += 1

# ==========================================
# 3. MODAIS
# ==========================================
@st.dialog(":material/category: Nova categoria", width="small")
def modal_formulario(acao="inserir", id_cat=None, dados_pre=None):
    fr_id = st.session_state.get("form_reset", 0)
    v_nome = dados_pre['nome'] if dados_pre is not None else ""
    v_tipo = dados_pre['tipo'] if dados_pre is not None else "Despesa"

    st.text_input("Nome da categoria:", value=v_nome, key=f"cat_nome_{fr_id}")
    st.selectbox("Natureza (Tipo):", ["Receita", "Despesa"], index=0 if v_tipo == "Receita" else 1, key=f"cat_tipo_{fr_id}")

    st.markdown("<br>", unsafe_allow_html=True)
    b_sal, b_fec = st.columns(2)
    with b_sal:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_salvar_categoria, args=(acao, id_cat))
    with b_fec:
        if st.button("Fechar", type="secondary", use_container_width=True):
            st.session_state.modal_cat_ativa = None; st.rerun()

    if st.session_state.get("msg_sucesso"):
        st.toast("Operação realizada com sucesso!", icon="✅"); time.sleep(2.0)
        st.session_state.msg_sucesso = False; st.rerun()
    elif st.session_state.get("msg_erro"):
        st.toast(st.session_state.msg_erro, icon="❌"); st.session_state.msg_erro = ""

@st.dialog(":material/delete: Excluir categoria", width="small")
def modal_exclusao(id_cat, nome_cat):
    vinc = GerenciadorBanco.executar_query("SELECT id FROM classificacoes WHERE id_categoria = %s LIMIT 1", (id_cat,))
    
    if not vinc.empty:
        st.warning(f"A categoria **{nome_cat}** não pode ser excluída porque possui classificações vinculadas a ela.")
        if st.button("Fechar", type="secondary", use_container_width=True):
            st.rerun()
    else:
        st.error(f"Deseja realmente excluir a categoria: **{nome_cat}**?")
        b_conf, b_canc = st.columns(2)
        with b_conf:
            st.button("Confirmar", type="primary", use_container_width=True, on_click=callback_exclusao_direta, args=(id_cat,))
        with b_canc:
            if st.button("Fechar", type="secondary", use_container_width=True):
                st.rerun()

# ==========================================
# 4. INTERFACE PRINCIPAL
# ==========================================
c_tit, c_fil, c_ins, c_mar = st.columns([5, 1.5, 1.5, 3])
with c_tit: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>category</span> Cadastro de categorias</h3>", unsafe_allow_html=True)
with c_fil:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True):
        st.session_state.show_filtros_cat = not st.session_state.show_filtros_cat; st.rerun()
with c_ins:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True):
        st.session_state.modal_cat_ativa, st.session_state.modal_cat_id, st.session_state.modal_cat_dados = "inserir", None, None; st.rerun()

if st.session_state.show_filtros_cat:
    with st.container(border=True):
        f_col1, f_col2 = st.columns([8.5, 1.5], vertical_alignment="bottom")
        busca = f_col1.text_input("Pesquisar por nome:", value=st.session_state.f_cat_busca)
        if f_col2.button("Pesquisar", type="tertiary", use_container_width=True):
            st.session_state.f_cat_busca = busca; st.rerun()

df = carregar_dados()
if not df.empty and st.session_state.f_cat_busca:
    df = df[df['nome'].str.contains(st.session_state.f_cat_busca, case=False)]

st.markdown('''<div class="cabecalho-grid"><div style="display: flex;"><div style="flex: 4.0;">Nome da categoria</div><div style="flex: 2.0; text-align: center;">Natureza</div><div style="flex: 1.0; text-align: center;">Ações</div></div></div>''', unsafe_allow_html=True)

if not df.empty:
    for _, row in df.iterrows():
        c = st.columns([4.0, 2.0, 0.5, 0.5], vertical_alignment="center")
        c[0].markdown(f"<span style='font-weight: 600;'>{row['nome']}</span>", unsafe_allow_html=True)
        badge = "badge-receita" if row['tipo'] == "Receita" else "badge-despesa"
        c[1].markdown(f"<div style='text-align: center;'><span class='{badge}'>{row['tipo']}</span></div>", unsafe_allow_html=True)
        if c[2].button(" ", icon=":material/edit:", key=f"ed_cat_{row['id']}", use_container_width=True):
            st.session_state.modal_cat_ativa, st.session_state.modal_cat_id, st.session_state.modal_cat_dados = "editar", row['id'], row; st.rerun()
        if c[3].button(" ", icon=":material/delete:", key=f"del_cat_{row['id']}", use_container_width=True):
            modal_exclusao(row['id'], row['nome'])
        st.markdown("<hr style='margin: 5px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
else:
    st.info("Nenhuma categoria encontrada.")

if st.session_state.modal_cat_ativa:
    modal_formulario(st.session_state.modal_cat_ativa, st.session_state.modal_cat_id, st.session_state.modal_cat_dados)