import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import os
import time
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

# ==========================================
# 1. CONFIGURAÇÕES E ESTADOS DE SESSÃO
# ==========================================
UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

if 'modal_ativa' not in st.session_state: st.session_state.modal_ativa = None
if 'modal_id' not in st.session_state: st.session_state.modal_id = None
if 'modal_dados' not in st.session_state: st.session_state.modal_dados = None

# ==========================================
# 2. FUNÇÕES DE APOIO E CONSULTAS
# ==========================================
def formatar_moeda(valor):
    """Formata valores para o padrão monetário R$ (R maiúsculo)."""
    if pd.isna(valor): return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def carregar_dados(data_ini, data_fim):
    query = """
    SELECT 
        l.id, l.data_digitacao, l.data_vencimento, l.data_efetivacao, l.status,
        e.nome AS nome_base_evento, l.id_evento, l.id_classificacao,
        CASE WHEN l.total_parcelas > 1 
             THEN e.nome || ' (' || l.parcela_atual || '/' || l.total_parcelas || ')' 
             ELSE e.nome 
        END AS evento_exibicao,
        c.nome AS classificacao, c.icone, cat.nome AS categoria, cat.tipo,
        COALESCE(l.valor_realizado, l.valor_previsto) AS valor_final,
        l.observacao, l.valor_previsto
    FROM lancamentos l
    INNER JOIN eventos e ON l.id_evento = e.id
    INNER JOIN classificacoes c ON l.id_classificacao = c.id
    INNER JOIN categorias cat ON c.id_categoria = cat.id
    WHERE l.data_vencimento >= %s AND l.data_vencimento <= %s
    ORDER BY l.data_vencimento ASC, l.id ASC
    """
    return GerenciadorBanco.executar_query(query, (data_ini, data_fim))

def obter_auxiliares():
    df_eventos = GerenciadorBanco.executar_query("SELECT id, nome, id_classificacao FROM eventos ORDER BY nome ASC")
    df_class = GerenciadorBanco.executar_query("SELECT id, nome FROM classificacoes ORDER BY nome ASC")
    return df_eventos, df_class

# ==========================================
# 3. CALLBACKS DE NEGÓCIO
# ==========================================
def on_change_intervalo(fr_id, dt_emissao):
    intervalo = st.session_state.get(f"ln_intervalo_{fr_id}", 1)
    if intervalo > 1:
        nova_data = dt_emissao + timedelta(days=intervalo)
        st.session_state[f"ln_data_venc_{fr_id}"] = nova_data

