import streamlit as st
import time
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

UtilitariosVisuais.aplicar_configuracoes_ui()

# ==========================================
# REGRAS DE NEGÓCIO E CRUD
# ==========================================
def carregar_dados(pesquisa="", classificacao_filtro="Todas as Classificações"):
    query = "SELECT e.id, e.nome, c.nome as class_nome, e.id_classificacao FROM eventos e JOIN classificacoes c ON e.id_classificacao = c.id WHERE 1=1"
    params = []
    if pesquisa:
        query += " AND e.nome ILIKE %s"
        params.append(f"%{pesquisa}%")
    if classificacao_filtro != "Todas as Classificações":
        query += " AND c.nome = %s"
        params.append(classificacao_filtro)
    query += " ORDER BY e.id DESC"
    return GerenciadorBanco.executar_query(query, tuple(params))

@st.dialog(":material/sell: Novo evento")
def modal_inclusao():
    classes = GerenciadorBanco.executar_query("SELECT id, nome FROM classificacoes ORDER BY nome")
    if classes.empty: st.warning("Cadastre uma classificação primeiro."); return
    
    nome = st.text_input("Nome do evento (Credor/Devedor):", placeholder="Ex: Supermercado, Salário...")
    class_pai = st.selectbox("Vincular à classificação (Grupo Macro):", options=classes.values.tolist(), format_func=lambda x: x[1])
    st.write("")
    
    msg_placeholder = st.empty()
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2: 
        if st.button("Cancelar", type="secondary", use_container_width=True): st.rerun()
    with c3: 
        if st.button("Salvar", type="primary", use_container_width=True):
            if nome.strip() and class_pai:
                with st.spinner("Processando..."):
                    GerenciadorBanco.executar_query("INSERT INTO eventos (nome, id_classificacao) VALUES (%s, %s)", (nome, int(class_pai[0])), is_select=False)
                    time.sleep(0.4)
                msg_placeholder.success(f"Evento '{nome}' registado com sucesso!")
                time.sleep(1); st.rerun()
            else: 
                msg_placeholder.error("O campo de nome é obrigatório.")

@st.dialog(":material/sell: Editar evento")
def modal_alteracao(id_evento, nome_atual, id_class_atual):
    nome = st.text_input("Nome do evento (Credor/Devedor):", value=nome_atual)
    classes = GerenciadorBanco.executar_query("SELECT id, nome FROM classificacoes ORDER BY nome")
    class_list = classes.values.tolist(); idx_class = next((i for i, c in enumerate(class_list) if c[0] == id_class_atual), 0)
    class_pai = st.selectbox("Vincular à classificação (Grupo Macro):", options=class_list, format_func=lambda x: x[1], index=idx_class)
    st.write("")
    
    msg_placeholder = st.empty()
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Cancelar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        if st.button("Salvar", type="primary", use_container_width=True):
            if nome.strip():
                with st.spinner("Processando..."):
                    GerenciadorBanco.executar_query("UPDATE eventos SET nome = %s, id_classificacao = %s WHERE id = %s", (nome, int(class_pai[0]), int(id_evento)), is_select=False)
                    time.sleep(0.4)
                msg_placeholder.success("Evento atualizado com sucesso!")
                time.sleep(1); st.rerun()
            else: 
                msg_placeholder.error("O campo de nome é obrigatório.")

