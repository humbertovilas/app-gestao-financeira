import streamlit as st
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais
import pandas as pd
import time
import os
import base64

UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

# ==========================================
# ACESSO A DADOS (CRUD)
# ==========================================
def carregar_dados(pesquisa=""):
    query = """
    SELECT c.id, c.nome, c.id_categoria, c.icone, cat.nome as categoria, cat.tipo 
    FROM classificacoes c
    INNER JOIN categorias cat ON c.id_categoria = cat.id
    """
    params = []
    if pesquisa:
        query += " WHERE c.nome ILIKE %s"
        params.append(f"%{pesquisa}%")
    query += " ORDER BY c.nome ASC"
    return GerenciadorBanco.executar_query(query, tuple(params))

def obter_categorias():
    return GerenciadorBanco.executar_query("SELECT id, nome, tipo FROM categorias ORDER BY nome ASC")

def obter_lista_cat_filtro():
    df_cat = GerenciadorBanco.executar_query("SELECT DISTINCT nome FROM categorias ORDER BY nome")
    return df_cat['nome'].tolist() if not df_cat.empty else []

def callback_inclusao(icone_base):
    nome = st.session_state.get(f"inc_nome_cls_{st.session_state.form_reset}", "")
    categoria_str = st.session_state.get(f"inc_cat_cls_{st.session_state.form_reset}", "")
    upload_arquivo = st.session_state.get(f"up_ico_cls_{st.session_state.form_reset}")
    remover_icone = st.session_state.get(f"rm_ico_inc_{st.session_state.form_reset}", False)
    
    if remover_icone:
        icone_final = "Sem ícone"
    else:
        icone_final = UtilitariosVisuais.salvar_icone_upload(upload_arquivo) if upload_arquivo is not None else icone_base
    
    if nome.strip() and categoria_str:
        id_categoria = int(categoria_str.split(" - ")[0])
        GerenciadorBanco.executar_query("INSERT INTO classificacoes (nome, id_categoria, icone) VALUES (%s, %s, %s)", (nome, id_categoria, icone_final), is_select=False)
        st.session_state.msg_sucesso_inc = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1
    else:
        st.session_state.msg_erro = "Nome e categoria são obrigatórios."

def callback_alteracao(id_cls, icone_atual):
    nome = st.session_state.get(f"alt_nome_cls_{st.session_state.form_reset}", "")
    categoria_str = st.session_state.get(f"alt_cat_cls_{st.session_state.form_reset}", "")
    upload_arquivo = st.session_state.get(f"up_ico_cls_{st.session_state.form_reset}")
    remover_icone = st.session_state.get(f"rm_ico_alt_{st.session_state.form_reset}", False)
    
    if remover_icone:
        icone_final = "Sem ícone"
    else:
        icone_final = UtilitariosVisuais.salvar_icone_upload(upload_arquivo) if upload_arquivo is not None else icone_atual
    
    if nome.strip() and categoria_str:
        id_categoria = int(categoria_str.split(" - ")[0])
        GerenciadorBanco.executar_query("UPDATE classificacoes SET nome = %s, id_categoria = %s, icone = %s WHERE id = %s", (nome, id_categoria, icone_final, id_cls), is_select=False)
        st.session_state.msg_sucesso = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1
    else:
        st.session_state.msg_erro = "Nome e categoria são obrigatórios."

def callback_exclusao(id_cls):
    df_ev = GerenciadorBanco.executar_query("SELECT count(id) as total FROM eventos WHERE id_classificacao = %s", (int(id_cls),))
    if df_ev.iloc[0]['total'] > 0:
        st.session_state.msg_erro = "Ação bloqueada: Existem eventos vinculados a esta classificação."
        st.session_state.form_cleared = True
    else:
        GerenciadorBanco.executar_query("DELETE FROM classificacoes WHERE id = %s", (int(id_cls),), is_select=False)
        st.session_state.msg_sucesso = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1

