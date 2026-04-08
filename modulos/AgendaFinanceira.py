import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import os
import time
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

# ==========================================
# 1. INICIALIZAÇÃO E GARANTIA DE ESTRUTURA
# ==========================================
@st.cache_resource(show_spinner=False)
def garantir_banco_seguro():
    GerenciadorBanco.inicializar_banco()

garantir_banco_seguro()
UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

if 'modal_ativa' not in st.session_state: st.session_state.modal_ativa = None
if 'modal_id' not in st.session_state: st.session_state.modal_id = None
if 'modal_dados' not in st.session_state: st.session_state.modal_dados = None
if 'modal_bx_id' not in st.session_state: st.session_state.modal_bx_id = None
if 'modal_bx_ev' not in st.session_state: st.session_state.modal_bx_ev = None
if 'modal_bx_vlr' not in st.session_state: st.session_state.modal_bx_vlr = None
if 'modal_del_id' not in st.session_state: st.session_state.modal_del_id = None
if 'modal_del_ev' not in st.session_state: st.session_state.modal_del_ev = None

# ==========================================
# 2. FUNÇÕES DE APOIO E CONSULTAS
# ==========================================
def formatar_moeda(valor):
    if pd.isna(valor): return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_data(show_spinner=False, ttl=600)
def obter_saldo_anterior(data_ini):
    query = """
    SELECT 
        COALESCE(SUM(CASE WHEN cat.tipo = 'Receita' THEN l.valor_realizado ELSE 0 END), 0) -
        COALESCE(SUM(CASE WHEN cat.tipo = 'Despesa' THEN l.valor_realizado ELSE 0 END), 0) as saldo
    FROM lancamentos l
    INNER JOIN classificacoes c ON l.id_classificacao = c.id
    INNER JOIN categorias cat ON c.id_categoria = cat.id
    WHERE l.status = 'Efetivado' AND l.data_efetivacao < %s
    """
    df = GerenciadorBanco.executar_query(query, (data_ini,))
    return float(df.iloc[0]['saldo']) if not df.empty else 0.0

@st.cache_data(show_spinner=False, ttl=600)
def carregar_dados(data_ini, data_fim):
    query = """
    SELECT 
        l.id, l.data_digitacao, l.data_vencimento, l.data_efetivacao, l.status,
        e.nome AS nome_base_evento, l.id_evento, l.id_classificacao,
        CASE WHEN l.total_parcelas > 1 THEN e.nome || ' (' || l.parcela_atual || '/' || l.total_parcelas || ')' ELSE e.nome END AS evento_exibicao,
        c.nome AS classificacao, c.icone, cat.nome AS categoria, cat.tipo,
        COALESCE(l.valor_realizado, l.valor_previsto) AS valor_final,
        l.observacao, l.valor_previsto, l.id_conta_bancaria
    FROM lancamentos l
    INNER JOIN eventos e ON l.id_evento = e.id
    INNER JOIN classificacoes c ON l.id_classificacao = c.id
    INNER JOIN categorias cat ON c.id_categoria = cat.id
    WHERE l.data_vencimento >= %s AND l.data_vencimento <= %s
    ORDER BY l.data_vencimento ASC, l.id ASC
    """
    return GerenciadorBanco.executar_query(query, (data_ini, data_fim))

@st.cache_data(show_spinner=False, ttl=3600)
def obter_auxiliares():
    df_ev = GerenciadorBanco.executar_query("SELECT id, nome, id_classificacao FROM eventos ORDER BY nome ASC")
    df_cls = GerenciadorBanco.executar_query("SELECT id, nome FROM classificacoes ORDER BY nome ASC")
    df_bco = GerenciadorBanco.executar_query("SELECT codigo, nome FROM bancos ORDER BY nome ASC")
    df_cb = GerenciadorBanco.executar_query("SELECT id, numero_conta, agencia_codigo, banco_codigo FROM contas_bancarias ORDER BY id DESC")
    return df_ev, df_cls, df_bco, df_cb