def callback_salvar_lancamento(acao="inserir", id_lancamento=None):
    fr_id = st.session_state.get("ln_form_reset")
    dt_digitacao = date.today()
    dt_venc_manual = st.session_state.get(f"ln_data_venc_{fr_id}")
    valor = st.session_state.get(f"ln_valor_{fr_id}", 0.0)
    parcelas = st.session_state.get(f"ln_parcelas_{fr_id}", 1)
    intervalo = st.session_state.get(f"ln_intervalo_{fr_id}", 1)
    status_tela = st.session_state.get(f"ln_status_{fr_id}", "Pendente")
    obs = st.session_state.get(f"ln_obs_{fr_id}", "")
    modo_evento = st.session_state.get(f"ln_modo_ev_{fr_id}", "Selecionar evento")
    
    if valor <= 0:
        st.session_state.msg_erro = "O valor deve ser maior que zero."
        return

    id_evento_final = None
    if modo_evento == "Cadastrar novo":
        nome_novo = st.session_state.get(f"ln_novo_ev_nome_{fr_id}", "").strip()
        class_nova = st.session_state.get(f"ln_novo_ev_class_{fr_id}")
        if not nome_novo:
            st.session_state.msg_erro = "Preencha o nome do novo evento."
            return
        df_c = GerenciadorBanco.executar_query("SELECT id FROM classificacoes WHERE nome = %s LIMIT 1", (class_nova,))
        id_class_id = int(df_c.iloc[0]['id'])
        GerenciadorBanco.executar_query("INSERT INTO eventos (nome, id_classificacao) VALUES (%s, %s)", (nome_novo, id_class_id), is_select=False)
        df_e = GerenciadorBanco.executar_query("SELECT id FROM eventos WHERE nome = %s ORDER BY id DESC LIMIT 1", (nome_novo,))
        id_evento_final = int(df_e.iloc[0]['id'])
    else:
        evento_sel = st.session_state.get(f"ln_evento_sel_{fr_id}")
        df_ev = GerenciadorBanco.executar_query("SELECT id, id_classificacao FROM eventos WHERE nome = %s LIMIT 1", (evento_sel,))
        if df_ev.empty:
            st.session_state.msg_erro = "Selecione um evento válido."
            return
        id_evento_final = int(df_ev.iloc[0]['id'])

    if acao == "editar" and id_lancamento:
        status_final = "Pendente" if dt_venc_manual > dt_digitacao else status_tela
        val_realizado = valor if status_final == "Efetivado" else None
        dt_efetivacao = dt_venc_manual if status_final == "Efetivado" else None
        GerenciadorBanco.executar_query("UPDATE lancamentos SET data_vencimento = %s, data_efetivacao = %s, valor_previsto = %s, valor_realizado = %s, id_evento = %s, status = %s, observacao = %s WHERE id = %s", (dt_venc_manual, dt_efetivacao, valor, val_realizado, id_evento_final, status_final, obs, id_lancamento), is_select=False)
    else:
        for i in range(parcelas):
            data_venc = dt_venc_manual + timedelta(days=intervalo * i)
            status_final = "Pendente" if data_venc > dt_digitacao else status_tela
            val_realizado = valor if status_final == "Efetivado" else None
            dt_efetivacao = data_venc if status_final == "Efetivado" else None
            GerenciadorBanco.executar_query("INSERT INTO lancamentos (data_digitacao, data_vencimento, data_efetivacao, valor_previsto, valor_realizado, id_evento, id_classificacao, parcela_atual, total_parcelas, status, observacao) VALUES (%s, %s, %s, %s, %s, %s, (SELECT id_classificacao FROM eventos WHERE id=%s), %s, %s, %s, %s)", (dt_digitacao, data_venc, dt_efetivacao, valor, val_realizado, id_evento_final, id_evento_final, i+1, parcelas, status_final, obs), is_select=False)
    
    st.session_state.msg_sucesso_cont = (acao == "inserir")
    st.session_state.msg_sucesso = (acao != "inserir")
    if acao != "inserir": st.session_state.modal_ativa = None
    st.session_state.form_reset += 1