# ==========================================
# MODAIS DE INTERAÇÃO (PRÉVIA VISUAL REATIVA)
# ==========================================
@st.dialog(":material/add_circle: Nova classificação")
def modal_inclusao(nome_base="", id_cat_base=None, nome_cat_base="", tipo_cat_base="", icone_base="Sem ícone"):
    df_categorias = obter_categorias()
    opcoes_cat = []
    idx_selecionado = 0
    if not df_categorias.empty:
        opcoes_cat = [f"{r['id']} - {r['nome']} ({r['tipo']})" for _, r in df_categorias.iterrows()]
        if id_cat_base:
            str_busca = f"{id_cat_base} - {nome_cat_base} ({tipo_cat_base})"
            idx_atual = opcoes_cat.index(str_busca) if str_busca in opcoes_cat else 0
            idx_selecionado = 0 if st.session_state.form_cleared else idx_atual

    if nome_base and not st.session_state.form_cleared:
        st.info("Modo de Replicação: Altere o nome para salvar como uma nova classificação.")
        
    val_nome = "" if st.session_state.form_cleared else nome_base
    st.text_input("Nome da classificação:", value=val_nome, key=f"inc_nome_cls_{st.session_state.form_reset}")
    
    if opcoes_cat:
        st.selectbox("Categoria mestre:", opcoes_cat, index=idx_selecionado, key=f"inc_cat_cls_{st.session_state.form_reset}")
    else:
        st.warning("Cadastre uma categoria primeiro.")
        
    st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
    
    upload_arquivo = st.file_uploader("Selecionar novo ícone (Procurar no computador):", type=["png"], key=f"up_ico_cls_{st.session_state.form_reset}")
    
    icone_atual_seguro = icone_base if pd.notna(icone_base) else "Sem ícone"
    
    # Inteligência de Pré-visualização com Opção de Remoção
    if upload_arquivo is not None:
        b64_uploaded = base64.b64encode(upload_arquivo.getvalue()).decode()
        st.markdown(f"<div style='margin-top: 5px; text-align: center;'><span style='font-size: 13px; font-weight: 600; color: #20c997;'>Pré-visualização do envio:</span><br><img src='data:image/png;base64,{b64_uploaded}' style='width: 64px; height: 64px; mix-blend-mode: multiply; border: 2px solid #20c997; padding: 4px; border-radius: 8px; background-color: #f8f9fa; margin-top: 5px;' /></div>", unsafe_allow_html=True)
    elif icone_atual_seguro != "Sem ícone" and not st.session_state.form_cleared:
        b64 = UtilitariosVisuais.obter_imagem_base64(os.path.join("Imagens", "Icones", icone_atual_seguro))
        if b64:
            c_prev, c_rm = st.columns([1, 1])
            with c_prev:
                st.markdown(f"<div style='margin-top: 5px; text-align: center;'><span style='font-size: 13px; font-weight: 600; color: #495057;'>Ícone base:</span><br><img src='data:image/png;base64,{b64}' style='width: 64px; height: 64px; mix-blend-mode: multiply; border: 1px solid #ced4da; padding: 4px; border-radius: 8px; background-color: #f8f9fa; margin-top: 5px;' /></div>", unsafe_allow_html=True)
            with c_rm:
                st.markdown("<div style='margin-top: 35px;'></div>", unsafe_allow_html=True)
                st.checkbox("Remover ícone", key=f"rm_ico_inc_{st.session_state.form_reset}")
        
    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns(3)
    with b2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with b3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_inclusao, args=(icone_atual_seguro,), disabled=len(opcoes_cat)==0)

    if st.session_state.get("msg_sucesso_inc"):
        st.toast("Operação realizada com sucesso!", icon="✅")
        st.session_state.msg_sucesso_inc = False
        st.session_state.form_cleared = False
    elif st.session_state.get("msg_erro"):
        st.toast(st.session_state.msg_erro, icon="❌")
        st.session_state.msg_erro = ""

