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
    query = "SELECT id, nome, tipo FROM categorias"
    params = []
    if pesquisa:
        query += " WHERE nome ILIKE %s"
        params.append(f"%{pesquisa}%")
    query += " ORDER BY nome ASC"
    return GerenciadorBanco.executar_query(query, tuple(params))

def callback_inclusao():
    nome = st.session_state.get(f"inc_nome_cat_{st.session_state.form_reset}", "")
    tipo = st.session_state.get(f"inc_tipo_cat_{st.session_state.form_reset}", "Despesa")
    
    if nome.strip():
        GerenciadorBanco.executar_query("INSERT INTO categorias (nome, tipo) VALUES (%s, %s)", (nome, tipo), is_select=False)
        st.session_state.msg_sucesso_inc = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1
    else:
        st.session_state.msg_erro = "O nome da categoria é obrigatório."

def callback_alteracao(id_cat):
    nome = st.session_state.get(f"alt_nome_cat_{st.session_state.form_reset}", "")
    tipo = st.session_state.get(f"alt_tipo_cat_{st.session_state.form_reset}", "Despesa")
    
    if nome.strip():
        GerenciadorBanco.executar_query("UPDATE categorias SET nome = %s, tipo = %s WHERE id = %s", (nome, tipo, id_cat), is_select=False)
        st.session_state.msg_sucesso = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1
    else:
        st.session_state.msg_erro = "O nome da categoria é obrigatório."

def callback_exclusao(id_cat):
    df_clas = GerenciadorBanco.executar_query("SELECT count(id) as total FROM classificacoes WHERE id_categoria = %s", (int(id_cat),))
    if df_clas.iloc[0]['total'] > 0:
        st.session_state.msg_erro = "Ação bloqueada: Existem classificações vinculadas a esta categoria."
        st.session_state.form_cleared = True
    else:
        GerenciadorBanco.executar_query("DELETE FROM categorias WHERE id = %s", (int(id_cat),), is_select=False)
        st.session_state.msg_sucesso = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1

