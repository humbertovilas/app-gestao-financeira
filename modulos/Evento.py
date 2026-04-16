import streamlit as st
import pandas as pd
import time
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

# ==========================================
# 1. CONFIGURAÇÕES E ESTADOS DE SESSÃO
# ==========================================
UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

if 'modal_ev_ativa' not in st.session_state: st.session_state.modal_ev_ativa = None
if 'modal_ev_id' not in st.session_state: st.session_state.modal_ev_id = None
if 'modal_ev_dados' not in st.session_state: st.session_state.modal_ev_dados = None
if 'show_filtros_ev' not in st.session_state: st.session_state.show_filtros_ev = False
if 'f_ev_busca' not in st.session_state: st.session_state.f_ev_busca = ""

# ==========================================
# 2. FUNÇÕES DE APOIO E CONSULTAS
# ==========================================
@st.cache_data(show_spinner=False, ttl=600)
def carregar_dados():
    query = """
        SELECT e.id, e.nome, c.nome as classificacao_nome, e.id_classificacao
        FROM eventos e
        INNER JOIN classificacoes c ON e.id_classificacao = c.id
        ORDER BY e.nome ASC
    """
    return GerenciadorBanco.executar_query(query)

@st.cache_data(show_spinner=False, ttl=3600)
def obter_classificacoes():
    return GerenciadorBanco.executar_query("SELECT id, nome FROM classificacoes ORDER BY nome ASC")

@st.cache_data(show_spinner=False, ttl=3600)
def obter_categorias():
    return GerenciadorBanco.executar_query("SELECT id, nome FROM categorias ORDER BY nome ASC")

def callback_salvar_evento(acao="inserir", id_evento=None):
    fr_id = st.session_state.get("form_reset")
    nome_ev = st.session_state.get(f"ev_nome_{fr_id}", "").strip()
    modo_class = st.session_state.get(f"ev_modo_cls_{fr_id}", "selecionar classificação")
    
    if not nome_ev:
        st.session_state.msg_erro = "O nome do evento é obrigatório."
        return

    id_cls_final = None
    if modo_class == "cadastrar nova":
        nome_nova_cls = st.session_state.get(f"ev_nova_cls_nome_{fr_id}", "").strip()
        cat_mestre = st.session_state.get(f"ev_nova_cls_cat_{fr_id}")
        if not nome_nova_cls:
            st.session_state.msg_erro = "Preencha o nome da nova classificação."
            return
        df_cat = GerenciadorBanco.executar_query("SELECT id FROM categorias WHERE nome = %s LIMIT 1", (cat_mestre,))
        id_cat_id = int(df_cat.iloc[0]['id'])
        GerenciadorBanco.executar_query("INSERT INTO classificacoes (nome, id_categoria, icone) VALUES (%s, %s, 'Sem ícone')", (nome_nova_cls, id_cat_id), is_select=False)
        df_cls = GerenciadorBanco.executar_query("SELECT id FROM classificacoes WHERE nome = %s ORDER BY id DESC LIMIT 1", (nome_nova_cls,))
        id_cls_final = int(df_cls.iloc[0]['id'])
    else:
        cls_sel = st.session_state.get(f"ev_cls_sel_{fr_id}")
        df_cls = GerenciadorBanco.executar_query("SELECT id FROM classificacoes WHERE nome = %s LIMIT 1", (cls_sel,))
        if df_cls.empty:
            st.session_state.msg_erro = "Selecione uma classificação válida."
            return
        id_cls_final = int(df_cls.iloc[0]['id'])

    if acao == "editar" and id_evento:
        GerenciadorBanco.executar_query("UPDATE eventos SET nome = %s, id_classificacao = %s WHERE id = %s", (nome_ev, id_cls_final, id_evento), is_select=False)
    else:
        GerenciadorBanco.executar_query("INSERT INTO eventos (nome, id_classificacao) VALUES (%s, %s)", (nome_ev, id_cls_final), is_select=False)

    st.cache_data.clear()
    st.session_state.msg_sucesso = True
    st.session_state.modal_ev_ativa = None
    st.session_state.form_reset += 1

def callback_exclusao_direta(id_evento):
    GerenciadorBanco.executar_query("DELETE FROM eventos WHERE id = %s", (id_evento,), is_select=False)
    st.cache_data.clear()
    st.session_state.msg_sucesso = True
    st.session_state.form_reset += 1

