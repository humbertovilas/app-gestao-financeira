import streamlit as st
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

# ==========================================
# REGRAS DE NEGÓCIO E CONSULTA
# ==========================================
def carregar_dados(pesquisa="", categoria_filtro="Todas as Categorias"):
    query = "SELECT cl.id, cl.nome, c.nome as cat_nome, cl.id_categoria FROM classificacoes cl JOIN categorias c ON cl.id_categoria = c.id WHERE 1=1"
    params = []
    if pesquisa:
        query += " AND cl.nome ILIKE %s"
        params.append(f"%{pesquisa}%")
    if categoria_filtro != "Todas as Categorias":
        query += " AND c.nome = %s"
        params.append(categoria_filtro)
    query += " ORDER BY cl.id DESC"
    return GerenciadorBanco.executar_query(query, tuple(params))

# ==========================================
# CALLBACKS (AÇÕES DE GRAVAÇÃO)
# ==========================================
def callback_inclusao():
    nome = st.session_state.get(f"inc_nome_cl_{st.session_state.form_reset}", "")
    cat_pai = st.session_state.get(f"inc_cat_cl_{st.session_state.form_reset}")
    if nome.strip() and cat_pai:
        GerenciadorBanco.executar_query("INSERT INTO classificacoes (nome, id_categoria) VALUES (%s, %s)", (nome, int(cat_pai[0])), is_select=False)
        st.session_state.msg_sucesso = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1
    else:
        st.session_state.msg_erro = "O campo de nome é obrigatório."

def callback_alteracao(id_class):
    nome = st.session_state.get(f"alt_nome_cl_{st.session_state.form_reset}", "")
    cat_pai = st.session_state.get(f"alt_cat_cl_{st.session_state.form_reset}")
    if nome.strip() and cat_pai:
        GerenciadorBanco.executar_query("UPDATE classificacoes SET nome = %s, id_categoria = %s WHERE id = %s", (nome, int(cat_pai[0]), int(id_class)), is_select=False)
        st.session_state.msg_sucesso = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1
    else:
        st.session_state.msg_erro = "O campo de nome é obrigatório."

def callback_exclusao(id_class):
    GerenciadorBanco.executar_query("DELETE FROM classificacoes WHERE id = %s", (int(id_class),), is_select=False)
    st.session_state.msg_sucesso = True
    st.session_state.form_cleared = True
    st.session_state.form_reset += 1

def callback_duplicacao():
    nome = st.session_state.get(f"dup_nome_cl_{st.session_state.form_reset}", "")
    cat_pai = st.session_state.get(f"dup_cat_cl_{st.session_state.form_reset}")
    if nome.strip() and cat_pai:
        GerenciadorBanco.executar_query("INSERT INTO classificacoes (nome, id_categoria) VALUES (%s, %s)", (nome, int(cat_pai[0])), is_select=False)
        st.session_state.msg_sucesso = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1
    else:
        st.session_state.msg_erro = "O campo de nome é obrigatório."

# ==========================================
# MODAIS PADRONIZADAS
# ==========================================
@st.dialog(":material/account_tree: Nova classificação")
def modal_inclusao():
    UtilitariosVisuais.exibir_mensagens()
    cats = GerenciadorBanco.executar_query("SELECT id, nome FROM categorias ORDER BY nome")
    
    if cats.empty: 
        st.warning("Cadastre uma categoria primeiro.")
        if st.button("Fechar", use_container_width=True): st.rerun()
        return
        
    val_nome = "" if st.session_state.form_cleared else ""
    idx_cat = 0 if st.session_state.form_cleared else 0
    
    st.text_input("Nome da classificação:", value=val_nome, placeholder="Ex: Despesas da residência...", key=f"inc_nome_cl_{st.session_state.form_reset}")
    st.selectbox("Vincular à categoria pai:", options=cats.values.tolist(), format_func=lambda x: x[1], index=idx_cat, key=f"inc_cat_cl_{st.session_state.form_reset}")
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2: 
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with c3: 
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_inclusao)

@st.dialog(":material/account_tree: Editar classificação")
def modal_alteracao(id_class, nome_atual, id_cat_atual):
    UtilitariosVisuais.exibir_mensagens()
    cats = GerenciadorBanco.executar_query("SELECT id, nome FROM categorias ORDER BY nome")
    cat_list = cats.values.tolist()
    
    val_nome = "" if st.session_state.form_cleared else nome_atual
    idx_cat = 0 if st.session_state.form_cleared else next((i for i, c in enumerate(cat_list) if c[0] == id_cat_atual), 0)
    
    st.text_input("Nome da classificação:", value=val_nome, key=f"alt_nome_cl_{st.session_state.form_reset}")
    st.selectbox("Vincular à categoria pai:", options=cat_list, format_func=lambda x: x[1], index=idx_cat, key=f"alt_cat_cl_{st.session_state.form_reset}")
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_alteracao, args=(id_class,))