# ==========================================
# 4. MODAIS
# ==========================================
@st.dialog(":material/account_balance_wallet: Lançamento financeiro", width="large")
def modal_formulario(acao="inserir", id_lancamento=None, dados_pre=None):
    fr_id = st.session_state.get("form_reset", 0)
    st.session_state["ln_form_reset"] = fr_id
    df_eventos, df_class = obter_auxiliares()
    op_eventos = df_eventos['nome'].tolist() if not df_eventos.empty else []
    op_class = df_class['nome'].tolist() if not df_class.empty else []
    
    v_data_dig = date.today()
    if f"ln_valor_{fr_id}" not in st.session_state:
        st.session_state[f"ln_valor_{fr_id}"] = float(dados_pre['valor_previsto']) if dados_pre is not None else 0.0
    if f"ln_data_venc_{fr_id}" not in st.session_state:
        st.session_state[f"ln_data_venc_{fr_id}"] = dados_pre['data_vencimento'] if dados_pre is not None else date.today()
        
    v_evento_idx = 0
    if dados_pre is not None and dados_pre['nome_base_evento'] in op_eventos:
        v_evento_idx = op_eventos.index(dados_pre['nome_base_evento'])

    st.number_input("Valor total previsto (R$):", min_value=0.0, step=0.01, format="%.2f", key=f"ln_valor_{fr_id}")
    col_p, col_i, col_v, col_s = st.columns(4)
    col_p.number_input("Total de parcelas:", min_value=1, max_value=240, step=1, disabled=(acao=="editar"), key=f"ln_parcelas_{fr_id}")
    
    # CORREÇÃO CRÍTICA: Remoção do key_alt e restauração do callback de intervalo
    col_i.number_input("Intervalo de dias:", min_value=1, step=1, disabled=(acao=="editar"), key=f"ln_intervalo_{fr_id}", on_change=on_change_intervalo, args=(fr_id, v_data_dig))
    
    col_v.date_input("Data de vencimento:", format="DD/MM/YYYY", key=f"ln_data_venc_{fr_id}")
    travar_status = st.session_state[f"ln_data_venc_{fr_id}"] > v_data_dig
    if travar_status: st.session_state[f"ln_status_{fr_id}"] = "Pendente"
    col_s.selectbox("Status inicial:", ["Pendente", "Efetivado"], disabled=travar_status, key=f"ln_status_{fr_id}")
    
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    
    # CORREÇÃO DE CAPITALIZAÇÃO NO ALTERNADOR
    st.radio("Origem do evento:", ["Selecionar evento", "Cadastrar novo"], horizontal=True, label_visibility="collapsed", key=f"ln_modo_ev_{fr_id}")
    c_ev, c_cl = st.columns(2)
    
    # Lógica de interface baseada na nova capitalização
    if st.session_state.get(f"ln_modo_ev_{fr_id}", "Selecionar evento") == "Selecionar evento":
        with c_ev: evento_sel = st.selectbox("Evento originador (credor/devedor):", op_eventos, index=v_evento_idx, key=f"ln_evento_sel_{fr_id}")
        with c_cl:
            nome_cl_sync = ""
            if evento_sel:
                df_sync = GerenciadorBanco.executar_query("SELECT c.nome FROM classificacoes c INNER JOIN eventos e ON e.id_classificacao = c.id WHERE e.nome = %s LIMIT 1", (evento_sel,))
                if not df_sync.empty: nome_cl_sync = df_sync.iloc[0]['nome']
            st.text_input("Classificação vinculada:", value=nome_cl_sync, disabled=True, key=f"cl_sync_{fr_id}")
    else:
        with c_ev: st.text_input("Nome do novo evento:", key=f"ln_novo_ev_nome_{fr_id}")
        with c_cl: st.selectbox("Vincule a uma classificação:", op_class, key=f"ln_novo_ev_class_{fr_id}")

    st.text_input("Observações / Justificativas opcionais:", key=f"ln_obs_{fr_id}")
    st.markdown("<br>", unsafe_allow_html=True)
    b_sal, b_fec = st.columns(2)
    with b_sal:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_salvar_lancamento, args=(acao, id_lancamento))
    with b_fec:
        if st.button("Fechar", type="secondary", use_container_width=True):
            st.session_state.modal_ativa = None; st.rerun()

    if st.session_state.get("msg_sucesso_cont"):
        st.toast("Operação realizada com sucesso!", icon="✅"); time.sleep(2.0)
        st.session_state.msg_sucesso_cont = False; st.rerun()
    elif st.session_state.get("msg_sucesso"):
        st.toast("Operação realizada com sucesso!", icon="✅"); time.sleep(2.0)
        st.session_state.msg_sucesso = False; st.rerun()
    elif st.session_state.get("msg_erro"):
        st.toast(st.session_state.msg_erro, icon="❌"); st.session_state.msg_erro = ""

@st.dialog(":material/check_circle: Conciliar lançamento", width="small")
def modal_baixa(id_l, ev_nome, v_orig):
    fr_id = st.session_state.get("form_reset", 0)
    st.info(f"Baixa de: **{ev_nome}**")
    c1, c2 = st.columns(2)
    c1.date_input("Data real de efetivação:", value=date.today(), format="DD/MM/YYYY", key=f"bx_data_{fr_id}")
    c2.text_input("Valor original (R$):", value=f"{v_orig:,.2f}", disabled=True)
    c3, c4 = st.columns(2)
    c3.number_input("Adicionar juros/multa (+):", min_value=0.0, step=0.01, key=f"bx_juros_{fr_id}")
    c4.number_input("Aplicar desconto (-):", min_value=0.0, step=0.01, key=f"bx_desconto_{fr_id}")
    st.text_input("Observações:", key=f"bx_obs_{fr_id}")
    b_conf, b_canc = st.columns(2)
    with b_conf:
        if st.button("Confirmar", type="primary", use_container_width=True):
            juros = st.session_state.get(f"bx_juros_{fr_id}", 0.0)
            desc = st.session_state.get(f"bx_desconto_{fr_id}", 0.0)
            obs = st.session_state.get(f"bx_obs_{fr_id}", "")
            dt_baixa = st.session_state.get(f"bx_data_{fr_id}")
            GerenciadorBanco.executar_query("UPDATE lancamentos SET valor_realizado = %s, data_efetivacao = %s, status = 'Efetivado', observacao = %s WHERE id = %s", (v_orig + juros - desc, dt_baixa, obs, id_l), is_select=False)
            st.session_state.msg_sucesso = True; st.session_state.form_reset += 1; st.rerun()
    with b_canc:
        if st.button("Fechar", type="secondary", use_container_width=True):
            st.rerun()

