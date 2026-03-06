import streamlit as st
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

# ==========================================
# REGRAS DE NEGÓCIO E CONSULTA
# ==========================================
def carregar_dados(pesquisa="", natureza="Todas as naturezas"):
    query = "SELECT id, nome as \"Nome da categoria\", tipo as \"Natureza\" FROM categorias WHERE 1=1"
    params = []
    if pesquisa:
        query += " AND nome ILIKE %s"
        params.append(f"%{pesquisa}%")
    if natureza == "Receita": query += " AND tipo = 'Receita'"
    elif natureza == "Despesa": query += " AND tipo = 'Despesa'"
    query += " ORDER BY id DESC"
    return GerenciadorBanco.executar_query(query, tuple(params))

# ==========================================
# CALLBACKS (AÇÕES DE GRAVAÇÃO)
# ==========================================
def callback_inclusao():
    nome = st.session_state.get(f"inc_nome_c_{st.session_state.form_reset}", "")
    tipo = st.session_state.get(f"inc_tipo_c_{st.session_state.form_reset}", "Receita")
    if nome.strip():
        GerenciadorBanco.executar_query("INSERT INTO categorias (nome, tipo) VALUES (%s, %s)", (nome, tipo), is_select=False)
        st.session_state.msg_sucesso = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1
    else:
        st.session_state.msg_erro = "O campo de nome é obrigatório."

def callback_alteracao(id_cat):
    nome = st.session_state.get(f"alt_nome_c_{st.session_state.form_reset}", "")
    tipo = st.session_state.get(f"alt_tipo_c_{st.session_state.form_reset}", "Receita")
    if nome.strip():
        GerenciadorBanco.executar_query("UPDATE categorias SET nome = %s, tipo = %s WHERE id = %s", (nome, tipo, id_cat), is_select=False)
        st.session_state.msg_sucesso = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1
    else:
        st.session_state.msg_erro = "O campo de nome é obrigatório."

def callback_exclusao(id_cat):
    GerenciadorBanco.executar_query("DELETE FROM categorias WHERE id = %s", (int(id_cat),), is_select=False)
    st.session_state.msg_sucesso = True
    st.session_state.form_cleared = True
    st.session_state.form_reset += 1

def callback_duplicacao():
    nome = st.session_state.get(f"dup_nome_c_{st.session_state.form_reset}", "")
    tipo = st.session_state.get(f"dup_tipo_c_{st.session_state.form_reset}", "Receita")
    if nome.strip():
        GerenciadorBanco.executar_query("INSERT INTO categorias (nome, tipo) VALUES (%s, %s)", (nome, tipo), is_select=False)
        st.session_state.msg_sucesso = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1
    else:
        st.session_state.msg_erro = "O campo de nome é obrigatório."

# ==========================================
# MODAIS PADRONIZADAS
# ==========================================
@st.dialog(":material/folder: Nova categoria")
def modal_inclusao():
    UtilitariosVisuais.exibir_mensagens()
    
    val_nome = "" if st.session_state.form_cleared else ""
    val_tipo = 0 if st.session_state.form_cleared else 0
    
    st.text_input("Nome da categoria:", value=val_nome, key=f"inc_nome_c_{st.session_state.form_reset}", placeholder="Ex: Alimentação, Salário...")
    st.selectbox("Natureza:", ["Receita", "Despesa"], index=val_tipo, key=f"inc_tipo_c_{st.session_state.form_reset}")
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_inclusao)

@st.dialog(":material/folder: Editar categoria")
def modal_alteracao(id_cat, nome_atual, tipo_atual):
    UtilitariosVisuais.exibir_mensagens()
    
    val_nome = "" if st.session_state.form_cleared else nome_atual
    val_tipo = 0 if st.session_state.form_cleared else (0 if tipo_atual == "Receita" else 1)
    
    st.text_input("Nome da categoria:", value=val_nome, key=f"alt_nome_c_{st.session_state.form_reset}")
    st.selectbox("Natureza:", ["Receita", "Despesa"], index=val_tipo, key=f"alt_tipo_c_{st.session_state.form_reset}")
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_alteracao, args=(id_cat,))