@st.dialog(":material/account_tree: Excluir classificação")
def modal_exclusao(id_class, nome_atual):
    UtilitariosVisuais.exibir_mensagens()
    
    if not st.session_state.form_cleared:
        df_vinculos = GerenciadorBanco.executar_query("SELECT COUNT(id) as total FROM eventos WHERE id_classificacao = %s", (id_class,))
        total_vinculos = int(df_vinculos.iloc[0]['total'])

        if total_vinculos > 0:
            html_bloqueio = f"""
            <div style="border-left: 5px solid #e76f51; background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #e9ecef;">
                <div style="display: flex; align-items: center; gap: 8px; color: #e76f51; font-weight: bold; font-size: 19px; margin-bottom: 12px;">
                    <span class="material-symbols-rounded" style="font-size: 26px;">block</span> Ação Bloqueada
                </div>
                <div style="color: #1a2a40; font-size: 17px; line-height: 1.6;">
                    Não é possível excluir a classificação <b style="color: #e76f51;">{nome_atual}</b>.<br>
                    <strong>Motivo:</strong> Existem <b>{total_vinculos}</b> evento(s) vinculado(s).
                </div>
            </div>
            """
            st.markdown(html_bloqueio, unsafe_allow_html=True)
            c1, c2 = st.columns([6, 4])
            with c2:
                if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
        else:
            html_confirmacao = f"""
            <div style="border-left: 5px solid #457b9d; background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #e9ecef;">
                <div style="color: #1a2a40; font-size: 17px; line-height: 1.6;">
                    Tem a certeza que deseja excluir a classificação <b>{nome_atual}</b>?<br>
                    <span style="color: #e76f51;"><i>Esta ação removerá o registo permanentemente.</i></span>
                </div>
            </div>
            """
            st.markdown(html_confirmacao, unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 3, 3])
            with c2:
                if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
            with c3:
                st.button("Confirmar", type="primary", use_container_width=True, on_click=callback_exclusao, args=(id_class,))
    else:
        c1, c2 = st.columns([7, 3])
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()

@st.dialog(":material/account_tree: Duplicar classificação")
def modal_duplicacao(nome_atual, id_cat_atual):
    UtilitariosVisuais.exibir_mensagens()
    cats = GerenciadorBanco.executar_query("SELECT id, nome FROM categorias ORDER BY nome")
    cat_list = cats.values.tolist()
    
    val_nome = "" if st.session_state.form_cleared else f"{nome_atual} (Cópia)"
    idx_cat = 0 if st.session_state.form_cleared else next((i for i, c in enumerate(cat_list) if c[0] == id_cat_atual), 0)
    
    st.text_input("Novo nome (cópia):", value=val_nome, key=f"dup_nome_cl_{st.session_state.form_reset}")
    st.selectbox("Vincular à categoria pai:", options=cat_list, format_func=lambda x: x[1], index=idx_cat, key=f"dup_cat_cl_{st.session_state.form_reset}")
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_duplicacao)

# ==========================================
# CONSTRUÇÃO DA TELA (VIEW)
# ==========================================
if 'f_cl_pesq' not in st.session_state: st.session_state.f_cl_pesq = ""
if 'f_cl_cat' not in st.session_state: st.session_state.f_cl_cat = "Todas as Categorias"
if 'show_f_cl' not in st.session_state: st.session_state.show_f_cl = False

c_titulo, c_filtrar, c_inserir, c_margem = st.columns([5, 1.5, 1.5, 3])
with c_titulo: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>account_tree</span> Cadastro de Classificações</h3>", unsafe_allow_html=True)
with c_filtrar:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True):
        st.session_state.show_f_cl = not st.session_state.show_f_cl; st.rerun()
with c_inserir:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True): 
        UtilitariosVisuais.preparar_modal()
        modal_inclusao()

if st.session_state.show_f_cl:
    with st.container(border=True):
        cp, cc, cb = st.columns([5, 3, 2])
        v_p = cp.text_input("Pesquisar classificação:", value=st.session_state.f_cl_pesq)
        cats_filtro = GerenciadorBanco.executar_query("SELECT nome FROM categorias ORDER BY nome")
        lista_filtro = ["Todas as Categorias"] + cats_filtro['nome'].tolist()
        idx_f = lista_filtro.index(st.session_state.f_cl_cat) if st.session_state.f_cl_cat in lista_filtro else 0
        v_c = cc.selectbox("Categoria (Grupo):", options=lista_filtro, index=idx_f)
        cb.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if cb.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True):
            st.session_state.f_cl_pesq, st.session_state.f_cl_cat = v_p, v_c; st.rerun()
st.markdown("<br>", unsafe_allow_html=True)

df = carregar_dados(st.session_state.f_cl_pesq, st.session_state.f_cl_cat)
st.markdown('<div class="cabecalho-grid"><div style="display: flex;"><div style="flex: 5;">Nome da classificação</div><div style="flex: 2; text-align: center;">Categoria pai</div><div style="flex: 2; text-align: center;">Ações</div></div></div>', unsafe_allow_html=True)

if df.empty:
    st.info("Nenhuma classificação encontrada na base de dados para este filtro.")
else:
    with st.container():
        st.markdown("<div class='btn-acao-grid'>", unsafe_allow_html=True)
        for _, row in df.iterrows():
            c1, c2, c3, c4, c5 = st.columns([5, 2, 0.66, 0.66, 0.68], vertical_alignment="center")
            c1.markdown(f"<span style='font-weight: 600; color: #1a2a40; font-size: 15px; padding-left: 10px;'>{row['nome']}</span>", unsafe_allow_html=True)
            c2.markdown(f"<div style='text-align: center;'><span class='badge-neutro'>{row['cat_nome']}</span></div>", unsafe_allow_html=True)
            if c3.button(" ", icon=":material/edit:", key=f"ed_cl_{row['id']}", help="Editar", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_alteracao(row['id'], row['nome'], row['id_categoria'])
            if c4.button(" ", icon=":material/content_copy:", key=f"cp_cl_{row['id']}", help="Duplicar", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_duplicacao(row['nome'], row['id_categoria'])
            if c5.button(" ", icon=":material/delete:", key=f"del_cl_{row['id']}", help="Excluir", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_exclusao(row['id'], row['nome'])
            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)