@st.dialog(":material/delete: Excluir lançamento", width="small")
def modal_exclusao(id_l, ev_nome):
    st.error(f"Excluir permanentemente a parcela: **{ev_nome}**?")
    b_conf, b_canc = st.columns(2)
    with b_conf:
        if st.button("Confirmar", type="primary", use_container_width=True):
            GerenciadorBanco.executar_query("DELETE FROM lancamentos WHERE id = %s", (id_l,), is_select=False)
            st.session_state.msg_sucesso = True; st.session_state.form_reset += 1; st.rerun()
    with b_canc:
        if st.button("Fechar", type="secondary", use_container_width=True):
            st.rerun()

# ==========================================
# 5. INTERFACE PRINCIPAL
# ==========================================
if 'show_filtros_lanc' not in st.session_state: st.session_state.show_filtros_lanc = False
hoje = date.today()
primeiro_dia, ultimo_dia = hoje.replace(day=1), hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])
if 'f_ln_dt_ini' not in st.session_state: st.session_state.f_ln_dt_ini = primeiro_dia
if 'f_ln_dt_fim' not in st.session_state: st.session_state.f_ln_dt_fim = ultimo_dia

c_tit, c_fil, c_ins, c_mar = st.columns([5, 1.5, 1.5, 3])
with c_tit: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>account_balance_wallet</span> Fluxo de lançamentos</h3>", unsafe_allow_html=True)
with c_fil:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True):
        st.session_state.show_filtros_lanc = not st.session_state.show_filtros_lanc; st.rerun()
with c_ins:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True):
        st.session_state.modal_ativa, st.session_state.modal_id, st.session_state.modal_dados = "inserir", None, None; st.rerun()

if st.session_state.show_filtros_lanc:
    with st.container(border=True):
        f1, f2, f3, f4, f5 = st.columns([1.5, 1.5, 2, 2, 3])
        v_dt_ini = f1.date_input("Data inicial:", value=st.session_state.f_ln_dt_ini, format="DD/MM/YYYY")
        v_dt_fim = f2.date_input("Data final:", value=st.session_state.f_ln_dt_fim, format="DD/MM/YYYY")
        v_nat = f3.selectbox("Natureza:", ["Entradas e saídas", "Apenas receitas (+)", "Apenas despesas (-)"])
        v_stat = f4.selectbox("Status:", ["Todos os status", "Apenas pendentes", "Apenas efetivados"])
        df_ev_list, _ = obter_auxiliares()
        lista_ev = df_ev_list['nome'].tolist() if not df_ev_list.empty else []
        v_evs = f5.multiselect("Eventos específicos:", options=lista_ev, placeholder="Todos os eventos")
        
        _, b_col, _ = st.columns([4, 2, 4])
        if b_col.button("Pesquisar", type="tertiary", use_container_width=True):
            st.session_state.f_ln_dt_ini, st.session_state.f_ln_dt_fim = v_dt_ini, v_dt_fim; st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
df = carregar_dados(st.session_state.f_ln_dt_ini, st.session_state.f_ln_dt_fim)

st.markdown('''<div class="cabecalho-grid"><div style="display: flex;"><div style="flex: 0.9;">Emissão</div><div style="flex: 0.9;">Venc.</div><div style="flex: 1.1; text-align: center;">Status</div><div style="flex: 2.5;">Evento financeiro</div><div style="flex: 1.2; text-align: center;">Categoria</div><div style="flex: 1.0; text-align: right;">Entrada</div><div style="flex: 1.0; text-align: right;">Saída</div><div style="flex: 1.0; text-align: right;">Saldo</div><div style="flex: 2.6; text-align: center;">Ações</div></div></div>''', unsafe_allow_html=True)