# ==========================================
# 3. MODAIS
# ==========================================
@st.dialog(":material/event: Evento financeiro", width="small")
def modal_formulario(acao="inserir", id_evento=None, dados_pre=None):
    fr_id = st.session_state.get("form_reset", 0)
    df_cls = obter_classificacoes(); op_cls = df_cls['nome'].tolist() if not df_cls.empty else []
    df_cats = obter_categorias(); op_cats = df_cats['nome'].tolist() if not df_cats.empty else []
    v_nome = dados_pre['nome'] if dados_pre is not None else ""
    v_cls_idx = 0
    if dados_pre is not None and dados_pre['classificacao_nome'] in op_cls: v_cls_idx = op_cls.index(dados_pre['classificacao_nome'])

    st.text_input("Nome do evento financeiro:", value=v_nome, key=f"ev_nome_{fr_id}")
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    st.radio("Origem da classificação:", ["selecionar classificação", "cadastrar nova"], horizontal=True, label_visibility="collapsed", key=f"ev_modo_cls_{fr_id}")
    
    if st.session_state[f"ev_modo_cls_{fr_id}"] == "selecionar classificação":
        st.selectbox("Classificação vinculada:", op_cls, index=v_cls_idx, key=f"ev_cls_sel_{fr_id}")
    else:
        st.text_input("Nome da nova classificação:", key=f"ev_nova_cls_nome_{fr_id}")
        st.selectbox("Vincule a uma categoria mestre:", op_cats, key=f"ev_nova_cls_cat_{fr_id}")

    st.markdown("<br>", unsafe_allow_html=True)
    b_sal, b_fec = st.columns(2)
    with b_sal:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_salvar_evento, args=(acao, id_evento))
    with b_fec:
        if st.button("Fechar", type="secondary", use_container_width=True):
            st.session_state.modal_ev_ativa = None; st.rerun()

    if st.session_state.get("msg_sucesso"):
        st.toast("Operação realizada com sucesso!", icon="✅"); time.sleep(2.0)
        st.session_state.msg_sucesso = False; st.rerun()
    elif st.session_state.get("msg_erro"):
        st.toast(st.session_state.msg_erro, icon="❌"); st.session_state.msg_erro = ""

@st.dialog(":material/delete: Excluir evento", width="small")
def modal_exclusao(id_evento, nome_evento):
    vinc = GerenciadorBanco.executar_query("SELECT id FROM lancamentos WHERE id_evento = %s LIMIT 1", (id_evento,))
    
    if not vinc.empty:
        st.warning(f"O evento **{nome_evento}** não pode ser excluído porque possui lançamentos financeiros vinculados a ele.")
        if st.button("Fechar", type="secondary", use_container_width=True):
            st.rerun()
    else:
        st.error(f"Deseja realmente excluir o evento: **{nome_evento}**?")
        b_conf, b_canc = st.columns(2)
        with b_conf:
            st.button("Confirmar", type="primary", use_container_width=True, on_click=callback_exclusao_direta, args=(id_evento,))
        with b_canc:
            if st.button("Fechar", type="secondary", use_container_width=True):
                st.rerun()

# ==========================================
# 4. INTERFACE PRINCIPAL
# ==========================================
c_tit, c_fil, c_ins, c_mar = st.columns([5, 1.5, 1.5, 3])
with c_tit: st.markdown("### :material/event: Cadastro de eventos")
with c_fil:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True):
        st.session_state.show_filtros_ev = not st.session_state.show_filtros_ev; st.rerun()
with c_ins:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True):
        st.session_state.modal_ev_ativa, st.session_state.modal_ev_id, st.session_state.modal_ev_dados = "inserir", None, None; st.rerun()

if st.session_state.show_filtros_ev:
    with st.container(border=True):
        f_col1, f_col2 = st.columns([8.5, 1.5], vertical_alignment="bottom")
        busca = f_col1.text_input("Pesquisar por evento ou classificação:", value=st.session_state.f_ev_busca)
        if f_col2.button("Pesquisar", type="tertiary", use_container_width=True):
            st.session_state.f_ev_busca = busca; st.rerun()

df = carregar_dados()
if not df.empty and st.session_state.f_ev_busca:
    df = df[df['nome'].str.contains(st.session_state.f_ev_busca, case=False) | df['classificacao_nome'].str.contains(st.session_state.f_ev_busca, case=False)]

st.markdown('''<div class="cabecalho-grid"><div style="display: flex;"><div style="flex: 3.5;">Evento financeiro (Credor/Devedor)</div><div style="flex: 2.5;">Classificação vinculada</div><div style="flex: 1.0; text-align: center;">Ações</div></div></div>''', unsafe_allow_html=True)

if not df.empty:
    for _, row in df.iterrows():
        c = st.columns([3.5, 2.5, 0.5, 0.5], vertical_alignment="center")
        c[0].markdown(f"<span style='font-weight: 600;'>{row['nome']}</span>", unsafe_allow_html=True)
        c[1].markdown(row['classificacao_nome'])
        if c[2].button(" ", icon=":material/edit:", key=f"ed_ev_{row['id']}", use_container_width=True):
            st.session_state.modal_ev_ativa, st.session_state.modal_ev_id, st.session_state.modal_ev_dados = "editar", row['id'], row; st.rerun()
        if c[3].button(" ", icon=":material/delete:", key=f"del_ev_{row['id']}", use_container_width=True):
            modal_exclusao(row['id'], row['nome'])
        st.markdown("<hr style='margin: 5px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
else: st.info("Nenhum evento financeiro encontrado.")

if st.session_state.modal_ev_ativa:
    modal_formulario(st.session_state.modal_ev_ativa, st.session_state.modal_ev_id, st.session_state.modal_ev_dados)