# ==========================================
# 3. CALLBACKS DE NEGÓCIO
# ==========================================
def on_change_intervalo(fr_id, dt_emissao):
    intervalo = st.session_state.get(f"ln_intervalo_{fr_id}", 1)
    if intervalo > 1: st.session_state[f"ln_data_venc_{fr_id}"] = dt_emissao + timedelta(days=intervalo)

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
        df_ev = GerenciadorBanco.executar_query("SELECT id FROM eventos WHERE nome = %s LIMIT 1", (evento_sel,))
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
    
    st.cache_data.clear() 
    st.session_state.msg_sucesso_cont = (acao == "inserir")
    st.session_state.msg_sucesso = (acao != "inserir")
    if acao != "inserir": st.session_state.modal_ativa = None
    st.session_state.form_reset += 1

# ==========================================
# 4. MODAIS ROTEADAS
# ==========================================
@st.dialog(":material/account_balance_wallet: Lançamento financeiro", width="large")
def modal_formulario(acao="inserir", id_lancamento=None, dados_pre=None):
    fr_id = st.session_state.get("form_reset", 0)
    st.session_state["ln_form_reset"] = fr_id
    df_eventos, df_class, _, _ = obter_auxiliares()
    op_eventos = df_eventos['nome'].tolist() if not df_eventos.empty else []
    op_class = df_class['nome'].tolist() if not df_class.empty else []
    
    v_data_dig = date.today()
    if f"ln_valor_{fr_id}" not in st.session_state:
        st.session_state[f"ln_valor_{fr_id}"] = float(dados_pre['valor_previsto']) if dados_pre is not None else 0.0
    if f"ln_data_venc_{fr_id}" not in st.session_state:
        st.session_state[f"ln_data_venc_{fr_id}"] = dados_pre['data_vencimento'] if dados_pre is not None else date.today()
        
    v_evento_idx = 0
    if dados_pre is not None and dados_pre['nome_base_evento'] in op_eventos: v_evento_idx = op_eventos.index(dados_pre['nome_base_evento'])

    st.number_input("Valor total previsto (R$):", min_value=0.0, step=0.01, format="%.2f", key=f"ln_valor_{fr_id}")
    col_p, col_i, col_v, col_s = st.columns(4)
    col_p.number_input("Total de parcelas:", min_value=1, max_value=240, step=1, disabled=(acao=="editar"), key=f"ln_parcelas_{fr_id}")
    col_i.number_input("Intervalo de dias:", min_value=1, step=1, disabled=(acao=="editar"), key=f"ln_intervalo_{fr_id}", on_change=on_change_intervalo, args=(fr_id, v_data_dig))
    col_v.date_input("Data de vencimento:", format="DD/MM/YYYY", key=f"ln_data_venc_{fr_id}")
    travar_status = st.session_state[f"ln_data_venc_{fr_id}"] > v_data_dig
    if travar_status: st.session_state[f"ln_status_{fr_id}"] = "Pendente"
    col_s.selectbox("Status inicial:", ["Pendente", "Efetivado"], disabled=travar_status, key=f"ln_status_{fr_id}")
    
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    st.radio("Origem do evento:", ["Selecionar evento", "Cadastrar novo"], horizontal=True, label_visibility="collapsed", key=f"ln_modo_ev_{fr_id}")
    c_ev, c_cl = st.columns(2)
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
    _, _, df_bancos, df_contas = obter_auxiliares()
    
    op_bancos = [f"{r['codigo']} - {r['nome']}" for _, r in df_bancos.iterrows()] if not df_bancos.empty else []
    op_contas = [f"{r['id']} - Banco {r['banco_codigo']} | Ag: {r['agencia_codigo']} | CC: {r['numero_conta']}" for _, r in df_contas.iterrows()] if not df_contas.empty else []

    if f"bx_juros_{fr_id}" not in st.session_state: st.session_state[f"bx_juros_{fr_id}"] = 0.0
    if f"bx_desconto_{fr_id}" not in st.session_state: st.session_state[f"bx_desconto_{fr_id}"] = 0.0
    if f"bx_final_{fr_id}" not in st.session_state: st.session_state[f"bx_final_{fr_id}"] = float(v_orig)

    def sync_pelo_final():
        vf = round(st.session_state[f"bx_final_{fr_id}"], 2)
        vo = round(float(v_orig), 2)
        if vf > vo:
            st.session_state[f"bx_juros_{fr_id}"] = round(vf - vo, 2)
            st.session_state[f"bx_desconto_{fr_id}"] = 0.0
        else:
            st.session_state[f"bx_juros_{fr_id}"] = 0.0
            st.session_state[f"bx_desconto_{fr_id}"] = round(vo - vf, 2)

    def sync_pelos_ajustes():
        j = round(st.session_state[f"bx_juros_{fr_id}"], 2)
        d = round(st.session_state[f"bx_desconto_{fr_id}"], 2)
        vo = round(float(v_orig), 2)
        st.session_state[f"bx_final_{fr_id}"] = round(vo + j - d, 2)

    st.info(f"Baixa de: **{ev_nome}**")
    
    c1, c2 = st.columns(2)
    c1.date_input("Data real de efetivação:", value=date.today(), format="DD/MM/YYYY", key=f"bx_data_{fr_id}")
    c2.text_input("Valor original (R$):", value=f"{v_orig:,.2f}", disabled=True)
    
    c3, c4 = st.columns(2)
    c3.number_input("Adicionar juros/multa (+):", min_value=0.0, step=0.01, key=f"bx_juros_{fr_id}", on_change=sync_pelos_ajustes)
    c4.number_input("Aplicar desconto (-):", min_value=0.0, step=0.01, key=f"bx_desconto_{fr_id}", on_change=sync_pelos_ajustes)
    
    st.markdown("<hr style='margin: 15px 0 5px 0;'>", unsafe_allow_html=True)
    st.number_input("VALOR FINAL A EFETIVAR (R$):", min_value=0.0, step=0.01, key=f"bx_final_{fr_id}", on_change=sync_pelo_final)
    
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    st.radio("Origem da conta bancária:", ["Selecionar conta", "Cadastrar nova"], horizontal=True, label_visibility="collapsed", key=f"bx_modo_cb_{fr_id}")
    
    if st.session_state.get(f"bx_modo_cb_{fr_id}", "Selecionar conta") == "Selecionar conta":
        st.selectbox("Conta da transação:", op_contas, key=f"bx_conta_sel_{fr_id}")
    else:
        cb_col1, cb_col2 = st.columns(2)
        cb_col1.selectbox("Banco associado:", op_bancos, key=f"bx_nova_cb_banco_{fr_id}")
        cb_col2.text_input("Número da agência:", key=f"bx_nova_cb_ag_{fr_id}")
        st.text_input("Número da conta:", key=f"bx_nova_cb_cc_{fr_id}")
    
    st.text_input("Observação da baixa (opcional):", key=f"bx_obs_{fr_id}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    b_conf, b_canc = st.columns(2)
    with b_conf:
        if st.button("Confirmar", type="primary", use_container_width=True):
            id_conta_final = None
            modo_cb = st.session_state.get(f"bx_modo_cb_{fr_id}", "Selecionar conta")
            
            if modo_cb == "Cadastrar nova":
                nova_ag = st.session_state.get(f"bx_nova_cb_ag_{fr_id}", "").strip()
                nova_cc = st.session_state.get(f"bx_nova_cb_cc_{fr_id}", "").strip()
                banco_sel = st.session_state.get(f"bx_nova_cb_banco_{fr_id}")
                
                if nova_cc and banco_sel:
                    cod_banco = banco_sel.split(" - ")[0]
                    GerenciadorBanco.executar_query("INSERT INTO contas_bancarias (numero_conta, agencia_codigo, banco_codigo) VALUES (%s, %s, %s)", (nova_cc, nova_ag, cod_banco), is_select=False)
                    df_cb_new = GerenciadorBanco.executar_query("SELECT id FROM contas_bancarias WHERE numero_conta = %s ORDER BY id DESC LIMIT 1", (nova_cc,))
                    if not df_cb_new.empty: id_conta_final = int(df_cb_new.iloc[0]['id'])
            else:
                sel_cb = st.session_state.get(f"bx_conta_sel_{fr_id}")
                if sel_cb: id_conta_final = int(sel_cb.split(" - ")[0])

            valor_final_banco = round(st.session_state.get(f"bx_final_{fr_id}", float(v_orig)), 2)
            obs = st.session_state.get(f"bx_obs_{fr_id}", "")
            dt_baixa = st.session_state.get(f"bx_data_{fr_id}")
            
            GerenciadorBanco.executar_query("UPDATE lancamentos SET valor_realizado = %s, data_efetivacao = %s, status = 'Efetivado', observacao = %s, id_conta_bancaria = %s WHERE id = %s", (valor_final_banco, dt_baixa, obs, id_conta_final, id_l), is_select=False)
            st.cache_data.clear() 
            st.session_state.msg_sucesso = True; st.session_state.form_reset += 1
            st.session_state.modal_bx_id = None; st.rerun()
    with b_canc:
        if st.button("Fechar", type="secondary", use_container_width=True): st.session_state.modal_bx_id = None; st.rerun()

@st.dialog(":material/delete: Excluir lançamento", width="small")
def modal_exclusao(id_l, ev_nome):
    st.error(f"Excluir permanentemente a parcela: **{ev_nome}**?")
    b_conf, b_canc = st.columns(2)
    with b_conf:
        if st.button("Confirmar", type="primary", use_container_width=True):
            GerenciadorBanco.executar_query("DELETE FROM lancamentos WHERE id = %s", (id_l,), is_select=False)
            st.cache_data.clear() 
            st.session_state.msg_sucesso = True; st.session_state.form_reset += 1
            st.session_state.modal_del_id = None; st.rerun()
    with b_canc:
        if st.button("Fechar", type="secondary", use_container_width=True): st.session_state.modal_del_id = None; st.rerun()

# ==========================================
# 5. INICIALIZAÇÃO DE ESTADOS E DATAS
# ==========================================
if 'show_filtros_lanc' not in st.session_state: st.session_state.show_filtros_lanc = False
hoje = date.today()
primeiro_dia, ultimo_dia = hoje.replace(day=1), hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])