@st.dialog(":material/folder: Excluir categoria")
def modal_exclusao(id_cat, nome_atual):
    UtilitariosVisuais.exibir_mensagens()
    
    if not st.session_state.form_cleared:
        df_vinculos = GerenciadorBanco.executar_query("SELECT COUNT(id) as total FROM classificacoes WHERE id_categoria = %s", (id_cat,))
        total_vinculos = int(df_vinculos.iloc[0]['total'])

        if total_vinculos > 0:
            html_bloqueio = f"""
            <div style="border-left: 5px solid #e76f51; background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #e9ecef;">
                <div style="display: flex; align-items: center; gap: 8px; color: #e76f51; font-weight: bold; font-size: 19px; margin-bottom: 12px;">
                    <span class="material-symbols-rounded" style="font-size: 26px;">block</span> Ação Bloqueada
                </div>
                <div style="color: #1a2a40; font-size: 17px; line-height: 1.6;">
                    Não é possível excluir a categoria <b style="color: #e76f51;">{nome_atual}</b>.<br>
                    <strong>Motivo:</strong> Existem <b>{total_vinculos}</b> classificação(ões) vinculada(s).
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
                    Tem a certeza que deseja excluir a categoria <b>{nome_atual}</b>?<br>
                    <span style="color: #e76f51;"><i>Esta ação removerá o registo permanentemente.</i></span>
                </div>
            </div>
            """
            st.markdown(html_confirmacao, unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 3, 3])
            with c2:
                if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
            with c3:
                st.button("Confirmar", type="primary", use_container_width=True, on_click=callback_exclusao, args=(id_cat,))
    else:
        c1, c2 = st.columns([7, 3])
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()

@st.dialog(":material/folder: Duplicar categoria")
def modal_duplicacao(nome_atual, tipo_atual):
    UtilitariosVisuais.exibir_mensagens()
    
    val_nome = "" if st.session_state.form_cleared else f"{nome_atual} (Cópia)"
    val_tipo = 0 if st.session_state.form_cleared else (0 if tipo_atual == "Receita" else 1)
    
    st.text_input("Novo nome da categoria (cópia):", value=val_nome, key=f"dup_nome_c_{st.session_state.form_reset}")
    st.selectbox("Natureza:", ["Receita", "Despesa"], index=val_tipo, key=f"dup_tipo_c_{st.session_state.form_reset}")
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_duplicacao)

# ==========================================
# CONSTRUÇÃO DA TELA (VIEW)
# ==========================================
if 'f_cat_pesq' not in st.session_state: st.session_state.f_cat_pesq = ""
if 'f_cat_nat' not in st.session_state: st.session_state.f_cat_nat = "Todas as naturezas"
if 'show_f_cat' not in st.session_state: st.session_state.show_f_cat = False

c_titulo, c_filtrar, c_inserir, c_margem = st.columns([5, 1.5, 1.5, 3])
with c_titulo: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>folder</span> Cadastro de Categorias</h3>", unsafe_allow_html=True)
with c_filtrar:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True):
        st.session_state.show_f_cat = not st.session_state.show_f_cat; st.rerun()
with c_inserir:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True): 
        UtilitariosVisuais.preparar_modal()
        modal_inclusao()

if st.session_state.show_f_cat:
    with st.container(border=True):
        cp, cn, cb = st.columns([5, 3, 2])
        v_pesq = cp.text_input("Pesquisar nome da categoria:", value=st.session_state.f_cat_pesq)
        op_nat = ["Todas as naturezas", "Receita", "Despesa"]
        v_nat = cn.selectbox("Natureza:", op_nat, index=op_nat.index(st.session_state.f_cat_nat))
        cb.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if cb.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True):
            st.session_state.f_cat_pesq, st.session_state.f_cat_nat = v_pesq, v_nat; st.rerun()
st.markdown("<br>", unsafe_allow_html=True)

df = carregar_dados(st.session_state.f_cat_pesq, st.session_state.f_cat_nat)
st.markdown('<div class="cabecalho-grid"><div style="display: flex;"><div style="flex: 5;">Nome da categoria</div><div style="flex: 2; text-align: center;">Natureza</div><div style="flex: 2; text-align: center;">Ações</div></div></div>', unsafe_allow_html=True)

if df.empty:
    st.info("Nenhuma categoria encontrada na base de dados para este filtro.")
else:
    with st.container():
        st.markdown("<div class='btn-acao-grid'>", unsafe_allow_html=True)
        for _, row in df.iterrows():
            id_cat, nome_cat, nat = row['id'], row['Nome da categoria'], row['Natureza']
            c1, c2, c3, c4, c5 = st.columns([5, 2, 0.66, 0.66, 0.68], vertical_alignment="center")
            c1.markdown(f"<span style='font-weight: 600; color: #1a2a40; font-size: 15px; padding-left: 10px;'>{nome_cat}</span>", unsafe_allow_html=True)
            badge = "badge-receita" if nat == "Receita" else "badge-despesa"
            c2.markdown(f"<div style='text-align: center;'><span class='{badge}'>{nat}</span></div>", unsafe_allow_html=True)
            if c3.button(" ", icon=":material/edit:", key=f"ec_{id_cat}", help="Editar", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_alteracao(int(id_cat), nome_cat, nat)
            if c4.button(" ", icon=":material/content_copy:", key=f"dc_{id_cat}", help="Duplicar", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_duplicacao(nome_cat, nat)
            if c5.button(" ", icon=":material/delete:", key=f"xc_{id_cat}", help="Excluir", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_exclusao(int(id_cat), nome_cat)
            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)