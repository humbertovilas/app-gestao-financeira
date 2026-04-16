import streamlit as st
import pandas as pd
import time
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

if 'modal_cb_ativa' not in st.session_state: st.session_state.modal_cb_ativa = None
if 'modal_cb_id' not in st.session_state: st.session_state.modal_cb_id = None
if 'modal_cb_dados' not in st.session_state: st.session_state.modal_cb_dados = None
if 'show_filtros_cb' not in st.session_state: st.session_state.show_filtros_cb = False
if 'f_cb_busca' not in st.session_state: st.session_state.f_cb_busca = ""
if 'modal_del_id_cb' not in st.session_state: st.session_state.modal_del_id_cb = None
if 'modal_del_nome_cb' not in st.session_state: st.session_state.modal_del_nome_cb = None

def carregar_dados():
    query = """
    SELECT c.id, c.numero_conta, c.agencia_codigo, c.agencia_nome, c.banco_codigo, c.endereco_agencia, b.nome as banco_nome 
    FROM contas_bancarias c 
    INNER JOIN bancos b ON c.banco_codigo = b.codigo 
    ORDER BY b.nome ASC, c.agencia_codigo ASC
    """
    return GerenciadorBanco.executar_query(query)

def obter_bancos():
    return GerenciadorBanco.executar_query("SELECT codigo, nome FROM bancos ORDER BY nome ASC")

def callback_salvar_conta(acao="inserir", id_cb=None):
    fr_id = st.session_state.get("form_reset")
    cc = st.session_state.get(f"cb_cc_{fr_id}", "").strip()
    ag = st.session_state.get(f"cb_ag_{fr_id}", "").strip()
    agn = st.session_state.get(f"cb_agn_{fr_id}", "").strip()
    end = st.session_state.get(f"cb_end_{fr_id}", "").strip()
    bco_str = st.session_state.get(f"cb_bco_{fr_id}", "")
    
    if not cc or not bco_str:
        st.session_state.msg_erro = "Conta corrente e Banco são obrigatórios."
        return

    bco_cod = bco_str.split(" - ")[0]

    if acao == "editar" and id_cb:
        GerenciadorBanco.executar_query("UPDATE contas_bancarias SET numero_conta=%s, agencia_codigo=%s, agencia_nome=%s, banco_codigo=%s, endereco_agencia=%s WHERE id=%s", (cc, ag, agn, bco_cod, end, id_cb), is_select=False)
    else:
        GerenciadorBanco.executar_query("INSERT INTO contas_bancarias (numero_conta, agencia_codigo, agencia_nome, banco_codigo, endereco_agencia) VALUES (%s, %s, %s, %s, %s)", (cc, ag, agn, bco_cod, end), is_select=False)

    st.session_state.msg_sucesso = True
    st.session_state.modal_cb_ativa = None
    st.session_state.form_reset += 1

def callback_exclusao_direta(id_cb):
    GerenciadorBanco.executar_query("DELETE FROM contas_bancarias WHERE id = %s", (id_cb,), is_select=False)
    st.session_state.msg_sucesso = True
    st.session_state.form_reset += 1

@st.dialog(":material/account_balance: Cadastro de conta bancária", width="small")
def modal_formulario(acao="inserir", id_cb=None, dados_pre=None):
    fr_id = st.session_state.get("form_reset", 0)
    df_bancos = obter_bancos()
    op_bancos = [f"{r['codigo']} - {r['nome']}" for _, r in df_bancos.iterrows()] if not df_bancos.empty else []
    
    v_cc = dados_pre['numero_conta'] if dados_pre is not None else ""
    v_ag = dados_pre['agencia_codigo'] if dados_pre is not None else ""
    v_agn = dados_pre['agencia_nome'] if dados_pre is not None else ""
    v_end = dados_pre['endereco_agencia'] if dados_pre is not None else ""
    v_bco_idx = 0
    if dados_pre is not None and op_bancos:
        str_busca = f"{dados_pre['banco_codigo']} - {dados_pre['banco_nome']}"
        if str_busca in op_bancos: v_bco_idx = op_bancos.index(str_busca)

    st.selectbox("Instituição Bancária:", op_bancos, index=v_bco_idx, key=f"cb_bco_{fr_id}")
    c1, c2 = st.columns(2)
    c1.text_input("Número da agência:", value=v_ag, key=f"cb_ag_{fr_id}")
    c2.text_input("Número da conta:", value=v_cc, key=f"cb_cc_{fr_id}")
    st.text_input("Nome da agência (opcional):", value=v_agn, key=f"cb_agn_{fr_id}")
    st.text_input("Endereço da agência (opcional):", value=v_end, key=f"cb_end_{fr_id}")

    st.markdown("<br>", unsafe_allow_html=True)
    b_sal, b_fec = st.columns(2)
    with b_sal: st.button("Salvar", type="primary", use_container_width=True, on_click=callback_salvar_conta, args=(acao, id_cb))
    with b_fec:
        if st.button("Fechar", type="secondary", use_container_width=True): st.session_state.modal_cb_ativa = None; st.rerun()

    if st.session_state.get("msg_sucesso"):
        st.toast("Operação realizada com sucesso!", icon="✅"); time.sleep(2.0); st.session_state.msg_sucesso = False; st.rerun()
    elif st.session_state.get("msg_erro"):
        st.toast(st.session_state.msg_erro, icon="❌"); st.session_state.msg_erro = ""

