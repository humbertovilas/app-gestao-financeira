import streamlit as st
import pandas as pd
import time
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

if 'modal_bco_ativa' not in st.session_state: st.session_state.modal_bco_ativa = None
if 'modal_bco_id' not in st.session_state: st.session_state.modal_bco_id = None
if 'modal_bco_dados' not in st.session_state: st.session_state.modal_bco_dados = None
if 'show_filtros_bco' not in st.session_state: st.session_state.show_filtros_bco = False
if 'f_bco_busca' not in st.session_state: st.session_state.f_bco_busca = ""
if 'modal_del_id_bco' not in st.session_state: st.session_state.modal_del_id_bco = None
if 'modal_del_nome_bco' not in st.session_state: st.session_state.modal_del_nome_bco = None

def carregar_dados():
    return GerenciadorBanco.executar_query("SELECT codigo, nome FROM bancos ORDER BY nome ASC")

def callback_salvar_banco(acao="inserir", id_bco_orig=None):
    fr_id = st.session_state.get("form_reset")
    codigo = st.session_state.get(f"bco_codigo_{fr_id}", "").strip()
    nome = st.session_state.get(f"bco_nome_{fr_id}", "").strip()
    
    if not codigo or not nome:
        st.session_state.msg_erro = "Código e Nome são obrigatórios."
        return

    if acao == "editar" and id_bco_orig:
        GerenciadorBanco.executar_query("UPDATE bancos SET codigo = %s, nome = %s WHERE codigo = %s", (codigo, nome, id_bco_orig), is_select=False)
    else:
        vinc = GerenciadorBanco.executar_query("SELECT codigo FROM bancos WHERE codigo = %s", (codigo,))
        if not vinc.empty:
            st.session_state.msg_erro = "Este código de banco já está cadastrado."
            return
        GerenciadorBanco.executar_query("INSERT INTO bancos (codigo, nome) VALUES (%s, %s)", (codigo, nome), is_select=False)

    st.session_state.msg_sucesso = True
    st.session_state.modal_bco_ativa = None
    st.session_state.form_reset += 1

def callback_exclusao_direta(codigo):
    GerenciadorBanco.executar_query("DELETE FROM bancos WHERE codigo = %s", (codigo,), is_select=False)
    st.session_state.msg_sucesso = True
    st.session_state.form_reset += 1

@st.dialog(":material/museum: Cadastro de banco", width="small")
def modal_formulario(acao="inserir", id_bco=None, dados_pre=None):
    fr_id = st.session_state.get("form_reset", 0)
    v_cod = dados_pre['codigo'] if dados_pre is not None else ""
    v_nome = dados_pre['nome'] if dados_pre is not None else ""

    c1, c2 = st.columns([1, 3])
    c1.text_input("Código (Ex: 001):", value=v_cod, key=f"bco_codigo_{fr_id}")
    c2.text_input("Nome da instituição:", value=v_nome, key=f"bco_nome_{fr_id}")

    st.markdown("<br>", unsafe_allow_html=True)
    b_sal, b_fec = st.columns(2)
    with b_sal: st.button("Salvar", type="primary", use_container_width=True, on_click=callback_salvar_banco, args=(acao, id_bco))
    with b_fec:
        if st.button("Fechar", type="secondary", use_container_width=True): st.session_state.modal_bco_ativa = None; st.rerun()

    if st.session_state.get("msg_sucesso"):
        st.toast("Operação realizada com sucesso!", icon="✅"); time.sleep(2.0); st.session_state.msg_sucesso = False; st.rerun()
    elif st.session_state.get("msg_erro"):
        st.toast(st.session_state.msg_erro, icon="❌"); st.session_state.msg_erro = ""

@st.dialog(":material/delete: Excluir banco", width="small")
def modal_exclusao(codigo, nome_bco):
    vinc = GerenciadorBanco.executar_query("SELECT id FROM contas_bancarias WHERE banco_codigo = %s LIMIT 1", (codigo,))
    if not vinc.empty:
        st.warning(f"O banco **{nome_bco}** não pode ser excluído porque possui contas vinculadas.")
        if st.button("Fechar", type="secondary", use_container_width=True): st.session_state.modal_del_id_bco = None; st.rerun()
    else:
        st.error(f"Deseja realmente excluir o banco: **{nome_bco}**?")
        b_conf, b_canc = st.columns(2)
        with b_conf:
            if st.button("Confirmar", type="primary", use_container_width=True): callback_exclusao_direta(codigo); st.session_state.modal_del_id_bco = None; st.rerun()
        with b_canc:
            if st.button("Fechar", type="secondary", use_container_width=True): st.session_state.modal_del_id_bco = None; st.rerun()

c_tit, c_fil, c_ins, c_mar = st.columns([5, 1.5, 1.5, 3])
with c_tit: st.markdown("### :material/museum: Instituições Bancárias")
with c_fil:
    if st.button("Filtrar", type="tertiary", use_container_width=True): st.session_state.show_filtros_bco = not st.session_state.show_filtros_bco; st.rerun()
with c_ins:
    if st.button("Inserir", type="primary", use_container_width=True): st.session_state.modal_bco_ativa, st.session_state.modal_bco_id, st.session_state.modal_bco_dados = "inserir", None, None; st.rerun()

if st.session_state.show_filtros_bco:
    with st.container(border=True):
        f_col1, f_col2 = st.columns([8.5, 1.5], vertical_alignment="bottom")
        busca = f_col1.text_input("Pesquisar por código ou nome:", value=st.session_state.f_bco_busca)
        if f_col2.button("Pesquisar", type="tertiary", use_container_width=True): st.session_state.f_bco_busca = busca; st.rerun()

df = carregar_dados()
if not df.empty and st.session_state.f_bco_busca: df = df[df['nome'].str.contains(st.session_state.f_bco_busca, case=False) | df['codigo'].str.contains(st.session_state.f_bco_busca, case=False)]

st.markdown('''<div class="cabecalho-grid"><div style="display: flex;"><div style="flex: 1.0;">Código FEBRABAN</div><div style="flex: 5.0;">Nome da Instituição</div><div style="flex: 1.0; text-align: center;">Ações</div></div></div>''', unsafe_allow_html=True)

if not df.empty:
    for _, row in df.iterrows():
        c = st.columns([1.0, 5.0, 0.5, 0.5], vertical_alignment="center")
        c[0].markdown(f"<span style='font-weight: 600;'>{row['codigo']}</span>", unsafe_allow_html=True)
        c[1].markdown(row['nome'])
        if c[2].button(" ", icon=":material/edit:", key=f"ed_bc_{row['codigo']}", use_container_width=True):
            st.session_state.modal_bco_ativa, st.session_state.modal_bco_id, st.session_state.modal_bco_dados = "editar", row['codigo'], row; st.rerun()
        if c[3].button(" ", icon=":material/delete:", key=f"del_bc_{row['codigo']}", use_container_width=True):
            st.session_state.modal_del_id_bco = row['codigo']; st.session_state.modal_del_nome_bco = row['nome']; st.rerun()
        st.markdown("<hr style='margin: 5px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
else: st.info("Nenhum banco encontrado.")

if st.session_state.modal_bco_ativa: modal_formulario(st.session_state.modal_bco_ativa, st.session_state.modal_bco_id, st.session_state.modal_bco_dados)
elif st.session_state.modal_del_id_bco is not None: modal_exclusao(st.session_state.modal_del_id_bco, st.session_state.modal_del_nome_bco)