if 'f_ln_dt_ini' not in st.session_state: st.session_state.f_ln_dt_ini = primeiro_dia
if 'f_ln_dt_fim' not in st.session_state: st.session_state.f_ln_dt_fim = ultimo_dia
if 'f_ln_nat' not in st.session_state: st.session_state.f_ln_nat = "Entradas e saídas"
if 'f_ln_stat' not in st.session_state: st.session_state.f_ln_stat = "Todos os status"
if 'f_ln_evs' not in st.session_state: st.session_state.f_ln_evs = []

# ==========================================
# 6. PROCESSAMENTO DOS DADOS (Antes da UI)
# ==========================================
df_base = carregar_dados(st.session_state.f_ln_dt_ini, st.session_state.f_ln_dt_fim).copy()

saldo_anterior = obter_saldo_anterior(st.session_state.f_ln_dt_ini)
entradas_periodo = 0.0
saidas_periodo = 0.0

if not df_base.empty:
    df_base['entrada'] = df_base.apply(lambda row: row['valor_final'] if row['tipo'] == 'Receita' else 0.0, axis=1)
    df_base['saida'] = df_base.apply(lambda row: row['valor_final'] if row['tipo'] == 'Despesa' else 0.0, axis=1)
    df_base['saldo_acumulado'] = df_base['entrada'].cumsum() - df_base['saida'].cumsum() + saldo_anterior
    
    if st.session_state.f_ln_nat == "Apenas receitas (+)": df_base = df_base[df_base['tipo'] == 'Receita']
    elif st.session_state.f_ln_nat == "Apenas despesas (-)": df_base = df_base[df_base['tipo'] == 'Despesa']
        
    if st.session_state.f_ln_stat == "Apenas pendentes": df_base = df_base[df_base['status'].str.lower() == 'pendente']
    elif st.session_state.f_ln_stat == "Apenas efetivados": df_base = df_base[df_base['status'].str.lower() == 'efetivado']
        
    if st.session_state.f_ln_evs: df_base = df_base[df_base['nome_base_evento'].isin(st.session_state.f_ln_evs)]
    
    entradas_periodo = df_base['entrada'].sum()
    saidas_periodo = df_base['saida'].sum()