@st.dialog(":material/delete: Excluir conta", width="small")
def modal_exclusao(id_cb, nome_cb):
    vinc = GerenciadorBanco.executar_query("SELECT id FROM lancamentos WHERE id_conta_bancaria = %s LIMIT 1", (id_cb,))
    if not vinc.empty:
        st.warning(f"A conta **{nome_cb}** não pode ser excluída porque possui lançamentos vinculados.")
        if st.button("Fechar", type="secondary", use_container_width=True): st.session_state.modal_del_id_cb = None; st.rerun()
    else:
        st.error(f"Deseja realmente excluir a conta: **{nome_cb}**?")
        b_conf, b_canc = st.columns(2)
        with b_conf:
            if st.button("Confirmar", type="primary", use_container_width=True): callback_exclusao_direta(id_cb); st.session_state.modal_del_id_cb = None; st.rerun()
        with b_canc:
            if st.button("Fechar", type="secondary", use_container_width=True): st.session_state.modal_del_id_cb = None; st.rerun()

c_tit, c_fil, c_ins, c_mar = st.columns([5, 1.5, 1.5, 3])
with c_tit: st.markdown("### :material/account_balance: Central de Contas Bancárias")
with c_fil:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True): st.session_state.show_filtros_cb = not st.session_state.show_filtros_cb; st.rerun()
with c_ins:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True): st.session_state.modal_cb_ativa, st.session_state.modal_cb_id, st.session_state.modal_cb_dados = "inserir", None, None; st.rerun()

if st.session_state.show_filtros_cb:
    with st.container(border=True):
        f_col1, f_col2 = st.columns([8.5, 1.5], vertical_alignment="bottom")
        busca = f_col1.text_input("Pesquisar por banco, agência ou conta:", value=st.session_state.f_cb_busca)
        if f_col2.button("Pesquisar", type="tertiary", use_container_width=True): st.session_state.f_cb_busca = busca; st.rerun()

df = carregar_dados()
if not df.empty and st.session_state.f_cb_busca: df = df[df['banco_nome'].str.contains(st.session_state.f_cb_busca, case=False) | df['numero_conta'].str.contains(st.session_state.f_cb_busca, case=False)]

st.markdown('''<div class="cabecalho-grid"><div style="display: flex;"><div style="flex: 2.5;">Instituição Bancária</div><div style="flex: 1.0;">Agência</div><div style="flex: 1.5;">Conta Corrente</div><div style="flex: 2.0;">Nome da Agência</div><div style="flex: 1.0; text-align: center;">Ações</div></div></div>''', unsafe_allow_html=True)

if not df.empty:
    for _, row in df.iterrows():
        c = st.columns([2.5, 1.0, 1.5, 2.0, 0.5, 0.5], vertical_alignment="center")
        c[0].markdown(f"<span style='font-weight: 600;'>{row['banco_codigo']} - {row['banco_nome']}</span>", unsafe_allow_html=True)
        c[1].markdown(row['agencia_codigo'] if pd.notna(row['agencia_codigo']) else "-")
        c[2].markdown(row['numero_conta'])
        c[3].markdown(row['agencia_nome'] if pd.notna(row['agencia_nome']) else "-")
        
        if c[4].button(" ", icon=":material/edit:", key=f"ed_cb_{row['id']}", use_container_width=True):
            st.session_state.modal_cb_ativa, st.session_state.modal_cb_id, st.session_state.modal_cb_dados = "editar", row['id'], row; st.rerun()
        if c[5].button(" ", icon=":material/delete:", key=f"del_cb_{row['id']}", use_container_width=True):
            st.session_state.modal_del_id_cb = row['id']; st.session_state.modal_del_nome_cb = f"Conta {row['numero_conta']} do {row['banco_nome']}"; st.rerun()
        st.markdown("<hr style='margin: 5px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
else: st.info("Nenhuma conta bancária encontrada.")

if st.session_state.modal_cb_ativa: modal_formulario(st.session_state.modal_cb_ativa, st.session_state.modal_cb_id, st.session_state.modal_cb_dados)
elif st.session_state.modal_del_id_cb is not None: modal_exclusao(st.session_state.modal_del_id_cb, st.session_state.modal_del_nome_cb)