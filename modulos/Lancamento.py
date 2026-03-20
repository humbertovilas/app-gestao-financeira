import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import os
import time
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

def formatar_moeda(valor):
    if pd.isna(valor): return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ==========================================
# GATILHOS DE INTERAÇÃO (CALLBACKS DE TELA)
# ==========================================
def on_change_intervalo(fr_id, dt_emissao):
    """Calcula automaticamente o 1º vencimento se o intervalo for maior que 1."""
    intervalo = st.session_state.get(f"ln_intervalo_{fr_id}", 1)
    if intervalo > 1:
        nova_data = dt_emissao + timedelta(days=intervalo)
        st.session_state[f"ln_data_venc_{fr_id}"] = nova_data
        if nova_data > dt_emissao:
            st.session_state[f"ln_status_{fr_id}"] = "Pendente"

# ==========================================
# REGRAS DE NEGÓCIO E CONSULTAS
# ==========================================
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
    df_eventos = GerenciadorBanco.executar_query("SELECT id, nome, id_classificacao FROM eventos ORDER BY nome")
    df_class = GerenciadorBanco.executar_query("SELECT id, nome FROM classificacoes ORDER BY nome")
    return df_eventos, df_class

# ==========================================
# CALLBACKS (GRAVAÇÃO, EDIÇÃO, CONCILIAÇÃO)
# ==========================================
def callback_salvar_lancamento(acao="inserir", id_lancamento=None):
    fr_id = st.session_state.get("ln_form_reset")
    
    dt_digitacao = date.today()
    dt_venc_manual = st.session_state.get(f"ln_data_venc_{fr_id}")
    
    valor = st.session_state.get(f"ln_valor_{fr_id}", 0.0)
    parcelas = st.session_state.get(f"ln_parcelas_{fr_id}", 1)
    intervalo = st.session_state.get(f"ln_intervalo_{fr_id}", 1)
    status_tela = st.session_state.get(f"ln_status_{fr_id}", "Pendente")
    obs = st.session_state.get(f"ln_obs_{fr_id}", "")
    
    evento_selecionado = st.session_state.get(f"ln_evento_sel_{fr_id}")
    classificacao_selecionada = st.session_state.get(f"ln_class_sel_{fr_id}")
    
    if valor <= 0:
        st.session_state.msg_erro = "O valor deve ser maior que zero."
        return

    id_evento_final = None
    id_class_final = None

    if evento_selecionado == "+ Criar novo evento...":
        nome_novo_evento = st.session_state.get(f"ln_novo_evento_{fr_id}", "").strip()
        
        if classificacao_selecionada:
            df_cls_id = GerenciadorBanco.executar_query("SELECT id FROM classificacoes WHERE nome = %s LIMIT 1", (classificacao_selecionada,))
            if not df_cls_id.empty:
                id_class_final = int(df_cls_id.iloc[0]['id'])
        
        if not nome_novo_evento or not id_class_final:
            st.session_state.msg_erro = "Preencha o nome do novo evento e a classificação vinculada."
            return
            
        GerenciadorBanco.executar_query("INSERT INTO eventos (nome, id_classificacao) VALUES (%s, %s)", (nome_novo_evento, id_class_final), is_select=False)
        df_novo = GerenciadorBanco.executar_query("SELECT id FROM eventos WHERE nome = %s ORDER BY id DESC LIMIT 1", (nome_novo_evento,))
        id_evento_final = int(df_novo.iloc[0]['id'])
    else:
        df_ev = GerenciadorBanco.executar_query("SELECT id, id_classificacao FROM eventos WHERE nome = %s LIMIT 1", (evento_selecionado,))
        if not df_ev.empty:
            id_evento_final = int(df_ev.iloc[0]['id'])
            id_class_final = int(df_ev.iloc[0]['id_classificacao'])

    if acao == "editar" and id_lancamento:
        status_final = "Pendente" if dt_venc_manual > dt_digitacao else status_tela
        val_realizado = valor if status_final == "Efetivado" else None
        dt_efetivacao = dt_venc_manual if status_final == "Efetivado" else None
        
        GerenciadorBanco.executar_query(
            """UPDATE lancamentos 
               SET data_vencimento = %s, data_efetivacao = %s, valor_previsto = %s, valor_realizado = %s, 
                   id_evento = %s, id_classificacao = %s, status = %s, observacao = %s 
               WHERE id = %s""",
            (dt_venc_manual, dt_efetivacao, valor, val_realizado, id_evento_final, id_class_final, status_final, obs, id_lancamento),
            is_select=False
        )
    else:
        for i in range(parcelas):
            data_venc = dt_venc_manual + timedelta(days=intervalo * i)
            status_final = "Pendente" if data_venc > dt_digitacao else status_tela
            val_realizado = valor if status_final == "Efetivado" else None
            dt_efetivacao = data_venc if status_final == "Efetivado" else None
            
            GerenciadorBanco.executar_query(
                """INSERT INTO lancamentos 
                   (data_digitacao, data_vencimento, data_efetivacao, valor_previsto, valor_realizado, id_evento, id_classificacao, parcela_atual, total_parcelas, status, observacao) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (dt_digitacao, data_venc, dt_efetivacao, valor, val_realizado, id_evento_final, id_class_final, i+1, parcelas, status_final, obs),
                is_select=False
            )
    
    if acao == "inserir":
        st.session_state.msg_sucesso_cont = True # Mantém a modal aberta
    else:
        st.session_state.msg_sucesso = True # Fecha a modal
        
    st.session_state.form_cleared = True
    st.session_state.form_reset += 1

def callback_conciliacao(id_lancamento, valor_original):
    fr_id = st.session_state.get("ln_form_reset")
    juros = st.session_state.get(f"bx_juros_{fr_id}", 0.0)
    desconto = st.session_state.get(f"bx_desconto_{fr_id}", 0.0)
    obs = st.session_state.get(f"bx_obs_{fr_id}", "")
    dt_baixa = st.session_state.get(f"bx_data_{fr_id}")
    
    valor_final = valor_original + juros - desconto
    
    if valor_final < 0:
        st.session_state.msg_erro = "O valor final não pode ser negativo."
        return
        
    GerenciadorBanco.executar_query(
        "UPDATE lancamentos SET valor_realizado = %s, data_efetivacao = %s, status = 'Efetivado', observacao = %s WHERE id = %s",
        (valor_final, dt_baixa, obs, id_lancamento), is_select=False
    )
    st.session_state.msg_sucesso = True
    st.session_state.form_cleared = True
    st.session_state.form_reset += 1

def callback_exclusao(id_lancamento):
    GerenciadorBanco.executar_query("DELETE FROM lancamentos WHERE id = %s", (int(id_lancamento),), is_select=False)
    st.session_state.msg_sucesso = True
    st.session_state.form_cleared = True
    st.session_state.form_reset += 1

# ==========================================
# MODAIS (UX/UI MESTRE)
# ==========================================
@st.dialog(":material/account_balance_wallet: Lançamento financeiro", width="large")
def modal_formulario(acao="inserir", id_lancamento=None, dados_pre=None):
    # O validador global de mensagens foi removido do topo para evitar fechamento indesejado
    fr_id = st.session_state.get("form_reset", 0)
    st.session_state["ln_form_reset"] = fr_id
    
    df_eventos, df_class = obter_auxiliares()
    
    op_eventos = ["+ Criar novo evento..."] + (df_eventos['nome'].tolist() if not df_eventos.empty else [])
    op_class = df_class['nome'].tolist() if not df_class.empty else []
    
    v_data_dig = dados_pre['data_digitacao'] if (dados_pre is not None and pd.notnull(dados_pre['data_digitacao'])) else date.today()
    
    if f"ln_data_venc_{fr_id}" in st.session_state:
        v_data_venc = st.session_state[f"ln_data_venc_{fr_id}"]
    else:
        v_data_venc = dados_pre['data_vencimento'] if dados_pre is not None else date.today()
        
    if f"ln_valor_{fr_id}" in st.session_state:
        v_valor = st.session_state[f"ln_valor_{fr_id}"]
    else:
        v_valor = float(dados_pre['valor_previsto']) if dados_pre is not None else 0.0
        
    if f"ln_obs_{fr_id}" in st.session_state:
        v_obs = st.session_state[f"ln_obs_{fr_id}"]
    else:
        v_obs = dados_pre['observacao'] if dados_pre is not None and dados_pre['observacao'] else ""
        
    v_evento_idx = 0
    if dados_pre is not None:
        v_status = 1 if dados_pre['status'] == 'Efetivado' else 0
        str_evento = dados_pre['nome_base_evento']
        if str_evento in op_eventos:
            v_evento_idx = op_eventos.index(str_evento)
    else:
        v_status = 0

    if acao == "editar":
        st.info("Modo de Edição: Você está alterando apenas esta parcela específica.")
    elif acao == "duplicar":
        st.info("Modo de Duplicação: Um novo lançamento independente será criado.")

    c1, c2 = st.columns(2)
    c1.date_input("Data de digitação (Emissão):", value=v_data_dig, format="DD/MM/YYYY", disabled=True, key=f"ln_data_dig_{fr_id}")
    c2.number_input("Valor total previsto (R$):", min_value=0.0, step=0.01, value=v_valor, format="%.2f", key=f"ln_valor_{fr_id}")

    c3, c4, c5, c6 = st.columns(4)
    c3.number_input("Total de parcelas:", min_value=1, max_value=240, value=1, step=1, disabled=(acao=="editar"), key=f"ln_parcelas_{fr_id}")
    
    c4.number_input("Intervalo de dias:", min_value=1, value=1, step=1, disabled=(acao=="editar"), key=f"ln_intervalo_{fr_id}", on_change=on_change_intervalo, args=(fr_id, v_data_dig))
    
    c5.date_input("Data de vencimento:", value=v_data_venc, format="DD/MM/YYYY", disabled=False, key=f"ln_data_venc_{fr_id}")
    
    # --- ENGENHARIA DA TRAVA VISUAL ---
    data_selecionada = st.session_state.get(f"ln_data_venc_{fr_id}", v_data_venc)
    travar_status = data_selecionada > v_data_dig

    if travar_status:
        st.session_state[f"ln_status_{fr_id}"] = "Pendente"
    elif f"ln_status_{fr_id}" not in st.session_state:
        if acao in ["inserir", "duplicar"]:
            st.session_state[f"ln_status_{fr_id}"] = "Efetivado"
        else:
            st.session_state[f"ln_status_{fr_id}"] = "Efetivado" if v_status == 1 else "Pendente"

    c6.selectbox("Status inicial:", ["Pendente", "Efetivado"], disabled=travar_status, key=f"ln_status_{fr_id}")
    # ----------------------------------
    
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    
    # --- ENGENHARIA DO FOCO E ORDEM VISUAL ---
    c7, c8 = st.columns(2)
    
    # Campo limpo de Dicas
    evento_sel = c7.selectbox("Evento originador (Credor/Devedor):", op_eventos, index=v_evento_idx, key=f"ln_evento_sel_{fr_id}")
    
    if evento_sel == "+ Criar novo evento...":
        c8.selectbox("Vincule a uma classificação:", op_class, key=f"ln_class_sel_{fr_id}")
        st.text_input("Digite o nome do novo evento:", placeholder="Ex: Conta de Luz CPFL...", key=f"ln_novo_evento_{fr_id}")
    else:
        df_ev_query = GerenciadorBanco.executar_query("SELECT id FROM eventos WHERE nome = %s LIMIT 1", (evento_sel,))
        if not df_ev_query.empty:
            id_ev = int(df_ev_query.iloc[0]['id'])
            nome_class = GerenciadorBanco.executar_query("SELECT c.nome FROM eventos e JOIN classificacoes c ON e.id_classificacao = c.id WHERE e.id = %s", (id_ev,)).iloc[0]['nome']
            c8.text_input("Classificação (Automática):", value=nome_class, disabled=True)
            st.session_state[f"ln_class_sel_{fr_id}"] = nome_class
        
    st.text_input("Observações / Justificativas opcionais:", value=v_obs, key=f"ln_obs_{fr_id}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns([4, 3, 3])
    
    # Salvar primeiro na ordem DOM = recebe o TAB antes do Fechar
    with b2:
        lbl_btn = "Atualizar Parcela" if acao == "editar" else "Salvar Lançamento"
        st.button(lbl_btn, type="primary", use_container_width=True, on_click=callback_salvar_lancamento, args=(acao, id_lancamento))
    
    with b3:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()

    # --- TRATAMENTO NATIVO DE MENSAGENS PARA MODAL PERSISTENTE ---
    if st.session_state.get("msg_sucesso_cont"):
        st.toast("Operação realizada com sucesso!", icon="✅")
        st.session_state.msg_sucesso_cont = False
    elif st.session_state.get("msg_sucesso"):
        st.toast("Operação realizada com sucesso!", icon="✅")
        time.sleep(2.0)
        st.session_state.msg_sucesso = False
        st.rerun()
    elif st.session_state.get("msg_erro"):
        st.toast(st.session_state.msg_erro, icon="❌")
        st.session_state.msg_erro = ""

@st.dialog(":material/check_circle: Conciliar lançamento")
def modal_baixa(id_lancamento, evento_nome, valor_original):
    UtilitariosVisuais.exibir_mensagens()
    fr_id = st.session_state.get("form_reset", 0)
    st.session_state["ln_form_reset"] = fr_id
    
    st.info(f"Processando a baixa de: **{evento_nome}**")
    
    c1, c2 = st.columns(2)
    c1.date_input("Data real de efetivação:", value=date.today(), format="DD/MM/YYYY", key=f"bx_data_{fr_id}")
    c2.text_input("Valor original (R$):", value=f"{valor_original:,.2f}", disabled=True)
    
    c3, c4 = st.columns(2)
    c3.number_input("Adicionar Juros/Multa (+):", min_value=0.0, step=0.01, value=0.0, key=f"bx_juros_{fr_id}")
    c4.number_input("Aplicar Desconto (-):", min_value=0.0, step=0.01, value=0.0, key=f"bx_desconto_{fr_id}")
    
    st.text_input("Observações da efetivação:", placeholder="Ex: Pago via PIX pelo app...", key=f"bx_obs_{fr_id}")
    
    b1, b2, b3 = st.columns([4, 3, 3])
    with b2:
        if st.button("Cancelar", type="secondary", use_container_width=True): st.rerun()
    with b3:
        st.button("Confirmar baixa", type="primary", use_container_width=True, on_click=callback_conciliacao, args=(id_lancamento, float(valor_original)))

@st.dialog(":material/delete: Excluir lançamento")
def modal_exclusao(id_lancamento, evento_nome):
    UtilitariosVisuais.exibir_mensagens()
    if not st.session_state.form_cleared:
        st.error(f"Esta ação excluirá permanentemente a parcela referente a **{evento_nome}**. O saldo será recalculado.")
        c1, c2, c3 = st.columns([2, 3, 3])
        with c2:
            if st.button("Cancelar", type="secondary", use_container_width=True): st.rerun()
        with c3:
            # Correção do Padrão Visual: "Confirmar exclusão" -> "Confirmar"
            st.button("Confirmar", type="primary", use_container_width=True, on_click=callback_exclusao, args=(id_lancamento,))

# ==========================================
# CONSTRUÇÃO DA TELA PRINCIPAL
# ==========================================
if 'show_filtros_lanc' not in st.session_state: st.session_state.show_filtros_lanc = False

hoje = date.today()
primeiro_dia = hoje.replace(day=1)
ultimo_dia = hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])

if 'f_ln_dt_ini' not in st.session_state: st.session_state.f_ln_dt_ini = primeiro_dia
if 'f_ln_dt_fim' not in st.session_state: st.session_state.f_ln_dt_fim = ultimo_dia
if 'f_ln_nat' not in st.session_state: st.session_state.f_ln_nat = "Entradas e Saídas"
if 'f_ln_stat' not in st.session_state: st.session_state.f_ln_stat = "Todos os Status"
if 'f_ln_evs' not in st.session_state: st.session_state.f_ln_evs = []

c_titulo, c_filtrar, c_inserir, c_margem = st.columns([5, 1.5, 1.5, 3])
with c_titulo: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>account_balance_wallet</span> Fluxo de Lançamentos</h3>", unsafe_allow_html=True)
with c_filtrar:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True):
        st.session_state.show_filtros_lanc = not st.session_state.show_filtros_lanc; st.rerun()
with c_inserir:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True): 
        UtilitariosVisuais.preparar_modal(); modal_formulario("inserir")

if st.session_state.show_filtros_lanc:
    with st.container(border=True):
        f1, f2, f3, f4, f5 = st.columns([1.5, 1.5, 2, 2, 3])
        v_dt_ini = f1.date_input("Data inicial:", value=st.session_state.f_ln_dt_ini, format="DD/MM/YYYY")
        v_dt_fim = f2.date_input("Data final:", value=st.session_state.f_ln_dt_fim, format="DD/MM/YYYY")
        
        op_nat = ["Entradas e Saídas", "Apenas Receitas (+)", "Apenas Despesas (-)"]
        idx_nat = op_nat.index(st.session_state.f_ln_nat) if st.session_state.f_ln_nat in op_nat else 0
        v_nat = f3.selectbox("Natureza:", op_nat, index=idx_nat)
        
        op_stat = ["Todos os Status", "Apenas Pendentes", "Apenas Efetivados"]
        idx_stat = op_stat.index(st.session_state.f_ln_stat) if st.session_state.f_ln_stat in op_stat else 0
        v_stat = f4.selectbox("Status:", op_stat, index=idx_stat)
        
        df_ev_list, _ = obter_auxiliares()
        lista_eventos = df_ev_list['nome'].tolist() if not df_ev_list.empty else []
        v_evs = f5.multiselect("Eventos específicos:", options=lista_eventos, default=st.session_state.f_ln_evs, placeholder="Todos os eventos")
        
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        b_space, b_check, b_btn = st.columns([6, 2.5, 1.5], vertical_alignment="center")
        
        with b_check:
            auto_refresh = st.checkbox("Refresh automático", value=st.session_state.get('f_ln_auto', False), key='f_ln_auto')
        with b_btn:
            if auto_refresh:
                st.session_state.f_ln_dt_ini = v_dt_ini
                st.session_state.f_ln_dt_fim = v_dt_fim
                st.session_state.f_ln_nat = v_nat
                st.session_state.f_ln_stat = v_stat
                st.session_state.f_ln_evs = v_evs
                st.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True, disabled=True)
            else:
                if st.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True):
                    st.session_state.f_ln_dt_ini = v_dt_ini
                    st.session_state.f_ln_dt_fim = v_dt_fim
                    st.session_state.f_ln_nat = v_nat
                    st.session_state.f_ln_stat = v_stat
                    st.session_state.f_ln_evs = v_evs
                    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

df = carregar_dados(st.session_state.f_ln_dt_ini, st.session_state.f_ln_dt_fim)

if not df.empty:
    if st.session_state.f_ln_nat == "Apenas Receitas (+)": df = df[df['tipo'] == 'Receita']
    elif st.session_state.f_ln_nat == "Apenas Despesas (-)": df = df[df['tipo'] == 'Despesa']
        
    if st.session_state.f_ln_stat == "Apenas Pendentes": df = df[df['status'] == 'Pendente']
    elif st.session_state.f_ln_stat == "Apenas Efetivados": df = df[df['status'] == 'Efetivado']
        
    if st.session_state.f_ln_evs: df = df[df['nome_base_evento'].isin(st.session_state.f_ln_evs)]

if not df.empty:
    df['entrada'] = df.apply(lambda row: row['valor_final'] if row['tipo'] == 'Receita' else 0.0, axis=1)
    df['saida'] = df.apply(lambda row: row['valor_final'] if row['tipo'] == 'Despesa' else 0.0, axis=1)
    df['saldo'] = df['entrada'].cumsum() - df['saida'].cumsum()

html_cabecalho = '''
<div class="cabecalho-grid">
    <div style="display: flex;">
        <div style="flex: 0.9;">Emissão</div>
        <div style="flex: 0.9;">Venc.</div>
        <div style="flex: 1.1; text-align: center;">Status</div>
        <div style="flex: 2.5;">Evento financeiro</div>
        <div style="flex: 1.2; text-align: center;">Categoria</div>
        <div style="flex: 1.0; text-align: right;">Entrada</div>
        <div style="flex: 1.0; text-align: right;">Saída</div>
        <div style="flex: 1.0; text-align: right;">Saldo</div>
        <div style="flex: 2.6; text-align: center;">Ações</div>
    </div>
</div>
'''
st.markdown(html_cabecalho, unsafe_allow_html=True)

if df.empty:
    st.info("Nenhum lançamento corresponde aos parâmetros de busca.")
else:
    with st.container():
        st.markdown("<div class='btn-acao-grid'>", unsafe_allow_html=True)
        for _, row in df.iterrows():
            id_lanc = row['id']
            data_dig_str = row['data_digitacao'].strftime('%d/%m/%Y') if pd.notnull(row['data_digitacao']) else "--/--/----"
            data_ven_str = row['data_vencimento'].strftime('%d/%m/%Y')
            
            badge_status = "badge-efetivado" if row['status'] == 'Efetivado' else "badge-pendente"
            badge_cat = "badge-receita" if row['tipo'] == 'Receita' else "badge-despesa"
            
            val_ent = f"<span style='color:#0f8661; font-weight:600;'>{formatar_moeda(row['entrada'])}</span>" if row['entrada'] > 0 else ""
            val_sai = f"<span style='color:#b3391b; font-weight:600;'>{formatar_moeda(row['saida'])}</span>" if row['saida'] > 0 else ""
            
            c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12 = st.columns([0.9, 0.9, 1.1, 2.5, 1.2, 1.0, 1.0, 1.0, 0.65, 0.65, 0.65, 0.65], vertical_alignment="center")
            
            c1.markdown(f"<span style='font-size: 13px; color: #495057;'>{data_dig_str}</span>", unsafe_allow_html=True)
            c2.markdown(f"<span style='font-size: 13px; color: #495057; font-weight: 600;'>{data_ven_str}</span>", unsafe_allow_html=True)
            c3.markdown(f"<div style='text-align: center;'><span class='{badge_status}'>{row['status']}</span></div>", unsafe_allow_html=True)
            
            icone_file = row['icone']
            html_icone = ""
            if pd.notna(icone_file) and icone_file != "Sem ícone":
                b64_img = UtilitariosVisuais.obter_imagem_base64(os.path.join("Imagens", "Icones", icone_file))
                if b64_img:
                    html_icone = f"<img src='data:image/png;base64,{b64_img}' style='width: 52px; height: 52px; margin-right: 15px; vertical-align: middle; mix-blend-mode: multiply;' />"

            bloco_evento = f"""
            <div style='display: flex; align-items: center;'>
                {html_icone}
                <div>
                    <span style='font-weight: 700; color: #1a2a40; font-size: 15px;'>{row['evento_exibicao']}</span><br>
                    <span style='font-size: 12px; color: #6c757d; font-weight: 500;'>{row['classificacao']}</span>
                </div>
            </div>
            """
            c4.markdown(bloco_evento, unsafe_allow_html=True)
            
            c5.markdown(f"<div style='text-align: center;'><span class='{badge_cat}'>{row['categoria']}</span></div>", unsafe_allow_html=True)
            
            c6.markdown(f"<div style='text-align: right; font-size: 13px;'>{val_ent}</div>", unsafe_allow_html=True)
            c7.markdown(f"<div style='text-align: right; font-size: 13px;'>{val_sai}</div>", unsafe_allow_html=True)
            c8.markdown(f"<div style='text-align: right; font-size: 13px; font-weight: 700; color: #1a2a40;'>{formatar_moeda(row['saldo'])}</div>", unsafe_allow_html=True)
            
            if row['status'] == 'Pendente':
                if c9.button(" ", icon=":material/done_all:", key=f"bx_{id_lanc}", help="Conciliar e Efetivar", use_container_width=True):
                    UtilitariosVisuais.preparar_modal(); modal_baixa(int(id_lanc), row['evento_exibicao'], row['valor_previsto'])
            else:
                c9.button(" ", icon=":material/done_all:", key=f"bx_dis_{id_lanc}", help="Lançamento já efetivado", disabled=True, use_container_width=True)
                
            if c10.button(" ", icon=":material/edit:", key=f"ed_{id_lanc}", help="Editar Parcela", use_container_width=True):
                UtilitariosVisuais.preparar_modal(); modal_formulario("editar", id_lancamento=id_lanc, dados_pre=row)
                
            if c11.button(" ", icon=":material/content_copy:", key=f"dp_{id_lanc}", help="Duplicar Lançamento", use_container_width=True):
                UtilitariosVisuais.preparar_modal(); modal_formulario("duplicar", dados_pre=row)
                
            if c12.button(" ", icon=":material/delete:", key=f"del_{id_lanc}", help="Excluir Parcela", use_container_width=True):
                UtilitariosVisuais.preparar_modal(); modal_exclusao(int(id_lanc), row['evento_exibicao'])
                
            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)