df = df_base
saldo_projetado = saldo_anterior + entradas_periodo - saidas_periodo
cor_proj = "#20c997" if saldo_projetado >= 0 else "#dc3545"

# ==========================================
# 7. RENDERIZAÇÃO DA INTERFACE (Hierarquia Invertida)
# ==========================================
# 7.1 CABEÇALHO SUPERIOR
c_tit, c_fil, c_ins, c_mar = st.columns([5, 1.5, 1.5, 3])
with c_tit: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>calendar_month</span> Agenda Financeira</h3>", unsafe_allow_html=True)
with c_fil:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True): st.session_state.show_filtros_lanc = not st.session_state.show_filtros_lanc; st.rerun()
with c_ins:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True): st.session_state.modal_ativa, st.session_state.modal_id, st.session_state.modal_dados = "inserir", None, None; st.rerun()

# 7.2 CARDS DE RESUMO (Ficam fixos visualmente no topo)
html_cards = f"""
<div style="display: flex; gap: 15px; margin-bottom: 20px; margin-top: 5px;">
    <div style="flex: 1; background-color: #6c757d; color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Saldo anterior (Ref. Filtro)</div>
        <div style="font-size: 22px; font-weight: 700; margin-top: 5px;">{formatar_moeda(saldo_anterior)}</div>
    </div>
    <div style="flex: 1; background-color: #20c997; color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">(+) Entradas no período</div>
        <div style="font-size: 22px; font-weight: 700; margin-top: 5px;">{formatar_moeda(entradas_periodo)}</div>
    </div>
    <div style="flex: 1; background-color: #e76f51; color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">(-) Saídas no período</div>
        <div style="font-size: 22px; font-weight: 700; margin-top: 5px;">{formatar_moeda(saidas_periodo)}</div>
    </div>
    <div style="flex: 1; background-color: #1a2a40; color: {cor_proj}; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 5px solid {cor_proj};">
        <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: white;">(=) Saldo projetado</div>
        <div style="font-size: 22px; font-weight: 700; margin-top: 5px;">{formatar_moeda(saldo_projetado)}</div>
    </div>
</div>
"""
st.markdown(html_cards, unsafe_allow_html=True)