@st.dialog(":material/edit: Editar classificação")
def modal_alteracao(id_cls, nome_atual, id_cat_atual, nome_cat_atual, tipo_cat_atual, icone_atual):
    UtilitariosVisuais.exibir_mensagens()
    df_categorias = obter_categorias()
    opcoes_cat = [f"{r['id']} - {r['nome']} ({r['tipo']})" for _, r in df_categorias.iterrows()]
    str_busca = f"{id_cat_atual} - {nome_cat_atual} ({tipo_cat_atual})"
    idx_atual = opcoes_cat.index(str_busca) if str_busca in opcoes_cat else 0
    
    val_nome = "" if st.session_state.form_cleared else nome_atual
    idx_selecionado = 0 if st.session_state.form_cleared else idx_atual
    
    st.text_input("Nome da classificação:", value=val_nome, key=f"alt_nome_cls_{st.session_state.form_reset}")
    st.selectbox("Categoria mestre:", opcoes_cat, index=idx_selecionado, key=f"alt_cat_cls_{st.session_state.form_reset}")
    
    st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
    
    upload_arquivo = st.file_uploader("Selecionar novo ícone (Procurar no computador):", type=["png"], key=f"up_ico_cls_{st.session_state.form_reset}")
    
    icone_atual_seguro = icone_atual if pd.notna(icone_atual) else "Sem ícone"
    
    # Inteligência de Pré-visualização com Opção de Remoção
    if upload_arquivo is not None:
        b64_uploaded = base64.b64encode(upload_arquivo.getvalue()).decode()
        st.markdown(f"<div style='margin-top: 5px; text-align: center;'><span style='font-size: 13px; font-weight: 600; color: #20c997;'>Novo ícone selecionado:</span><br><img src='data:image/png;base64,{b64_uploaded}' style='width: 64px; height: 64px; mix-blend-mode: multiply; border: 2px solid #20c997; padding: 4px; border-radius: 8px; background-color: #f8f9fa; margin-top: 5px;' /></div>", unsafe_allow_html=True)
    elif icone_atual_seguro != "Sem ícone":
        b64 = UtilitariosVisuais.obter_imagem_base64(os.path.join("Imagens", "Icones", icone_atual_seguro))
        if b64:
            c_prev, c_rm = st.columns([1, 1])
            with c_prev:
                st.markdown(f"<div style='margin-top: 5px; text-align: center;'><span style='font-size: 13px; font-weight: 600; color: #495057;'>Ícone atual vinculado:</span><br><img src='data:image/png;base64,{b64}' style='width: 64px; height: 64px; mix-blend-mode: multiply; border: 1px solid #ced4da; padding: 4px; border-radius: 8px; background-color: #f8f9fa; margin-top: 5px;' /></div>", unsafe_allow_html=True)
            with c_rm:
                st.markdown("<div style='margin-top: 35px;'></div>", unsafe_allow_html=True)
                st.checkbox("Remover ícone", key=f"rm_ico_alt_{st.session_state.form_reset}")
            
    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns(3)
    with b2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with b3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_alteracao, args=(id_cls, icone_atual_seguro))

@st.dialog(":material/delete: Excluir classificação")
def modal_exclusao(id_cls, nome_atual):
    UtilitariosVisuais.exibir_mensagens()
    if not st.session_state.form_cleared:
        html_confirmacao = f"""
        <div style="border-left: 5px solid #e76f51; background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #e9ecef;">
            <div style="color: #1a2a40; font-size: 17px; line-height: 1.6;">
                Tem a certeza que deseja excluir a classificação <b>{nome_atual}</b>?<br>
                <span style="color: #e76f51;"><i>Esta ação é irreversível.</i></span>
            </div>
        </div>
        """
        st.markdown(html_confirmacao, unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
        with c3:
            st.button("Confirmar", type="primary", use_container_width=True, on_click=callback_exclusao, args=(id_cls,))
    else:
        c1, c2, c3 = st.columns(3)
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
if 'f_cls_pesq' not in st.session_state: st.session_state.f_cls_pesq = ""
if 'f_cls_cat' not in st.session_state or isinstance(st.session_state.f_cls_cat, str): st.session_state.f_cls_cat = []
if 'show_f_cls' not in st.session_state: st.session_state.show_f_cls = False

c_titulo, c_filtrar, c_inserir, c_margem = st.columns([5, 1.5, 1.5, 3])
with c_titulo: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>account_tree</span> Cadastro de Classificações</h3>", unsafe_allow_html=True)
with c_filtrar:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True):
        st.session_state.show_f_cls = not st.session_state.show_f_cls; st.rerun()