if not df.empty:
    df['entrada'] = df.apply(lambda row: row['valor_final'] if row['tipo'] == 'Receita' else 0.0, axis=1)
    df['saida'] = df.apply(lambda row: row['valor_final'] if row['tipo'] == 'Despesa' else 0.0, axis=1)
    df['saldo'] = df['entrada'].cumsum() - df['saida'].cumsum()
    for _, row in df.iterrows():
        c = st.columns([0.9, 0.9, 1.1, 2.5, 1.2, 1.0, 1.0, 1.0, 0.65, 0.65, 0.65, 0.65], vertical_alignment="center")
        c[0].markdown(f"<span style='font-size: 13px;'>{row['data_digitacao'].strftime('%d/%m/%Y')}</span>", unsafe_allow_html=True)
        c[1].markdown(f"<span style='font-size: 13px; font-weight: 600;'>{row['data_vencimento'].strftime('%d/%m/%Y')}</span>", unsafe_allow_html=True)
        badge_s = "badge-efetivado" if row['status'].lower() == 'efetivado' else "badge-pendente"
        c[2].markdown(f"<div style='text-align: center;'><span class='{badge_s}'>{row['status']}</span></div>", unsafe_allow_html=True)
        icone_file, html_i = row['icone'], ""
        if pd.notna(icone_file) and icone_file != "Sem ícone":
            b64 = UtilitariosVisuais.obter_imagem_base64(os.path.join("Imagens", "Icones", icone_file))
            if b64: html_i = f"<img src='data:image/png;base64,{b64}' style='width: 52px; mix-blend-mode: multiply; margin-right: 15px;' />"
        c[3].markdown(f"<div style='display: flex; align-items: center;'>{html_i}<div><span style='font-weight: 700; font-size: 15px;'>{row['evento_exibicao']}</span><br><span style='font-size: 12px; color: #6c757d;'>{row['classificacao']}</span></div></div>", unsafe_allow_html=True)
        badge_c = "badge-receita" if row['tipo'] == 'Receita' else "badge-despesa"
        c[4].markdown(f"<div style='text-align: center;'><span class='{badge_c}'>{row['categoria']}</span></div>", unsafe_allow_html=True)
        c[5].markdown(f"<div style='text-align: right; color:#0f8661;'>{formatar_moeda(row['entrada']) if row['entrada']>0 else ''}</div>", unsafe_allow_html=True)
        c[6].markdown(f"<div style='text-align: right; color:#b3391b;'>{formatar_moeda(row['saida']) if row['saida']>0 else ''}</div>", unsafe_allow_html=True)
        c[7].markdown(f"<div style='text-align: right; font-weight: 700;'>{formatar_moeda(row['saldo'])}</div>", unsafe_allow_html=True)
        if row['status'].lower() == 'pendente':
            if c[8].button(" ", icon=":material/done_all:", key=f"bx_{row['id']}", use_container_width=True): modal_baixa(row['id'], row['evento_exibicao'], row['valor_previsto'])
        if c[9].button(" ", icon=":material/edit:", key=f"ed_{row['id']}", use_container_width=True):
            st.session_state.modal_ativa, st.session_state.modal_id, st.session_state.modal_dados = "editar", row['id'], row; st.rerun()
        if c[10].button(" ", icon=":material/content_copy:", key=f"dp_{row['id']}", use_container_width=True):
            st.session_state.modal_ativa, st.session_state.modal_id, st.session_state.modal_dados = "duplicar", None, row; st.rerun()
        if c[11].button(" ", icon=":material/delete:", key=f"del_{row['id']}", use_container_width=True): modal_exclusao(row['id'], row['evento_exibicao'])
        st.markdown("<hr style='margin: 5px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
else: st.info("Nenhum lançamento encontrado.")

if st.session_state.modal_ativa:
    modal_formulario(st.session_state.modal_ativa, st.session_state.modal_id, st.session_state.modal_dados)