# 7.3 PAINEL DE FILTROS (Abre entre os cards e a tabela)
@st.fragment
def renderizar_painel_filtros():
    with st.container(border=True):
        f1, f2, f3, f4 = st.columns([1.5, 1.5, 2, 2])
        v_dt_ini = f1.date_input("Data inicial:", value=st.session_state.f_ln_dt_ini, format="DD/MM/YYYY")
        v_dt_fim = f2.date_input("Data final:", value=st.session_state.f_ln_dt_fim, format="DD/MM/YYYY")
        
        op_nat = ["Entradas e saídas", "Apenas receitas (+)", "Apenas despesas (-)"]
        idx_nat = op_nat.index(st.session_state.f_ln_nat) if st.session_state.f_ln_nat in op_nat else 0
        v_nat = f3.selectbox("Natureza:", op_nat, index=idx_nat)
        
        op_stat = ["Todos os status", "Apenas pendentes", "Apenas efetivados"]
        idx_stat = op_stat.index(st.session_state.f_ln_stat) if st.session_state.f_ln_stat in op_stat else 0
        v_stat = f4.selectbox("Status:", op_stat, index=idx_stat)
        
        f5, f_check, f_btn = st.columns([5.5, 1.5, 1.5], vertical_alignment="bottom")
        df_ev_list, _, _, _ = obter_auxiliares()
        lista_ev = df_ev_list['nome'].tolist() if not df_ev_list.empty else []
        v_evs = f5.multiselect("Eventos específicos:", options=lista_ev, default=st.session_state.f_ln_evs, placeholder="Todos os eventos")
        
        with f_check:
            auto_refresh = st.checkbox("Refresh automático", value=st.session_state.get('f_ln_auto', False), key='f_ln_auto')
        
        with f_btn:
            mudou_algo = (v_dt_ini != st.session_state.f_ln_dt_ini or
                          v_dt_fim != st.session_state.f_ln_dt_fim or
                          v_nat != st.session_state.f_ln_nat or
                          v_stat != st.session_state.f_ln_stat or
                          v_evs != st.session_state.f_ln_evs)

            if auto_refresh:
                st.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True, disabled=True)
                if mudou_algo:
                    st.session_state.f_ln_dt_ini = v_dt_ini
                    st.session_state.f_ln_dt_fim = v_dt_fim
                    st.session_state.f_ln_nat = v_nat
                    st.session_state.f_ln_stat = v_stat
                    st.session_state.f_ln_evs = v_evs
                    st.rerun()
            else:
                if st.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True):
                    st.session_state.f_ln_dt_ini = v_dt_ini
                    st.session_state.f_ln_dt_fim = v_dt_fim
                    st.session_state.f_ln_nat = v_nat
                    st.session_state.f_ln_stat = v_stat
                    st.session_state.f_ln_evs = v_evs
                    st.rerun()

