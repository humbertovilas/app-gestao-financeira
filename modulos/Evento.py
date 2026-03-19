import streamlit as st
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais
import pandas as pd
import time

UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

# ==========================================
# ACESSO A DADOS (CRUD)
# ==========================================
def carregar_dados(pesquisa=""):
    query = """
    SELECT e.id, e.nome, e.id_classificacao, c.nome as classificacao, cat.nome as categoria, cat.tipo 
    FROM eventos e
    INNER JOIN classificacoes c ON e.id_classificacao = c.id
    INNER JOIN categorias cat ON c.id_categoria = cat.id
    """
    params = []
    if pesquisa:
        query += " WHERE e.nome ILIKE %s"
        params.append(f"%{pesquisa}%")
    query += " ORDER BY e.nome ASC"
    return GerenciadorBanco.executar_query(query, tuple(params))

def carregar_classificacoes():
    query = """
    SELECT c.id, c.nome, cat.tipo 
    FROM classificacoes c
    INNER JOIN categorias cat ON c.id_categoria = cat.id
    ORDER BY c.nome ASC
    """
    return GerenciadorBanco.executar_query(query)

def obter_listas_filtro():
    df_clas = GerenciadorBanco.executar_query("SELECT DISTINCT nome FROM classificacoes ORDER BY nome")
    df_cat = GerenciadorBanco.executar_query("SELECT DISTINCT nome FROM categorias ORDER BY nome")
    
    lista_clas = df_clas['nome'].tolist() if not df_clas.empty else []
    lista_cat = df_cat['nome'].tolist() if not df_cat.empty else []
    return lista_clas, lista_cat

def callback_inclusao():
    nome = st.session_state.get(f"inc_nome_ev_{st.session_state.form_reset}", "")
    classificacao_str = st.session_state.get(f"inc_clas_ev_{st.session_state.form_reset}", "")
    
    if nome.strip() and classificacao_str:
        id_classificacao = int(classificacao_str.split(" - ")[0])
        GerenciadorBanco.executar_query(
            "INSERT INTO eventos (nome, id_classificacao) VALUES (%s, %s)", 
            (nome, id_classificacao), is_select=False
        )
        st.session_state.msg_sucesso_inc = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1
    else:
        st.session_state.msg_erro = "Nome do evento e classificação são obrigatórios."

def callback_alteracao(id_evento):
    nome = st.session_state.get(f"alt_nome_ev_{st.session_state.form_reset}", "")
    classificacao_str = st.session_state.get(f"alt_clas_ev_{st.session_state.form_reset}", "")
    
    if nome.strip() and classificacao_str:
        id_classificacao = int(classificacao_str.split(" - ")[0])
        GerenciadorBanco.executar_query(
            "UPDATE eventos SET nome = %s, id_classificacao = %s WHERE id = %s", 
            (nome, id_classificacao, id_evento), is_select=False
        )
        st.session_state.msg_sucesso = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1
    else:
        st.session_state.msg_erro = "Nome do evento e classificação são obrigatórios."

def callback_exclusao(id_evento):
    GerenciadorBanco.executar_query("DELETE FROM eventos WHERE id = %s", (int(id_evento),), is_select=False)
    st.session_state.msg_sucesso = True
    st.session_state.form_cleared = True
    st.session_state.form_reset += 1

