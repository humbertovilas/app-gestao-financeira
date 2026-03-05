import streamlit as st
import streamlit.components.v1 as components
import psycopg2
import pandas as pd
import time
import os

# ==========================================
# INÍCIO DO MÓDULO: CONFIGURAÇÃO DE PÁGINA E CSS
# ==========================================
caminho_favicon = os.path.join("Imagens", "favicon.png")
if not os.path.exists(caminho_favicon):
    caminho_favicon = os.path.join("IMAGENS", "favicon.png")

st.set_page_config(
    page_title="Gestão Financeira",
    page_icon=caminho_favicon if os.path.exists(caminho_favicon) else None,
    layout="wide"
)

# Injeção SEGURA da biblioteca de ícones do Google
st.markdown("<link href='https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0' rel='stylesheet'>", unsafe_allow_html=True)

def carregar_css(file_name):
    with open(file_name, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

try:
    carregar_css("style.css")
except Exception as e:
    st.error(f"Erro ao carregar o CSS: {e}")

# ==========================================
# INÍCIO DO MÓDULO: INFRAESTRUTURA DE DADOS (ALTA PERFORMANCE)
# ==========================================
@st.cache_resource(ttl=3600)
def get_db_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

@st.cache_resource
def inicializar_banco():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS categorias 
                      (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, tipo TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS classificacoes 
                      (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, id_categoria INTEGER NOT NULL, 
                       FOREIGN KEY (id_categoria) REFERENCES categorias (id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS eventos 
                      (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, id_classificacao INTEGER NOT NULL, 
                       FOREIGN KEY (id_classificacao) REFERENCES classificacoes (id))''')
    conn.commit()

try:
    inicializar_banco()
except Exception as e:
    st.error(f"Detalhe técnico do erro: {e}")
    st.stop()

# ==========================================
# FUNÇÕES DE APOIO (DATABASE POSTGRESQL COM RECONEXÃO AUTOMÁTICA)
# ==========================================
def db_query(query, params=(), is_select=True):
    try:
        conn = get_db_connection()
        if is_select:
            return pd.read_sql_query(query, conn, params=params)
        else:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
    except psycopg2.OperationalError:
        st.cache_resource.clear()
        conn = get_db_connection()
        if is_select:
            return pd.read_sql_query(query, conn, params=params)
        else:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

# ==========================================
# INÍCIO DO MÓDULO: NAVEGAÇÃO WEB E MENSAGENS
# ==========================================
def injetar_navegacao_enter():
    js = """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            const active = doc.activeElement;
            if (active && (active.tagName === 'INPUT' || active.tagName === 'SELECT')) {
                e.preventDefault(); 
                const focusable = Array.from(doc.querySelectorAll('input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])'));
                const index = focusable.indexOf(active);
                if (index > -1 && index < focusable.length - 1) {
                    focusable[index + 1].focus();
                }
            }
        }
    });
    </script>
    """
    components.html(js, height=0, width=0)

injetar_navegacao_enter()

def injeção_js_alerta_3s():
    js_ocultar_alerta = """
    <script>
    const doc = window.parent.document;
    setTimeout(() => {
        const alertas = doc.querySelectorAll('[data-testid="stAlert"]');
        alertas.forEach(alerta => {
            alerta.style.transition = 'opacity 0.5s ease';
            alerta.style.opacity = '0';
            setTimeout(() => alerta.style.display = 'none', 500);
        });
    }, 3000);
    </script>
    """
    components.html(js_ocultar_alerta, height=0, width=0)

# ==========================================
# INÍCIO DO MÓDULO: MENU LATERAL (SIDEBAR)
# ==========================================
if 'modulo_ativo' not in st.session_state:
    st.session_state.modulo_ativo = "Categorias"

@st.dialog(":material/construction: Aviso do sistema")
def modal_em_construcao(nome_modulo):
    st.info(f"Módulo \"{nome_modulo}\" em construção. Aguarde...")
    if st.button("Fechar", type="secondary", use_container_width=True):
        st.rerun()

with st.sidebar:
    st.markdown("""
        <div class='sidebar-title'>
            <span class='material-symbols-rounded' style='color: #20c997; margin-right: 10px; font-size: 28px;'>pie_chart</span>
            Gestão Financeira
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Dashboard", icon=":material/dashboard:", use_container_width=True): modal_em_construcao("Dashboard")
    if st.button("Agenda financeira", icon=":material/calendar_month:", use_container_width=True): modal_em_construcao("Agenda financeira")
    if st.button("Lançamentos", icon=":material/sync_alt:", use_container_width=True): modal_em_construcao("Lançamentos")
    
    if st.button("Eventos", type="primary" if st.session_state.modulo_ativo == "Eventos" else "secondary", icon=":material/sell:", use_container_width=True):
        st.session_state.modulo_ativo = "Eventos"
        st.rerun()
    
    if st.button("Classificações", type="primary" if st.session_state.modulo_ativo == "Classificações" else "secondary", icon=":material/account_tree:", use_container_width=True):
        st.session_state.modulo_ativo = "Classificações"
        st.rerun()
        
    if st.button("Categorias", type="primary" if st.session_state.modulo_ativo == "Categorias" else "secondary", icon=":material/folder:", use_container_width=True):
        st.session_state.modulo_ativo = "Categorias"
        st.rerun()

# ==========================================
# MÓDULO: CATEGORIAS
# ==========================================
def carregar_dados_categorias(pesquisa="", natureza="Todas as naturezas"):
    query = "SELECT id, nome as \"Nome da categoria\", tipo as \"Natureza\" FROM categorias WHERE 1=1"
    params = []
    if pesquisa:
        query += " AND nome ILIKE %s"
        params.append(f"%{pesquisa}%")
    if natureza == "Receita": query += " AND tipo = 'Receita'"
    elif natureza == "Despesa": query += " AND tipo = 'Despesa'"
    query += " ORDER BY id DESC"
    return db_query(query, tuple(params))

def salvar_categoria(nome, tipo):
    db_query("INSERT INTO categorias (nome, tipo) VALUES (%s, %s)", (nome, tipo), is_select=False)

@st.dialog(":material/folder: Nova categoria")
def modal_inclusao_categoria():
    nome = st.text_input("Nome da categoria:", placeholder="Ex: Alimentação, Salário...", key="inc_nome")
    tipo = st.selectbox("Natureza:", ["Receita", "Despesa"], key="inc_tipo")
    st.write("")
    
    msg_placeholder = st.empty()
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Cancelar", type="secondary", use_container_width=True, key="inc_btn_canc"): st.rerun()
    with c3:
        if st.button("Salvar", type="primary", use_container_width=True, key="inc_btn_salv"):
            if nome.strip():
                with st.spinner("Processando..."):
                    salvar_categoria(nome, tipo)
                    time.sleep(0.4)
                msg_placeholder.success(f"Categoria '{nome}' registada com sucesso!")
                time.sleep(1); st.rerun()
            else:
                msg_placeholder.error("O campo de nome é obrigatório.")

@st.dialog(":material/folder: Editar categoria")
def modal_alteracao_categoria(id_cat, nome_atual, tipo_atual):
    nome = st.text_input("Nome da categoria:", value=nome_atual, key=f"alt_nome_{id_cat}")
    idx_tipo = 0 if tipo_atual == "Receita" else 1
    tipo = st.selectbox("Natureza:", ["Receita", "Despesa"], index=idx_tipo, key=f"alt_tipo_{id_cat}")
    st.write("")
    
    msg_placeholder = st.empty()
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Cancelar", type="secondary", use_container_width=True, key=f"alt_btn_canc_{id_cat}"): st.rerun()
    with c3:
        if st.button("Salvar", type="primary", use_container_width=True, key=f"alt_btn_salv_{id_cat}"):
            if nome.strip():
                with st.spinner("Processando..."):
                    db_query("UPDATE categorias SET nome = %s, tipo = %s WHERE id = %s", (nome, tipo, id_cat), is_select=False)
                    time.sleep(0.4)
                msg_placeholder.success("Categoria atualizada com sucesso!")
                time.sleep(1); st.rerun()
            else: 
                msg_placeholder.error("O campo de nome é obrigatório.")

@st.dialog(":material/folder: Excluir categoria")
def modal_exclusao_categoria(id_cat, nome_atual):
    df_vinculos = db_query("SELECT COUNT(id) as total FROM classificacoes WHERE id_categoria = %s", (id_cat,))
    total_vinculos = int(df_vinculos.iloc[0]['total'])

    if total_vinculos > 0:
        html_bloqueio = f"""
        <div style="border-left: 5px solid #e76f51; background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #e9ecef;">
            <div style="display: flex; align-items: center; gap: 8px; color: #e76f51; font-weight: bold; font-size: 19px; margin-bottom: 12px;">
                <span class="material-symbols-rounded" style="font-size: 26px;">block</span> Ação Bloqueada
            </div>
            <div style="color: #1a2a40; font-size: 17px; line-height: 1.6;">
                Não é possível excluir a categoria <b style="color: #e76f51;">{nome_atual}</b>.<br>
                <strong>Motivo:</strong> Existem <b>{total_vinculos}</b> classificação(ões) vinculada(s) a esta categoria.<br><br>
                <span style="color: #457b9d;"><i>Por favor, altere ou exclua as classificações dependentes antes de tentar novamente.</i></span>
            </div>
        </div>
        """
        st.markdown(html_bloqueio, unsafe_allow_html=True)
        c1, c2 = st.columns([6, 4])
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True, key=f"exc_btn_fechar_{id_cat}"): st.rerun()
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
        msg_placeholder = st.empty()
        c1, c2, c3 = st.columns([2, 3, 3])
        with c2:
            if st.button("Cancelar", type="secondary", use_container_width=True, key=f"exc_btn_canc_{id_cat}"): st.rerun()
        with c3:
            if st.button("Confirmar exclusão", type="primary", use_container_width=True, key=f"exc_btn_conf_{id_cat}"):
                with st.spinner("Processando..."):
                    db_query("DELETE FROM categorias WHERE id = %s", (int(id_cat),), is_select=False)
                    time.sleep(0.4)
                msg_placeholder.success("Categoria excluída com sucesso!")
                time.sleep(1); st.rerun()

@st.dialog(":material/folder: Duplicar categoria")
def modal_duplicacao_categoria(nome_atual, tipo_atual):
    nome = st.text_input("Novo nome da categoria (cópia):", value=f"{nome_atual} (Cópia)", key=f"dup_nome_{nome_atual}")
    idx_tipo = 0 if tipo_atual == "Receita" else 1
    tipo = st.selectbox("Natureza:", ["Receita", "Despesa"], index=idx_tipo, key=f"dup_tipo_{nome_atual}")
    st.write("")
    
    msg_placeholder = st.empty()
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Cancelar", type="secondary", use_container_width=True, key=f"dup_btn_canc_{nome_atual}"): st.rerun()
    with c3:
        if st.button("Salvar", type="primary", use_container_width=True, key=f"dup_btn_salv_{nome_atual}"):
            if nome.strip():
                with st.spinner("Processando..."):
                    salvar_categoria(nome, tipo)
                    time.sleep(0.4)
                msg_placeholder.success("Categoria duplicada com sucesso!")
                time.sleep(1); st.rerun()
            else: 
                msg_placeholder.error("O campo de nome é obrigatório.")

def render_categorias():
    if 'f_cat_pesq' not in st.session_state: st.session_state.f_cat_pesq = ""
    if 'f_cat_nat' not in st.session_state: st.session_state.f_cat_nat = "Todas as naturezas"
    if 'show_f_cat' not in st.session_state: st.session_state.show_f_cat = False

    c_titulo, c_filtrar, c_inserir, c_margem = st.columns([5, 1.5, 1.5, 3])
    with c_titulo: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>folder</span> Cadastro de Categorias</h3>", unsafe_allow_html=True)
    with c_filtrar:
        if st.button("Filtrar", icon=":material/search:", use_container_width=True):
            st.session_state.show_f_cat = not st.session_state.show_f_cat; st.rerun()
    with c_inserir:
        if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True): modal_inclusao_categoria()

    if st.session_state.show_f_cat:
        with st.container(border=True):
            cp, cn, cb = st.columns([5, 3, 2])
            v_pesq = cp.text_input("Pesquisar nome da categoria:", value=st.session_state.f_cat_pesq)
            op_nat = ["Todas as naturezas", "Receita", "Despesa"]
            v_nat = cn.selectbox("Natureza:", op_nat, index=op_nat.index(st.session_state.f_cat_nat))
            cb.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if cb.button("Pesquisar", icon=":material/search:", use_container_width=True):
                st.session_state.f_cat_pesq, st.session_state.f_cat_nat = v_pesq, v_nat; st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)

    df = carregar_dados_categorias(st.session_state.f_cat_pesq, st.session_state.f_cat_nat)
    st.markdown('<div class="cabecalho-grid"><div style="display: flex;"><div style="flex: 5;">Nome da categoria</div><div style="flex: 2; text-align: center;">Natureza</div><div style="flex: 2; text-align: center;">Ações</div></div></div>', unsafe_allow_html=True)

    if df.empty:
        st.info("Nenhuma categoria encontrada na base de dados para este filtro.")
    else:
        with st.container():
            st.markdown("<div class='btn-acao-grid'>", unsafe_allow_html=True)
            for _, row in df.iterrows():
                id_cat, nome, nat = row['id'], row['Nome da categoria'], row['Natureza']
                c1, c2, c3, c4, c5 = st.columns([5, 2, 0.66, 0.66, 0.68], vertical_alignment="center")
                c1.markdown(f"<span style='font-weight: 600; color: #1a2a40; font-size: 15px; padding-left: 10px;'>{nome}</span>", unsafe_allow_html=True)
                badge = "badge-receita" if nat == "Receita" else "badge-despesa"
                c2.markdown(f"<div style='text-align: center;'><span class='{badge}'>{nat}</span></div>", unsafe_allow_html=True)
                if c3.button(" ", icon=":material/edit:", key=f"ec_{id_cat}", help="Editar", use_container_width=True): modal_alteracao_categoria(int(id_cat), nome, nat)
                if c4.button(" ", icon=":material/content_copy:", key=f"dc_{id_cat}", help="Duplicar", use_container_width=True): modal_duplicacao_categoria(nome, nat)
                if c5.button(" ", icon=":material/delete:", key=f"xc_{id_cat}", help="Excluir", use_container_width=True): modal_exclusao_categoria(int(id_cat), nome)
                st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# MÓDULO: CLASSIFICAÇÕES
# ==========================================
def carregar_dados_classificacoes(pesquisa="", categoria_filtro="Todas as Categorias"):
    query = "SELECT cl.id, cl.nome, c.nome as cat_nome, cl.id_categoria FROM classificacoes cl JOIN categorias c ON cl.id_categoria = c.id WHERE 1=1"
    params = []
    if pesquisa:
        query += " AND cl.nome ILIKE %s"
        params.append(f"%{pesquisa}%")
    if categoria_filtro != "Todas as Categorias":
        query += " AND c.nome = %s"
        params.append(categoria_filtro)
    query += " ORDER BY cl.id DESC"
    return db_query(query, tuple(params))

@st.dialog(":material/account_tree: Nova classificação")
def modal_inclusao_classificacao():
    cats = db_query("SELECT id, nome FROM categorias ORDER BY nome")
    if cats.empty: st.warning("Cadastre uma categoria primeiro."); return
    
    nome = st.text_input("Nome da classificação:", placeholder="Ex: Despesas da residência...", key="inc_nome_class")
    cat_pai = st.selectbox("Vincular à categoria pai:", options=cats.values.tolist(), format_func=lambda x: x[1], key="inc_cat_pai")
    st.write("")
    
    msg_placeholder = st.empty()
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2: 
        if st.button("Cancelar", type="secondary", use_container_width=True, key="btn_canc_cl"): st.rerun()
    with c3: 
        if st.button("Salvar", type="primary", use_container_width=True, key="btn_salv_cl"):
            if nome.strip() and cat_pai:
                with st.spinner("Processando..."):
                    db_query("INSERT INTO classificacoes (nome, id_categoria) VALUES (%s, %s)", (nome, int(cat_pai[0])), is_select=False)
                    time.sleep(0.4)
                msg_placeholder.success(f"Classificação '{nome}' registada com sucesso!")
                time.sleep(1); st.rerun()
            else:
                msg_placeholder.error("O campo de nome é obrigatório.")

@st.dialog(":material/account_tree: Editar classificação")
def modal_editar_classificacao(id_class, nome_atual, id_cat_atual):
    nome = st.text_input("Nome da classificação:", value=nome_atual, key=f"ed_nom_cl_{id_class}")
    cats = db_query("SELECT id, nome FROM categorias ORDER BY nome")
    cat_list = cats.values.tolist(); idx_cat = next((i for i, c in enumerate(cat_list) if c[0] == id_cat_atual), 0)
    cat_pai = st.selectbox("Vincular à categoria pai:", options=cat_list, format_func=lambda x: x[1], index=idx_cat, key=f"ed_cat_cl_{id_class}")
    st.write("")
    
    msg_placeholder = st.empty()
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Cancelar", type="secondary", use_container_width=True, key=f"ed_canc_cl_{id_class}"): st.rerun()
    with c3:
        if st.button("Salvar", type="primary", use_container_width=True, key=f"ed_salv_cl_{id_class}"):
            if nome.strip():
                with st.spinner("Processando..."):
                    db_query("UPDATE classificacoes SET nome = %s, id_categoria = %s WHERE id = %s", (nome, int(cat_pai[0]), int(id_class)), is_select=False)
                    time.sleep(0.4)
                msg_placeholder.success("Classificação atualizada com sucesso!")
                time.sleep(1); st.rerun()
            else: 
                msg_placeholder.error("O campo de nome é obrigatório.")

@st.dialog(":material/account_tree: Excluir classificação")
def modal_excluir_classificacao(id_class, nome):
    df_vinculos = db_query("SELECT COUNT(id) as total FROM eventos WHERE id_classificacao = %s", (id_class,))
    total_vinculos = int(df_vinculos.iloc[0]['total'])

    if total_vinculos > 0:
        html_bloqueio = f"""
        <div style="border-left: 5px solid #e76f51; background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #e9ecef;">
            <div style="display: flex; align-items: center; gap: 8px; color: #e76f51; font-weight: bold; font-size: 19px; margin-bottom: 12px;">
                <span class="material-symbols-rounded" style="font-size: 26px;">block</span> Ação Bloqueada
            </div>
            <div style="color: #1a2a40; font-size: 17px; line-height: 1.6;">
                Não é possível excluir a classificação <b style="color: #e76f51;">{nome}</b>.<br>
                <strong>Motivo:</strong> Existem <b>{total_vinculos}</b> evento(s) vinculado(s) a esta classificação.<br><br>
                <span style="color: #457b9d;"><i>Por favor, altere ou exclua os eventos dependentes antes de tentar novamente.</i></span>
            </div>
        </div>
        """
        st.markdown(html_bloqueio, unsafe_allow_html=True)
        c1, c2 = st.columns([6, 4])
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True, key=f"exc_cl_fechar_{id_class}"): st.rerun()
    else:
        html_confirmacao = f"""
        <div style="border-left: 5px solid #457b9d; background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #e9ecef;">
            <div style="color: #1a2a40; font-size: 17px; line-height: 1.6;">
                Tem a certeza que deseja excluir a classificação <b>{nome}</b>?<br>
                <span style="color: #e76f51;"><i>Esta ação removerá o registo permanentemente.</i></span>
            </div>
        </div>
        """
        st.markdown(html_confirmacao, unsafe_allow_html=True)
        msg_placeholder = st.empty()
        c1, c2, c3 = st.columns([2, 3, 3])
        with c2:
            if st.button("Cancelar", type="secondary", use_container_width=True, key=f"del_canc_cl_{id_class}"): st.rerun()
        with c3:
            if st.button("Confirmar exclusão", type="primary", use_container_width=True, key=f"del_conf_cl_{id_class}"):
                with st.spinner("Processando..."):
                    db_query("DELETE FROM classificacoes WHERE id = %s", (int(id_class),), is_select=False)
                    time.sleep(0.4)
                msg_placeholder.success("Classificação excluída com sucesso!")
                time.sleep(1); st.rerun()

@st.dialog(":material/account_tree: Duplicar classificação")
def modal_duplicar_classificacao(nome_atual, id_cat_atual):
    nome = st.text_input("Novo nome (cópia):", value=f"{nome_atual} (Cópia)", key=f"dup_nom_cl_{nome_atual}")
    cats = db_query("SELECT id, nome FROM categorias ORDER BY nome")
    cat_list = cats.values.tolist(); idx_cat = next((i for i, c in enumerate(cat_list) if c[0] == id_cat_atual), 0)
    cat_pai = st.selectbox("Vincular à categoria pai:", options=cat_list, format_func=lambda x: x[1], index=idx_cat, key=f"dup_cat_cl_{nome_atual}")
    st.write("")
    
    msg_placeholder = st.empty()
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Cancelar", type="secondary", use_container_width=True, key=f"dup_canc_cl_{nome_atual}"): st.rerun()
    with c3:
        if st.button("Salvar", type="primary", use_container_width=True, key=f"dup_salv_cl_{nome_atual}"):
            if nome.strip():
                with st.spinner("Processando..."):
                    db_query("INSERT INTO classificacoes (nome, id_categoria) VALUES (%s, %s)", (nome, int(cat_pai[0])), is_select=False)
                    time.sleep(0.4)
                msg_placeholder.success("Classificação duplicada com sucesso!")
                time.sleep(1); st.rerun()
            else: 
                msg_placeholder.error("O campo de nome é obrigatório.")

def render_classificacoes():
    if 'f_cl_pesq' not in st.session_state: st.session_state.f_cl_pesq = ""
    if 'f_cl_cat' not in st.session_state: st.session_state.f_cl_cat = "Todas as Categorias"
    if 'show_f_cl' not in st.session_state: st.session_state.show_f_cl = False
    
    c_titulo, c_filtrar, c_inserir, c_margem = st.columns([5, 1.5, 1.5, 3])
    with c_titulo: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>account_tree</span> Cadastro de Classificações</h3>", unsafe_allow_html=True)
    with c_filtrar:
        if st.button("Filtrar", icon=":material/search:", use_container_width=True, key="btn_f_cl"):
            st.session_state.show_f_cl = not st.session_state.show_f_cl; st.rerun()
    with c_inserir:
        if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True, key="btn_ins_cl"): modal_inclusao_classificacao()
    
    if st.session_state.show_f_cl:
        with st.container(border=True):
            cp, cc, cb = st.columns([5, 3, 2])
            v_p = cp.text_input("Pesquisar classificação:", value=st.session_state.f_cl_pesq, key="inp_f_cl_p")
            cats_filtro = db_query("SELECT nome FROM categorias ORDER BY nome")
            lista_filtro = ["Todas as Categorias"] + cats_filtro['nome'].tolist()
            idx_f = lista_filtro.index(st.session_state.f_cl_cat) if st.session_state.f_cl_cat in lista_filtro else 0
            v_c = cc.selectbox("Categoria (Grupo):", options=lista_filtro, index=idx_f, key="inp_f_cl_c")
            cb.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if cb.button("Pesquisar", icon=":material/search:", use_container_width=True, key="btn_f_run_cl"):
                st.session_state.f_cl_pesq, st.session_state.f_cl_cat = v_p, v_c; st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)

    df = carregar_dados_classificacoes(st.session_state.f_cl_pesq, st.session_state.f_cl_cat)
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
                if c3.button(" ", icon=":material/edit:", key=f"ed_cl_{row['id']}", help="Editar", use_container_width=True): modal_editar_classificacao(row['id'], row['nome'], row['id_categoria'])
                if c4.button(" ", icon=":material/content_copy:", key=f"cp_cl_{row['id']}", help="Duplicar", use_container_width=True): modal_duplicar_classificacao(row['nome'], row['id_categoria'])
                if c5.button(" ", icon=":material/delete:", key=f"del_cl_{row['id']}", help="Excluir", use_container_width=True): modal_excluir_classificacao(row['id'], row['nome'])
                st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# MÓDULO: EVENTOS
# ==========================================
def carregar_dados_eventos(pesquisa="", classificacao_filtro="Todas as Classificações"):
    query = "SELECT e.id, e.nome, c.nome as class_nome, e.id_classificacao FROM eventos e JOIN classificacoes c ON e.id_classificacao = c.id WHERE 1=1"
    params = []
    if pesquisa:
        query += " AND e.nome ILIKE %s"
        params.append(f"%{pesquisa}%")
    if classificacao_filtro != "Todas as Classificações":
        query += " AND c.nome = %s"
        params.append(classificacao_filtro)
    query += " ORDER BY e.id DESC"
    return db_query(query, tuple(params))

@st.dialog(":material/sell: Novo evento")
def modal_inclusao_evento():
    classes = db_query("SELECT id, nome FROM classificacoes ORDER BY nome")
    if classes.empty: st.warning("Cadastre uma classificação primeiro."); return
    
    nome = st.text_input("Nome do evento (Credor/Devedor):", placeholder="Ex: Supermercado, Salário...", key="inc_nome_ev")
    class_pai = st.selectbox("Vincular à classificação (Grupo Macro):", options=classes.values.tolist(), format_func=lambda x: x[1], key="inc_class_pai")
    st.write("")
    
    msg_placeholder = st.empty()
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2: 
        if st.button("Cancelar", type="secondary", use_container_width=True, key="btn_canc_ev"): st.rerun()
    with c3: 
        if st.button("Salvar", type="primary", use_container_width=True, key="btn_salv_ev"):
            if nome.strip() and class_pai:
                with st.spinner("Processando..."):
                    db_query("INSERT INTO eventos (nome, id_classificacao) VALUES (%s, %s)", (nome, int(class_pai[0])), is_select=False)
                    time.sleep(0.4)
                msg_placeholder.success(f"Evento '{nome}' registado com sucesso!")
                time.sleep(1); st.rerun()
            else: 
                msg_placeholder.error("O campo de nome é obrigatório.")

@st.dialog(":material/sell: Editar evento")
def modal_editar_evento(id_evento, nome_atual, id_class_atual):
    nome = st.text_input("Nome do evento (Credor/Devedor):", value=nome_atual, key=f"ed_nom_ev_{id_evento}")
    classes = db_query("SELECT id, nome FROM classificacoes ORDER BY nome")
    class_list = classes.values.tolist(); idx_class = next((i for i, c in enumerate(class_list) if c[0] == id_class_atual), 0)
    class_pai = st.selectbox("Vincular à classificação (Grupo Macro):", options=class_list, format_func=lambda x: x[1], index=idx_class, key=f"ed_class_ev_{id_evento}")
    st.write("")
    
    msg_placeholder = st.empty()
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Cancelar", type="secondary", use_container_width=True, key=f"ed_canc_ev_{id_evento}"): st.rerun()
    with c3:
        if st.button("Salvar", type="primary", use_container_width=True, key=f"ed_salv_ev_{id_evento}"):
            if nome.strip():
                with st.spinner("Processando..."):
                    db_query("UPDATE eventos SET nome = %s, id_classificacao = %s WHERE id = %s", (nome, int(class_pai[0]), int(id_evento)), is_select=False)
                    time.sleep(0.4)
                msg_placeholder.success("Evento atualizado com sucesso!")
                time.sleep(1); st.rerun()
            else: 
                msg_placeholder.error("O campo de nome é obrigatório.")

@st.dialog(":material/sell: Excluir evento")
def modal_excluir_evento(id_evento, nome):
    html_confirmacao = f"""
    <div style="border-left: 5px solid #457b9d; background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #e9ecef;">
        <div style="color: #1a2a40; font-size: 17px; line-height: 1.6;">
            Tem a certeza que deseja excluir o evento <b>{nome}</b>?<br>
            <span style="color: #e76f51;"><i>Esta ação removerá o registo permanentemente.</i></span>
        </div>
    </div>
    """
    st.markdown(html_confirmacao, unsafe_allow_html=True)
    msg_placeholder = st.empty()
    c1, c2, c3 = st.columns([2, 3, 3])
    with c2:
        if st.button("Cancelar", type="secondary", use_container_width=True, key=f"del_canc_ev_{id_evento}"): st.rerun()
    with c3:
        if st.button("Confirmar exclusão", type="primary", use_container_width=True, key=f"del_conf_ev_{id_evento}"):
            with st.spinner("Processando..."):
                db_query("DELETE FROM eventos WHERE id = %s", (int(id_evento),), is_select=False)
                time.sleep(0.4)
            msg_placeholder.success("Evento excluído com sucesso!")
            time.sleep(1); st.rerun()

@st.dialog(":material/sell: Duplicar evento")
def modal_duplicar_evento(nome_atual, id_class_atual):
    nome = st.text_input("Novo nome (cópia):", value=f"{nome_atual} (Cópia)", key=f"dup_nom_ev_{nome_atual}")
    classes = db_query("SELECT id, nome FROM classificacoes ORDER BY nome")
    class_list = classes.values.tolist(); idx_class = next((i for i, c in enumerate(class_list) if c[0] == id_class_atual), 0)
    class_pai = st.selectbox("Vincular à classificação (Grupo Macro):", options=class_list, format_func=lambda x: x[1], index=idx_class, key=f"dup_class_ev_{nome_atual}")
    st.write("")
    
    msg_placeholder = st.empty()
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Cancelar", type="secondary", use_container_width=True, key=f"dup_canc_ev_{nome_atual}"): st.rerun()
    with c3:
        if st.button("Salvar", type="primary", use_container_width=True, key=f"dup_salv_ev_{nome_atual}"):
            if nome.strip():
                with st.spinner("Processando..."):
                    db_query("INSERT INTO eventos (nome, id_classificacao) VALUES (%s, %s)", (nome, int(class_pai[0])), is_select=False)
                    time.sleep(0.4)
                msg_placeholder.success("Evento duplicado com sucesso!")
                time.sleep(1); st.rerun()
            else: 
                msg_placeholder.error("O campo de nome é obrigatório.")

def render_eventos():
    if 'f_ev_pesq' not in st.session_state: st.session_state.f_ev_pesq = ""
    if 'f_ev_class' not in st.session_state: st.session_state.f_ev_class = "Todas as Classificações"
    if 'show_f_ev' not in st.session_state: st.session_state.show_f_ev = False
    
    c_titulo, c_filtrar, c_inserir, c_margem = st.columns([5, 1.5, 1.5, 3])
    with c_titulo: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>sell</span> Cadastro de Eventos</h3>", unsafe_allow_html=True)
    with c_filtrar:
        if st.button("Filtrar", icon=":material/search:", use_container_width=True, key="btn_f_ev"):
            st.session_state.show_f_ev = not st.session_state.show_f_ev; st.rerun()
    with c_inserir:
        if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True, key="btn_ins_ev"): modal_inclusao_evento()
    
    if st.session_state.show_f_ev:
        with st.container(border=True):
            cp, cc, cb = st.columns([5, 3, 2])
            v_p = cp.text_input("Pesquisar nome do evento:", value=st.session_state.f_ev_pesq, key="inp_f_ev_p")
            classes_filtro = db_query("SELECT nome FROM classificacoes ORDER BY nome")
            lista_filtro = ["Todas as Classificações"] + classes_filtro['nome'].tolist()
            idx_f = lista_filtro.index(st.session_state.f_ev_class) if st.session_state.f_ev_class in lista_filtro else 0
            v_c = cc.selectbox("Classificação Vinculada:", options=lista_filtro, index=idx_f, key="inp_f_ev_c")
            cb.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if cb.button("Pesquisar", icon=":material/search:", use_container_width=True, key="btn_f_run_ev"):
                st.session_state.f_ev_pesq, st.session_state.f_ev_class = v_p, v_c; st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)

    df = carregar_dados_eventos(st.session_state.f_ev_pesq, st.session_state.f_ev_class)
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
                if c3.button(" ", icon=":material/edit:", key=f"ed_ev_{row['id']}", help="Editar", use_container_width=True): modal_editar_evento(row['id'], row['nome'], row['id_classificacao'])
                if c4.button(" ", icon=":material/content_copy:", key=f"cp_ev_{row['id']}", help="Duplicar", use_container_width=True): modal_duplicar_evento(row['nome'], row['id_classificacao'])
                if c5.button(" ", icon=":material/delete:", key=f"del_ev_{row['id']}", help="Excluir", use_container_width=True): modal_excluir_evento(row['id'], row['nome'])
                st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# EXECUÇÃO DO PROJETO
# ==========================================
modulo_atual = st.session_state.modulo_ativo

if modulo_atual == "Categorias":
    render_categorias()
elif modulo_atual == "Classificações":
    render_classificacoes()
elif modulo_atual == "Eventos":
    render_eventos()