with c_inserir:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True): 
        UtilitariosVisuais.preparar_modal(); modal_inclusao()

if st.session_state.show_f_cls:
    with st.container(border=True):
        lista_cat = obter_lista_cat_filtro()
        
        f1, f2, f_check, f_btn = st.columns([3, 2.5, 1.5, 1.5], vertical_alignment="bottom")
        v_pesq = f1.text_input("Pesquisar classificação:", value=st.session_state.f_cls_pesq)
        v_cat = f2.multiselect("Filtrar por categoria:", options=lista_cat, default=st.session_state.f_cls_cat, placeholder="Todas as categorias")
        
        with f_check:
            auto_refresh = st.checkbox("Refresh automático", value=st.session_state.get('f_cls_auto', False), key='f_cls_auto')
        with f_btn:
            if auto_refresh:
                st.session_state.f_cls_pesq = v_pesq
                st.session_state.f_cls_cat = v_cat
                st.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True, disabled=True)
            else:
                if st.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True):
                    st.session_state.f_cls_pesq = v_pesq
                    st.session_state.f_cls_cat = v_cat
                    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

df = carregar_dados(st.session_state.f_cls_pesq)

if not df.empty and st.session_state.f_cls_cat:
    df = df[df['categoria'].isin(st.session_state.f_cls_cat)]

html_cabecalho = '''
<div class="cabecalho-grid">
    <div style="display: flex;">
        <div style="flex: 4;">Nome da Classificação</div>
        <div style="flex: 4;">Categoria vinculada</div>
        <div style="flex: 2; text-align: center;">Ações</div>
    </div>
</div>
'''
st.markdown(html_cabecalho, unsafe_allow_html=True)

if df.empty:
    st.info("Nenhuma classificação encontrada.")
else:
    with st.container():
        st.markdown("<div class='btn-acao-grid'>", unsafe_allow_html=True)
        for _, row in df.iterrows():
            id_cls, nome, id_cat, categoria, tipo, icone = row['id'], row['nome'], row['id_categoria'], row['categoria'], row['tipo'], row['icone']
            c1, c2, c3, c4, c5 = st.columns([4, 4, 0.65, 0.65, 0.65], vertical_alignment="center")
            
            html_icone = ""
            if pd.notna(icone) and icone != "Sem ícone":
                b64 = UtilitariosVisuais.obter_imagem_base64(os.path.join("Imagens", "Icones", icone))
                if b64:
                    html_icone = f"<img src='data:image/png;base64,{b64}' style='width: 48px; height: 48px; margin-right: 15px; vertical-align: middle; mix-blend-mode: multiply;' />"
            
            c1.markdown(f"<div style='display: flex; align-items: center; padding-left: 10px;'>{html_icone}<span style='font-weight: 600; color: #1a2a40; font-size: 15px;'>{nome}</span></div>", unsafe_allow_html=True)
            
            badge = "badge-receita" if tipo == "Receita" else "badge-despesa"
            c2.markdown(f"<div style='display: flex; align-items: center; gap: 10px;'><span style='color: #495057; font-size: 14px;'>{categoria}</span><span class='{badge}'>{tipo}</span></div>", unsafe_allow_html=True)
            
            if c3.button(" ", icon=":material/content_copy:", key=f"rcl_{id_cls}", help="Replicar", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_inclusao(nome, int(id_cat), categoria, tipo, icone)
            if c4.button(" ", icon=":material/edit:", key=f"ecl_{id_cls}", help="Editar", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_alteracao(int(id_cls), nome, int(id_cat), categoria, tipo, icone)
            if c5.button(" ", icon=":material/delete:", key=f"xcl_{id_cls}", help="Excluir", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_exclusao(int(id_cls), nome)
            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)