# ==========================================
# MODAIS DE INTERAÇÃO
# ==========================================
@st.dialog(":material/add_circle: Novo evento")
def modal_inclusao(nome_base="", id_classificacao_base=None, nome_classificacao_base="", tipo_base=""):
    df_classificacoes = carregar_classificacoes()
    
    opcoes_classificacoes = []
    idx_selecionado = 0
    if not df_classificacoes.empty:
        opcoes_classificacoes = [f"{row['id']} - {row['nome']} ({row['tipo']})" for _, row in df_classificacoes.iterrows()]
        if id_classificacao_base:
            str_busca = f"{id_classificacao_base} - {nome_classificacao_base} ({tipo_base})"
            idx_atual = opcoes_classificacoes.index(str_busca) if str_busca in opcoes_classificacoes else 0
            idx_selecionado = 0 if st.session_state.form_cleared else idx_atual
            
    if nome_base and not st.session_state.form_cleared:
        st.info("Modo de Replicação: Altere o nome para salvar como um novo evento.")
        
    val_nome = "" if st.session_state.form_cleared else nome_base
    
    st.text_input("Nome do evento:", value=val_nome, key=f"inc_nome_ev_{st.session_state.form_reset}")
    if opcoes_classificacoes:
        st.selectbox("Classificação vinculada:", opcoes_classificacoes, index=idx_selecionado, key=f"inc_clas_ev_{st.session_state.form_reset}")
    else:
        st.warning("Cadastre ao menos uma classificação antes de criar um evento.")
        
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_inclusao, disabled=len(opcoes_classificacoes)==0)

    if st.session_state.get("msg_sucesso_inc"):
        st.toast("Operação realizada com sucesso!", icon="✅")
        st.session_state.msg_sucesso_inc = False
        st.session_state.form_cleared = False
    elif st.session_state.get("msg_erro"):
        st.toast(st.session_state.msg_erro, icon="❌")
        st.session_state.msg_erro = ""

@st.dialog(":material/edit: Editar evento")
def modal_alteracao(id_evento, nome_atual, id_classificacao_atual, nome_classificacao_atual, tipo_atual):
    UtilitariosVisuais.exibir_mensagens()
    df_classificacoes = carregar_classificacoes()
    
    opcoes_classificacoes = [f"{row['id']} - {row['nome']} ({row['tipo']})" for _, row in df_classificacoes.iterrows()]
    
    str_busca = f"{id_classificacao_atual} - {nome_classificacao_atual} ({tipo_atual})"
    idx_atual = opcoes_classificacoes.index(str_busca) if str_busca in opcoes_classificacoes else 0
    
    val_nome = "" if st.session_state.form_cleared else nome_atual
    idx_selecionado = 0 if st.session_state.form_cleared else idx_atual
    
    st.text_input("Nome do evento:", value=val_nome, key=f"alt_nome_ev_{st.session_state.form_reset}")
    st.selectbox("Classificação vinculada:", opcoes_classificacoes, index=idx_selecionado, key=f"alt_clas_ev_{st.session_state.form_reset}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_alteracao, args=(id_evento,))

@st.dialog(":material/delete: Excluir evento")
def modal_exclusao(id_evento, nome_atual):
    UtilitariosVisuais.exibir_mensagens()
    
    if not st.session_state.form_cleared:
        html_confirmacao = f"""
        <div style="border-left: 5px solid #e76f51; background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #e9ecef;">
            <div style="color: #1a2a40; font-size: 17px; line-height: 1.6;">
                Tem a certeza que deseja excluir o evento <b>{nome_atual}</b>?<br>
                <span style="color: #e76f51;"><i>Esta ação é irreversível.</i></span>
            </div>
        </div>
        """
        st.markdown(html_confirmacao, unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
        with c3:
            st.button("Confirmar", type="primary", use_container_width=True, on_click=callback_exclusao, args=(id_evento,))
    else:
        c1, c2, c3 = st.columns(3)
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
if 'f_ev_pesq' not in st.session_state: st.session_state.f_ev_pesq = ""
if 'f_ev_clas' not in st.session_state or isinstance(st.session_state.f_ev_clas, str): st.session_state.f_ev_clas = []
if 'f_ev_cat' not in st.session_state or isinstance(st.session_state.f_ev_cat, str): st.session_state.f_ev_cat = []
if 'show_f_ev' not in st.session_state: st.session_state.show_f_ev = False

c_titulo, c_filtrar, c_inserir, c_margem = st.columns([5, 1.5, 1.5, 3])
with c_titulo: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>sell</span> Cadastro de Eventos</h3>", unsafe_allow_html=True)
with c_filtrar:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True):
        st.session_state.show_f_ev = not st.session_state.show_f_ev; st.rerun()
with c_inserir:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True): 
        UtilitariosVisuais.preparar_modal()
        modal_inclusao()