# ==========================================
# MODAIS DE INTERAÇÃO
# ==========================================
@st.dialog(":material/add_circle: Nova categoria")
def modal_inclusao(nome_base="", tipo_base="Despesa"):
    val_nome = "" if st.session_state.form_cleared else nome_base
    idx_tipo = 0 if tipo_base == "Despesa" else 1
    idx_selecionado = 0 if st.session_state.form_cleared else idx_tipo
    
    if nome_base and not st.session_state.form_cleared:
        st.info("Modo de Replicação: Altere o nome para salvar como uma nova categoria.")
        
    st.text_input("Nome da categoria:", value=val_nome, key=f"inc_nome_cat_{st.session_state.form_reset}")
    st.selectbox("Natureza (Tipo):", ["Despesa", "Receita"], index=idx_selecionado, key=f"inc_tipo_cat_{st.session_state.form_reset}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_inclusao)
        
    if st.session_state.get("msg_sucesso_inc"):
        st.toast("Operação realizada com sucesso!", icon="✅")
        st.session_state.msg_sucesso_inc = False
        st.session_state.form_cleared = False
    elif st.session_state.get("msg_erro"):
        st.toast(st.session_state.msg_erro, icon="❌")
        st.session_state.msg_erro = ""

@st.dialog(":material/edit: Editar categoria")
def modal_alteracao(id_cat, nome_atual, tipo_atual):
    UtilitariosVisuais.exibir_mensagens()
    val_nome = "" if st.session_state.form_cleared else nome_atual
    idx_tipo = 0 if tipo_atual == "Despesa" else 1
    idx_selecionado = 0 if st.session_state.form_cleared else idx_tipo
    
    st.text_input("Nome da categoria:", value=val_nome, key=f"alt_nome_cat_{st.session_state.form_reset}")
    st.selectbox("Natureza (Tipo):", ["Despesa", "Receita"], index=idx_selecionado, key=f"alt_tipo_cat_{st.session_state.form_reset}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_alteracao, args=(id_cat,))

@st.dialog(":material/delete: Excluir categoria")
def modal_exclusao(id_cat, nome_atual):
    UtilitariosVisuais.exibir_mensagens()
    if not st.session_state.form_cleared:
        html_confirmacao = f"""
        <div style="border-left: 5px solid #e76f51; background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #e9ecef;">
            <div style="color: #1a2a40; font-size: 17px; line-height: 1.6;">
                Tem a certeza que deseja excluir a categoria <b>{nome_atual}</b>?<br>
                <span style="color: #e76f51;"><i>Esta ação é irreversível.</i></span>
            </div>
        </div>
        """
        st.markdown(html_confirmacao, unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
        with c3:
            st.button("Confirmar", type="primary", use_container_width=True, on_click=callback_exclusao, args=(id_cat,))
    else:
        c1, c2, c3 = st.columns(3)
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
if 'f_cat_pesq' not in st.session_state: st.session_state.f_cat_pesq = ""
if 'f_cat_tipo' not in st.session_state or isinstance(st.session_state.f_cat_tipo, str): st.session_state.f_cat_tipo = []
if 'show_f_cat' not in st.session_state: st.session_state.show_f_cat = False

c_titulo, c_filtrar, c_inserir, c_margem = st.columns([5, 1.5, 1.5, 3])
with c_titulo: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>folder</span> Cadastro de Categorias</h3>", unsafe_allow_html=True)
with c_filtrar:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True):
        st.session_state.show_f_cat = not st.session_state.show_f_cat; st.rerun()
with c_inserir:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True): 
        UtilitariosVisuais.preparar_modal(); modal_inclusao()

if st.session_state.show_f_cat:
    with st.container(border=True):
        f1, f2, f_check, f_btn = st.columns([3, 2.5, 1.5, 1.5], vertical_alignment="bottom")
        v_pesq = f1.text_input("Pesquisar nome da categoria:", value=st.session_state.f_cat_pesq)
        
        op_tipo = ["Receita", "Despesa"]
        v_tipo = f2.multiselect("Natureza:", options=op_tipo, default=st.session_state.f_cat_tipo, placeholder="Todas as naturezas")
        
        with f_check:
            auto_refresh = st.checkbox("Refresh automático", value=st.session_state.get('f_cat_auto', False), key='f_cat_auto')
        with f_btn:
            if auto_refresh:
                st.session_state.f_cat_pesq = v_pesq
                st.session_state.f_cat_tipo = v_tipo
                st.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True, disabled=True)
            else:
                if st.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True):
                    st.session_state.f_cat_pesq = v_pesq
                    st.session_state.f_cat_tipo = v_tipo
                    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

df = carregar_dados(st.session_state.f_cat_pesq)

if not df.empty and st.session_state.f_cat_tipo:
    df = df[df['tipo'].isin(st.session_state.f_cat_tipo)]

html_cabecalho = '''
<div class="cabecalho-grid">
    <div style="display: flex;">
        <div style="flex: 5;">Nome da Categoria</div>
        <div style="flex: 3; text-align: center;">Natureza (Tipo)</div>
        <div style="flex: 2; text-align: center;">Ações</div>
    </div>
</div>
'''
st.markdown(html_cabecalho, unsafe_allow_html=True)

if df.empty:
    st.info("Nenhuma categoria encontrada.")
else:
    with st.container():
        st.markdown("<div class='btn-acao-grid'>", unsafe_allow_html=True)
        for _, row in df.iterrows():
            id_cat, nome, tipo = row['id'], row['nome'], row['tipo']
            c1, c2, c3, c4, c5 = st.columns([5, 3, 0.65, 0.65, 0.65], vertical_alignment="center")
            c1.markdown(f"<span style='font-weight: 600; color: #1a2a40; font-size: 15px; padding-left: 10px;'>{nome}</span>", unsafe_allow_html=True)
            
            badge = "badge-receita" if tipo == "Receita" else "badge-despesa"
            c2.markdown(f"<div style='text-align: center;'><span class='{badge}'>{tipo}</span></div>", unsafe_allow_html=True)
            
            if c3.button(" ", icon=":material/content_copy:", key=f"rc_{id_cat}", help="Replicar", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_inclusao(nome, tipo)
            if c4.button(" ", icon=":material/edit:", key=f"ec_{id_cat}", help="Editar", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_alteracao(int(id_cat), nome, tipo)
            if c5.button(" ", icon=":material/delete:", key=f"xc_{id_cat}", help="Excluir", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_exclusao(int(id_cat), nome)
            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)