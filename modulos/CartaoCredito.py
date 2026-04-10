import streamlit as st
import pandas as pd
import time
from datetime import datetime, date
from fpdf import FPDF
import io
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

# ==========================================
# 1. CONFIGURAÇÕES E ESTADOS DE SESSÃO
# ==========================================
UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

if 'modal_cc_ativa' not in st.session_state: st.session_state.modal_cc_ativa = None
if 'modal_cc_id' not in st.session_state: st.session_state.modal_cc_id = None
if 'modal_cc_dados' not in st.session_state: st.session_state.modal_cc_dados = None
if 'modal_fat_id' not in st.session_state: st.session_state.modal_fat_id = None
if 'modal_fat_nome' not in st.session_state: st.session_state.modal_fat_nome = None
if 'modal_del_id' not in st.session_state: st.session_state.modal_del_id = None
if 'modal_del_ev' not in st.session_state: st.session_state.modal_del_ev = None
if 'show_filtros_cc' not in st.session_state: st.session_state.show_filtros_cc = False
if 'f_cc_busca' not in st.session_state: st.session_state.f_cc_busca = ""

# ==========================================
# 2. MOTOR DE PDF (FPDF2) ATUALIZADO
# ==========================================
class PDF_Fatura(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Sistema financeiro - Fatura detalhada', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def gerar_pdf_bytes(df_detalhes, nome_cartao, vencimento, total):
    pdf = PDF_Fatura()
    pdf.add_page()
    
    # Cabeçalho do Cliente
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Cartão: {nome_cartao}", 0, 1)
    pdf.cell(0, 10, f"Vencimento: {vencimento.strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(5)

    # Tabela de Itens (Nova ordem: Data, Fornecedor, Evento, Categoria, Valor)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, 10, "Data compra", 1, 0, 'C', True)
    pdf.cell(45, 10, "Fornecedor", 1, 0, 'L', True)
    pdf.cell(55, 10, "Evento", 1, 0, 'L', True)
    pdf.cell(35, 10, "Categoria", 1, 0, 'C', True)
    pdf.cell(30, 10, "Valor (R$)", 1, 1, 'R', True)

    pdf.set_font('Arial', '', 8)
    for _, row in df_detalhes.iterrows():
        dt = row['data_compra'].strftime('%d/%m/%Y') if pd.notna(row['data_compra']) else "-"
        forn = str(row['fornecedor'])[:25] if pd.notna(row['fornecedor']) else "-"
        
        pdf.cell(25, 10, dt, 1, 0, 'C')
        pdf.cell(45, 10, forn, 1, 0, 'L')
        pdf.cell(55, 10, str(row['descricao'])[:35], 1, 0, 'L')
        pdf.cell(35, 10, str(row['categoria'])[:20], 1, 0, 'C')
        pdf.cell(30, 10, f"{row['valor_previsto']:,.2f}", 1, 1, 'R')

    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(150, 10, "Total da fatura:", 0, 0, 'R')
    pdf.cell(40, 10, f"R$ {total:,.2f}", 0, 1, 'R')
    
    return pdf.output()

# ==========================================
# 3. FUNÇÕES DE APOIO E CONSULTAS
# ==========================================
def carregar_dados():
    return GerenciadorBanco.executar_query("SELECT id, nome, limite_total, dia_fechamento, dia_vencimento FROM cartoes_credito ORDER BY nome ASC")

def carregar_resumo_faturas(id_cartao):
    query = """
    SELECT data_vencimento, SUM(valor_previsto) as total, status
    FROM lancamentos 
    WHERE id_cartao_credito = %s
    GROUP BY data_vencimento, status
    ORDER BY data_vencimento DESC
    """
    return GerenciadorBanco.executar_query(query, (id_cartao,))

def carregar_detalhes_fatura(id_cc, vencimento):
    query = """
    SELECT l.data_compra, e.nome || ' (' || l.parcela_atual || '/' || l.total_parcelas || ')' as descricao, 
           l.valor_previsto, c.nome as categoria, f.nome as fornecedor
    FROM lancamentos l
    INNER JOIN eventos e ON l.id_evento = e.id
    INNER JOIN classificacoes c ON l.id_classificacao = c.id
    LEFT JOIN fornecedores f ON l.id_fornecedor = f.id
    WHERE l.id_cartao_credito = %s AND l.data_vencimento = %s
    ORDER BY l.data_compra ASC, l.id ASC
    """
    return GerenciadorBanco.executar_query(query, (id_cc, vencimento))

def obter_limite_utilizado(id_cartao):
    query = "SELECT SUM(valor_previsto) as total FROM lancamentos WHERE id_cartao_credito = %s AND status = 'Pendente'"
    df = GerenciadorBanco.executar_query(query, (id_cartao,))
    total = df.iloc[0]['total']
    return float(total) if pd.notna(total) else 0.0

def executar_pagamento_fatura(id_cartao, vencimento):
    query = """
    UPDATE lancamentos 
    SET status = 'Efetivado', valor_realizado = valor_previsto, data_efetivacao = CURRENT_DATE
    WHERE id_cartao_credito = %s AND data_vencimento = %s AND status = 'Pendente'
    """
    GerenciadorBanco.executar_query(query, (id_cartao, vencimento), is_select=False)
    st.cache_data.clear()
    st.toast(f"Fatura com vencimento em {vencimento.strftime('%d/%m/%Y')} paga com sucesso!", icon="✅")

def executar_reabertura_fatura(id_cartao, vencimento):
    query = """
    UPDATE lancamentos 
    SET status = 'Pendente', valor_realizado = NULL, data_efetivacao = NULL
    WHERE id_cartao_credito = %s AND data_vencimento = %s
    """
    GerenciadorBanco.executar_query(query, (id_cartao, vencimento), is_select=False)
    st.cache_data.clear()
    st.toast(f"Fatura {vencimento.strftime('%d/%m/%Y')} reaberta para ajustes.", icon="✅")

# ==========================================
# 4. MODAIS DE INTERAÇÃO 
# ==========================================
@st.dialog(":material/credit_card: Cartão de crédito", width="small")
def modal_formulario(acao="inserir", id_cc=None, dados_pre=None):
    fr_id = st.session_state.get("form_reset", 0)
    
    v_nome = dados_pre['nome'] if dados_pre is not None else ""
    v_limite = float(dados_pre['limite_total']) if dados_pre is not None else 0.0
    v_fechamento = int(dados_pre['dia_fechamento']) if dados_pre is not None else 1
    v_vencimento = int(dados_pre['dia_vencimento']) if dados_pre is not None else 10

    st.text_input("Nome do cartão (Ex: Nubank, Itaú):", value=v_nome, key=f"cc_nome_{fr_id}")
    st.number_input("Limite total (R$):", value=v_limite, min_value=0.0, step=100.0, format="%.2f", key=f"cc_limite_{fr_id}")
    
    c1, c2 = st.columns(2)
    c1.number_input("Dia de fechamento:", value=v_fechamento, min_value=1, max_value=31, step=1, key=f"cc_f_{fr_id}")
    c2.number_input("Dia de vencimento:", value=v_vencimento, min_value=1, max_value=31, step=1, key=f"cc_v_{fr_id}")

    st.markdown("<br>", unsafe_allow_html=True)
    b_sal, b_fec = st.columns(2)
    with b_sal:
        if st.button("Salvar", type="primary", use_container_width=True):
            nome = st.session_state.get(f"cc_nome_{fr_id}", "").strip()
            limite = st.session_state.get(f"cc_limite_{fr_id}", 0.0)
            dia_fechamento = st.session_state.get(f"cc_f_{fr_id}", 1)
            dia_vencimento = st.session_state.get(f"cc_v_{fr_id}", 1)
            
            if not nome or limite <= 0:
                st.session_state.msg_erro = "O nome é obrigatório e o limite deve ser maior que zero."
                st.rerun()
            else:
                if acao == "editar" and id_cc:
                    GerenciadorBanco.executar_query("UPDATE cartoes_credito SET nome = %s, limite_total = %s, dia_fechamento = %s, dia_vencimento = %s WHERE id = %s", (nome, limite, dia_fechamento, dia_vencimento, id_cc), is_select=False)
                else:
                    GerenciadorBanco.executar_query("INSERT INTO cartoes_credito (nome, limite_total, dia_fechamento, dia_vencimento) VALUES (%s, %s, %s, %s)", (nome, limite, dia_fechamento, dia_vencimento), is_select=False)

                st.cache_data.clear()
                st.session_state.msg_sucesso = True
                st.session_state.modal_cc_ativa = None
                st.session_state.form_reset += 1
                st.rerun() 
                
    with b_fec:
        if st.button("Fechar", type="secondary", use_container_width=True):
            st.session_state.modal_cc_ativa = None
            st.rerun()

    if st.session_state.get("msg_sucesso"):
        st.toast("Operação realizada com sucesso!", icon="✅"); time.sleep(1.0)
        st.session_state.msg_sucesso = False; st.rerun()
    elif st.session_state.get("msg_erro"):
        st.toast(st.session_state.msg_erro, icon="❌"); st.session_state.msg_erro = ""

@st.dialog(":material/delete: Excluir cartão", width="small")
def modal_exclusao(id_cc, nome_cc):
    vinc = GerenciadorBanco.executar_query("SELECT id FROM lancamentos WHERE id_cartao_credito = %s LIMIT 1", (id_cc,))
    
    if not vinc.empty:
        st.warning(f"O cartão **{nome_cc}** não pode ser excluído porque possui lançamentos financeiros vinculados a ele.")
        if st.button("Fechar", type="secondary", use_container_width=True): 
            st.session_state.modal_del_id = None
            st.rerun()
    else:
        st.error(f"Deseja realmente excluir o cartão: **{nome_cc}**?")
        b_conf, b_canc = st.columns(2)
        with b_conf:
            if st.button("Confirmar", type="primary", use_container_width=True):
                GerenciadorBanco.executar_query("DELETE FROM cartoes_credito WHERE id = %s", (id_cc,), is_select=False)
                st.cache_data.clear()
                st.session_state.msg_sucesso = True
                st.session_state.modal_del_id = None
                st.session_state.form_reset += 1
                st.rerun()
        with b_canc:
            if st.button("Fechar", type="secondary", use_container_width=True): 
                st.session_state.modal_del_id = None
                st.rerun()

@st.dialog(":material/receipt_long: Gestão de faturas", width="large")
def modal_faturas(id_cartao, nome_cartao):
    st.markdown(f"#### Faturas do cartão: {nome_cartao}")
    df_f = carregar_resumo_faturas(id_cartao)
    
    if df_f.empty:
        st.info("Nenhuma despesa lançada para este cartão até o momento.")
    else:
        for _, f in df_f.iterrows():
            venc = f['data_vencimento']
            status_f = f['status']
            total_f = f['total']
            
            icone_header = "⏳" if status_f == 'Pendente' else "✅"
            
            with st.expander(f"{icone_header} Vencimento em {venc.strftime('%d/%m/%Y')} — R$ {total_f:,.2f}"):
                
                # 1. Busca os detalhes da fatura
                df_det = carregar_detalhes_fatura(id_cartao, venc)
                
                # 2. Formatação dos Nomes de Colunas para exibição na Tela
                if not df_det.empty:
                    df_tela = df_det.copy()
                    df_tela['data_compra'] = pd.to_datetime(df_tela['data_compra']).dt.strftime('%d/%m/%Y').fillna("-")
                    df_tela['valor_previsto'] = df_tela['valor_previsto'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    df_tela['fornecedor'] = df_tela['fornecedor'].fillna("-")
                    
                    df_tela = df_tela.rename(columns={
                        'data_compra': 'Data da compra',
                        'descricao': 'Evento',
                        'fornecedor': 'Fornecedor',
                        'categoria': 'Categoria',
                        'valor_previsto': 'Valor da parcela'
                    })
                    
                    # Organiza a ordem das colunas: Data -> Fornecedor -> Evento
                    df_tela = df_tela[['Data da compra', 'Fornecedor', 'Evento', 'Categoria', 'Valor da parcela']]
                    
                    # Exibe no Streamlit
                    st.dataframe(df_tela, hide_index=True, use_container_width=True)
                
                # 3. Gerador de PDF
                pdf_output = gerar_pdf_bytes(df_det, nome_cartao, venc, total_f)
                st.download_button(label="📥 Baixar fatura detalhada (PDF)", data=bytes(pdf_output), file_name=f"Fatura_{nome_cartao}_{venc}.pdf", mime="application/pdf", key=f"pdf_{venc}_{id_cartao}")
                
                # 4. Ações de Pagamento
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                if status_f == 'Pendente':
                    st.warning("Esta fatura ainda está aberta ou aguardando pagamento.")
                    if st.button("Pagar fatura total", type="primary", key=f"pay_{venc}_{id_cartao}"):
                        executar_pagamento_fatura(id_cartao, venc)
                        st.rerun()
                else:
                    st.success("Esta fatura já consta como PAGA. (Lançamentos bloqueados para edição na Agenda Financeira).")
                    if st.button("Reabrir fatura (estornar)", type="secondary", key=f"open_{venc}_{id_cartao}"):
                        executar_reabertura_fatura(id_cartao, venc)
                        st.rerun()
                    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Fechar painel", use_container_width=True):
        st.session_state.modal_fat_id = None
        st.rerun()

# ==========================================
# 5. INTERFACE PRINCIPAL
# ==========================================
c_tit, c_fil, c_ins, c_mar = st.columns([5, 1.5, 1.5, 3])
with c_tit: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>credit_card</span> Cartões de crédito</h3>", unsafe_allow_html=True)
with c_fil:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True):
        st.session_state.show_filtros_cc = not st.session_state.show_filtros_cc; st.rerun()
with c_ins:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True):
        st.session_state.modal_cc_ativa, st.session_state.modal_cc_id, st.session_state.modal_cc_dados = "inserir", None, None; st.rerun()

if st.session_state.show_filtros_cc:
    with st.container(border=True):
        f_col1, f_col2 = st.columns([8.5, 1.5], vertical_alignment="bottom")
        busca = f_col1.text_input("Pesquisar por nome:", value=st.session_state.f_cc_busca)
        if f_col2.button("Pesquisar", type="tertiary", use_container_width=True):
            st.session_state.f_cc_busca = busca; st.rerun()

df = carregar_dados()
if not df.empty and st.session_state.f_cc_busca:
    df = df[df['nome'].str.contains(st.session_state.f_cc_busca, case=False)]

st.markdown('''<div class="cabecalho-grid"><div style="display: flex;"><div style="flex: 2.5;">Nome do Cartão</div><div style="flex: 1.0; text-align: center;">Fech. / Venc.</div><div style="flex: 1.5; text-align: right;">Limite Total</div><div style="flex: 1.5; text-align: right;">Limite Disp.</div><div style="flex: 1.5; text-align: center;">Ações</div></div></div>''', unsafe_allow_html=True)

if not df.empty:
    for _, row in df.iterrows():
        limite_usado = obter_limite_utilizado(row['id'])
        limite_total = float(row['limite_total'])
        limite_disponivel = limite_total - limite_usado
        
        cor_disp = "#0f8661" if limite_disponivel > 0 else "#dc3545"

        c = st.columns([2.5, 1.0, 1.5, 1.5, 0.5, 0.5, 0.5], vertical_alignment="center")
        
        c[0].markdown(f"<span style='font-weight: 700; color: #1a2a40; font-size: 15px;'>💳 {row['nome']}</span>", unsafe_allow_html=True)
        c[1].markdown(f"<div style='text-align: center; color: #495057;'>Dia {row['dia_fechamento']} / {row['dia_vencimento']}</div>", unsafe_allow_html=True)
        c[2].markdown(f"<div style='text-align: right; color: #495057;'>R$ {limite_total:,.2f}</div>", unsafe_allow_html=True)
        c[3].markdown(f"<div style='text-align: right; font-weight: 700; color: {cor_disp};'>R$ {limite_disponivel:,.2f}</div>", unsafe_allow_html=True)
        
        if c[4].button(" ", icon=":material/receipt_long:", key=f"fat_{row['id']}", use_container_width=True, help="Gerenciar Faturas"):
            st.session_state.modal_fat_id, st.session_state.modal_fat_nome = row['id'], row['nome']; st.rerun()
        if c[5].button(" ", icon=":material/edit:", key=f"ed_cc_{row['id']}", use_container_width=True, help="Editar Cartão"):
            st.session_state.modal_cc_ativa, st.session_state.modal_cc_id, st.session_state.modal_cc_dados = "editar", row['id'], row; st.rerun()
        if c[6].button(" ", icon=":material/delete:", key=f"del_cc_{row['id']}", use_container_width=True, help="Excluir Cartão"):
            st.session_state.modal_del_id = row['id']; st.session_state.modal_del_ev = row['nome']; st.rerun()
            
        st.markdown("<hr style='margin: 5px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
else:
    st.info("Nenhum cartão de crédito cadastrado.")

# MOTOR CENTRAL DE RENDERIZAÇÃO DE MODAIS
if st.session_state.modal_cc_ativa:
    modal_formulario(st.session_state.modal_cc_ativa, st.session_state.modal_cc_id, st.session_state.modal_cc_dados)
elif st.session_state.get("modal_del_id") is not None:
    modal_exclusao(st.session_state.modal_del_id, st.session_state.modal_del_ev)
elif st.session_state.get("modal_fat_id") is not None:
    modal_faturas(st.session_state.modal_fat_id, st.session_state.modal_fat_nome)