if st.session_state.show_f_ev:
    with st.container(border=True):
        lista_clas, lista_cat = obter_listas_filtro()
        
        f1, f2, f3, f4 = st.columns([2.5, 2, 2, 1.5], vertical_alignment="bottom")
        v_pesq = f1.text_input("Pesquisar nome do evento:", value=st.session_state.f_ev_pesq)
        v_clas = f2.multiselect("Classificação vinculada:", options=lista_clas, default=st.session_state.f_ev_clas, placeholder="Todas as classificações")
        v_cat = f3.multiselect("Categoria:", options=lista_cat, default=st.session_state.f_ev_cat, placeholder="Todas as categorias")
        
        with f4:
            auto_refresh = st.checkbox("Refresh automático", value=st.session_state.get('f_ev_auto', False), key='f_ev_auto')
            if auto_refresh:
                st.session_state.f_ev_pesq = v_pesq
                st.session_state.f_ev_clas = v_clas
                st.session_state.f_ev_cat = v_cat
                st.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True, disabled=True)
            else:
                if st.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True):
                    st.session_state.f_ev_pesq = v_pesq
                    st.session_state.f_ev_clas = v_clas
                    st.session_state.f_ev_cat = v_cat
                    st.rerun()
            
st.markdown("<br>", unsafe_allow_html=True)

df = carregar_dados(st.session_state.f_ev_pesq)

if not df.empty:
    if st.session_state.f_ev_clas:
        df = df[df['classificacao'].isin(st.session_state.f_ev_clas)]
    if st.session_state.f_ev_cat:
        df = df[df['categoria'].isin(st.session_state.f_ev_cat)]

html_cabecalho = '''
<div class="cabecalho-grid">
    <div style="display: flex;">
        <div style="flex: 3.5;">Nome do evento</div>
        <div style="flex: 2.5;">Classificação vinculada</div>
        <div style="flex: 2; text-align: center;">Categoria</div>
        <div style="flex: 2.5; text-align: center;">Ações</div>
    </div>
</div>
'''
st.markdown(html_cabecalho, unsafe_allow_html=True)

if df.empty:
    st.info("Nenhum evento encontrado para os filtros selecionados.")
else:
    with st.container():
        st.markdown("<div class='btn-acao-grid'>", unsafe_allow_html=True)
        for _, row in df.iterrows():
            id_ev, nome, id_classificacao, classificacao, categoria, tipo = row['id'], row['nome'], row['id_classificacao'], row['classificacao'], row['categoria'], row['tipo']
            
            c1, c2, c3, c4, c5, c6 = st.columns([3.5, 2.5, 2, 0.75, 0.75, 0.75], vertical_alignment="center")
            c1.markdown(f"<span style='font-weight: 600; color: #1a2a40; font-size: 15px; padding-left: 10px;'>{nome}</span>", unsafe_allow_html=True)
            c2.markdown(f"<span style='color: #495057; font-size: 14px;'>{classificacao}</span>", unsafe_allow_html=True)
            
            badge = "badge-receita" if tipo == "Receita" else "badge-despesa"
            c3.markdown(f"<div style='text-align: center;'><span class='{badge}'>{categoria}</span></div>", unsafe_allow_html=True)
            
            if c4.button(" ", icon=":material/content_copy:", key=f"re_{id_ev}", help="Replicar", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_inclusao(nome, int(id_classificacao), classificacao, tipo)
            if c5.button(" ", icon=":material/edit:", key=f"ee_{id_ev}", help="Editar", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_alteracao(int(id_ev), nome, int(id_classificacao), classificacao, tipo)
            if c6.button(" ", icon=":material/delete:", key=f"xe_{id_ev}", help="Excluir", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_exclusao(int(id_ev), nome)
            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)