if st.session_state.show_filtros_lanc:
    renderizar_painel_filtros()

# 7.4 GRID DE DADOS
st.markdown('''<div class="cabecalho-grid"><div style="display: flex;"><div style="flex: 1.0;">Emissão</div><div style="flex: 1.0;">Venc.</div><div style="flex: 1.1; text-align: center;">Status</div><div style="flex: 2.5;">Evento financeiro</div><div style="flex: 1.2; text-align: center;">Categoria</div><div style="flex: 1.0; text-align: right;">Entrada</div><div style="flex: 1.0; text-align: right;">Saída</div><div style="flex: 1.0; text-align: right;">Saldo</div><div style="flex: 2.0; text-align: center;">Ações</div></div></div>''', unsafe_allow_html=True)

if not df.empty:
    for _, row in df.iterrows():
        c = st.columns([1.0, 1.0, 1.1, 2.5, 1.2, 1.0, 1.0, 1.0, 0.5, 0.5, 0.5, 0.5], vertical_alignment="center")
        cor_venc, peso_venc = "#1a2a40", "600"
        if row['status'].lower() == 'pendente':
            if row['data_vencimento'] < hoje: cor_venc, peso_venc = "#dc3545", "800"
            elif row['data_vencimento'] == hoje: cor_venc, peso_venc = "#fd7e14", "800"

        c[0].markdown(f"<span style='font-size: 13px; white-space: nowrap;'>{row['data_digitacao'].strftime('%d/%m/%Y')}</span>", unsafe_allow_html=True)
        c[1].markdown(f"<span style='font-size: 13px; font-weight: {peso_venc}; color: {cor_venc}; white-space: nowrap;'>{row['data_vencimento'].strftime('%d/%m/%Y')}</span>", unsafe_allow_html=True)
        
        badge_s = "badge-efetivado" if row['status'].lower() == 'efetivado' else "badge-pendente"
        c[2].markdown(f"<div style='text-align: center;'><span class='{badge_s}'>{row['status']}</span></div>", unsafe_allow_html=True)
        
        icone_file, html_i = row['icone'], ""
        if pd.notna(icone_file) and icone_file != "Sem ícone":
            b64 = UtilitariosVisuais.obter_imagem_base64(os.path.join("Imagens", "Icones", icone_file))
            if b64: html_i = f"<img src='data:image/png;base64,{b64}' style='width: 52px; mix-blend-mode: multiply; margin-right: 15px;' />"
        c[3].markdown(f"<div style='display: flex; align-items: center;'>{html_i}<div><span style='font-weight: 700; font-size: 15px;'>{row['evento_exibicao']}</span><br><span style='font-size: 12px; color: #6c757d;'>{row['classificacao']}</span></div></div>", unsafe_allow_html=True)
        
        badge_c = "badge-receita" if row['tipo'] == 'Receita' else "badge-despesa"
        c[4].markdown(f"<div style='text-align: center;'><span class='{badge_c}'>{row['categoria']}</span></div>", unsafe_allow_html=True)
        
        c[5].markdown(f"<div style='text-align: right; color:#0f8661; white-space: nowrap;'>{formatar_moeda(row['entrada']) if row['entrada']>0 else ''}</div>", unsafe_allow_html=True)
        c[6].markdown(f"<div style='text-align: right; color:#b3391b; white-space: nowrap;'>{formatar_moeda(row['saida']) if row['saida']>0 else ''}</div>", unsafe_allow_html=True)
        c[7].markdown(f"<div style='text-align: right; font-weight: 700; white-space: nowrap;'>{formatar_moeda(row['saldo_acumulado'])}</div>", unsafe_allow_html=True)
        
        if row['status'].lower() == 'pendente':
            if c[8].button(" ", icon=":material/done_all:", key=f"bx_{row['id']}", use_container_width=True, help="Conciliar Baixa"):
                st.session_state.modal_bx_id = row['id']; st.session_state.modal_bx_ev = row['evento_exibicao']; st.session_state.modal_bx_vlr = row['valor_previsto']; st.rerun()
        if c[9].button(" ", icon=":material/edit:", key=f"ed_{row['id']}", use_container_width=True, help="Editar"):
            st.session_state.modal_ativa, st.session_state.modal_id, st.session_state.modal_dados = "editar", row['id'], row; st.rerun()
        if c[10].button(" ", icon=":material/content_copy:", key=f"dp_{row['id']}", use_container_width=True, help="Duplicar"):
            st.session_state.modal_ativa, st.session_state.modal_id, st.session_state.modal_dados = "duplicar", None, row; st.rerun()
        if c[11].button(" ", icon=":material/delete:", key=f"del_{row['id']}", use_container_width=True, help="Excluir"): 
            st.session_state.modal_del_id = row['id']; st.session_state.modal_del_ev = row['evento_exibicao']; st.rerun()
        st.markdown("<hr style='margin: 5px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
else: st.info("Nenhum lançamento encontrado neste período ou para o filtro selecionado.")

# MOTOR CENTRAL DE RENDERIZAÇÃO DE MODAIS
if st.session_state.modal_ativa: modal_formulario(st.session_state.modal_ativa, st.session_state.modal_id, st.session_state.modal_dados)
elif st.session_state.modal_bx_id is not None: modal_baixa(st.session_state.modal_bx_id, st.session_state.modal_bx_ev, st.session_state.modal_bx_vlr)
elif st.session_state.modal_del_id is not None: modal_exclusao(st.session_state.modal_del_id, st.session_state.modal_del_ev)