@st.dialog(":material/sell: Excluir evento")
def modal_exclusao(id_evento, nome_atual):
    html_confirmacao = f"""
    <div style="border-left: 5px solid #457b9d; background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #e9ecef;">
        <div style="color: #1a2a40; font-size: 17px; line-height: 1.6;">
            Tem a certeza que deseja excluir o evento <b>{nome_atual}</b>?<br>
            <span style="color: #e76f51;"><i>Esta ação removerá o registo permanentemente.</i></span>
        </div>
    </div>
    """
    st.markdown(html_confirmacao, unsafe_allow_html=True)
    msg_placeholder = st.empty()
    c1, c2, c3 = st.columns([2, 3, 3])
    with c2:
        if st.button("Cancelar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        if st.button("Confirmar exclusão", type="primary", use_container_width=True):
            with st.spinner("Processando..."):
                GerenciadorBanco.executar_query("DELETE FROM eventos WHERE id = %s", (int(id_evento),), is_select=False)
                time.sleep(0.4)
            msg_placeholder.success("Evento excluído com sucesso!")
            time.sleep(1); st.rerun()

@st.dialog(":material/sell: Duplicar evento")
def modal_duplicacao(nome_atual, id_class_atual):
    nome = st.text_input("Novo nome (cópia):", value=f"{nome_atual} (Cópia)")
    classes = GerenciadorBanco.executar_query("SELECT id, nome FROM classificacoes ORDER BY nome")
    class_list = classes.values.tolist(); idx_class = next((i for i, c in enumerate(class_list) if c[0] == id_class_atual), 0)
    class_pai = st.selectbox("Vincular à classificação (Grupo Macro):", options=class_list, format_func=lambda x: x[1], index=idx_class)
    st.write("")
    
    msg_placeholder = st.empty()
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Cancelar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        if st.button("Salvar", type="primary", use_container_width=True):
            if nome.strip():
                with st.spinner("Processando..."):
                    GerenciadorBanco.executar_query("INSERT INTO eventos (nome, id_classificacao) VALUES (%s, %s)", (nome, int(class_pai[0])), is_select=False)
                    time.sleep(0.4)
                msg_placeholder.success("Evento duplicado com sucesso!")
                time.sleep(1); st.rerun()
            else: 
                msg_placeholder.error("O campo de nome é obrigatório.")

# ==========================================
# CONSTRUÇÃO DA TELA (VIEW)
# ==========================================
if 'f_ev_pesq' not in st.session_state: st.session_state.f_ev_pesq = ""
if 'f_ev_class' not in st.session_state: st.session_state.f_ev_class = "Todas as Classificações"
if 'show_f_ev' not in st.session_state: st.session_state.show_f_ev = False

c_titulo, c_filtrar, c_inserir, c_margem = st.columns([5, 1.5, 1.5, 3])
with c_titulo: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>sell</span> Cadastro de Eventos</h3>", unsafe_allow_html=True)
with c_filtrar:
    if st.button("Filtrar", icon=":material/search:", use_container_width=True):
        st.session_state.show_f_ev = not st.session_state.show_f_ev; st.rerun()
with c_inserir:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True): modal_inclusao()

if st.session_state.show_f_ev:
    with st.container(border=True):
        cp, cc, cb = st.columns([5, 3, 2])
        v_p = cp.text_input("Pesquisar nome do evento:", value=st.session_state.f_ev_pesq)
        classes_filtro = GerenciadorBanco.executar_query("SELECT nome FROM classificacoes ORDER BY nome")
        lista_filtro = ["Todas as Classificações"] + classes_filtro['nome'].tolist()
        idx_f = lista_filtro.index(st.session_state.f_ev_class) if st.session_state.f_ev_class in lista_filtro else 0
        v_c = cc.selectbox("Classificação Vinculada:", options=lista_filtro, index=idx_f)
        cb.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if cb.button("Pesquisar", icon=":material/search:", use_container_width=True):
            st.session_state.f_ev_pesq, st.session_state.f_ev_class = v_p, v_c; st.rerun()
st.markdown("<br>", unsafe_allow_html=True)

df = carregar_dados(st.session_state.f_ev_pesq, st.session_state.f_ev_class)
st.markdown('<div class="cabecalho-grid"><div style="display: flex;"><div style="flex: 5;">Nome do evento (Credor/Devedor)</div><div style="flex: 2; text-align: center;">Classificação vinculada</div><div style="flex: 2; text-align: center;">Ações</div></div></div>', unsafe_allow_html=True)

if df.empty:
    st.info("Nenhum evento encontrado na base de dados para este filtro.")
else:
    with st.container():
        st.markdown("<div class='btn-acao-grid'>", unsafe_allow_html=True)
        for _, row in df.iterrows():
            c1, c2, c3, c4, c5 = st.columns([5, 2, 0.66, 0.66, 0.68], vertical_alignment="center")
            c1.markdown(f"<span style='font-weight: 600; color: #1a2a40; font-size: 15px; padding-left: 10px;'>{row['nome']}</span>", unsafe_allow_html=True)
            c2.markdown(f"<div style='text-align: center;'><span class='badge-neutro'>{row['class_nome']}</span></div>", unsafe_allow_html=True)
            if c3.button(" ", icon=":material/edit:", key=f"ed_ev_{row['id']}", help="Editar", use_container_width=True): modal_alteracao(row['id'], row['nome'], row['id_classificacao'])
            if c4.button(" ", icon=":material/content_copy:", key=f"cp_ev_{row['id']}", help="Duplicar", use_container_width=True): modal_duplicacao(row['nome'], row['id_classificacao'])
            if c5.button(" ", icon=":material/delete:", key=f"del_ev_{row['id']}", help="Excluir", use_container_width=True): modal_exclusao(row['id'], row['nome'])
            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)