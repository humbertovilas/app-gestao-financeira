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
# INÍCIO DO MÓDULO: INFRAESTRUTURA DE DADOS (POSTGRESQL NEON DB)
# ==========================================
def get_db_connection():
    # Conecta usando a chave secreta guardada no secrets.toml ou no servidor em nuvem
    return psycopg2.connect(st.secrets["DATABASE_URL"])

def inicializar_banco():
    conn = get_db_connection()
    cursor = conn.cursor()
    # PostgreSQL usa SERIAL em vez de AUTOINCREMENT
    cursor.execute('''CREATE TABLE IF NOT EXISTS categorias 
                      (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, tipo TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS classificacoes 
                      (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, id_categoria INTEGER NOT NULL, 
                       FOREIGN KEY (id_categoria) REFERENCES categorias (id))''')
    conn.commit()
    conn.close()

try:
    inicializar_banco()
except Exception as e:
    st.error("Erro ao conectar no banco de dados em nuvem. Verifique o secrets.toml.")
    st.stop()

# ==========================================
# INÍCIO DO MÓDULO: NAVEGAÇÃO WEB (ENTER PARA TAB) E MENSAGENS
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
    if st.button("Eventos", icon=":material/sell:", use_container_width=True): modal_em_construcao("Eventos")
    
    if st.button("Classificações", type="primary" if st.session_state.modulo_ativo == "Classificações" else "secondary", icon=":material/account_tree:", use_container_width=True):
        st.session_state.modulo_ativo = "Classificações"
        st.rerun()
        
    if st.button("Categorias", type="primary" if st.session_state.modulo_ativo == "Categorias" else "secondary", icon=":material/folder:", use_container_width=True):
        st.session_state.modulo_ativo = "Categorias"
        st.rerun()

# ==========================================
# FUNÇÕES DE APOIO (DATABASE POSTGRESQL)
# ==========================================
def db_query(query, params=(), is_select=True):
    conn = get_db_connection()
    if is_select:
        # PostgreSQL usa %s como marcador de parâmetro, não mais ?
        res = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return res
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

# ==========================================
# MÓDULO: CATEGORIAS
# ==========================================
def carregar_dados(pesquisa="", natureza="Todas as naturezas"):
    query = "SELECT id, nome as \"Nome da categoria\", tipo as \"Natureza\" FROM categorias WHERE 1=1"
    params = []
    if pesquisa:
        # ILIKE no PostgreSQL ignora maiúsculas e minúsculas
        query += " AND nome ILIKE %s"
        params.append(f"%{pesquisa}%")
    if natureza == "Receita": query += " AND tipo = 'Receita'"
    elif natureza == "Despesa": query += " AND tipo = 'Despesa'"
    
    # Adicionando ordenação padrão
    query += " ORDER BY id DESC"
    return db_query(query, tuple(params))

def salvar_categoria(nome, tipo):
    db_query("INSERT INTO categorias (nome, tipo) VALUES (%s, %s)", (nome, tipo), is_select=False)

def acao_salvar_novo():
    nome = st.session_state.inc_nome
    tipo = st.session_state.inc_tipo
    if nome.strip():
        salvar_categoria(nome, tipo)
        st.session_state.inc_nome = ""
        st.session_state.inc_tipo = "Receita"
        st.session_state.msg_aviso_inclusao = ("success", f"Categoria '{nome}' registada com sucesso!")
    else:
        st.session_state.msg_aviso_inclusao = ("error", "O campo de nome é obrigatório.")

@st.dialog(":material/folder: Nova categoria")
def modal_inclusao():
    if "inc_nome" not in st.session_state: st.session_state.inc_nome = ""
    if "inc_tipo" not in st.session_state: st.session_state.inc_tipo = "Receita"

    input_nome = st.text_input("Nome da categoria:", placeholder="Ex: Alimentação, Salário...", key="inc_nome")
    input_tipo = st.selectbox("Natureza:", ["Receita", "Despesa"], key="inc_tipo")
    st.write("")
    
    if "msg_aviso_inclusao" in st.session_state:
        tipo_msg, texto = st.session_state.msg_aviso_inclusao
        if tipo_msg == "success": st.success(texto)
        else: st.error(texto)
        del st.session_state.msg_aviso_inclusao
        injeção_js_alerta_3s()
        
    col_vazia, col_canc, col_salv = st.columns([4, 3, 3])
    with col_canc:
        if st.button("Cancelar", type="secondary", use_container_width=True, key="inc_btn_canc"): st.rerun()
    with col_salv:
        st.button("Salvar", type="primary", use_container_width=True, key="inc_btn_salv", on_click=acao_salvar_novo)

def alterar_categoria(id_cat, novo_nome, novo_tipo):
    db_query("UPDATE categorias SET nome = %s, tipo = %s WHERE id = %s", (novo_nome, novo_tipo, id_cat), is_select=False)

@st.dialog(":material/folder: Editar categoria")
def modal_alteracao(id_cat, nome_atual, tipo_atual):
    input_nome = st.text_input("Nome da categoria:", value=nome_atual, key=f"alt_nome_{id_cat}")
    idx_tipo = 0 if tipo_atual == "Receita" else 1
    input_tipo = st.selectbox("Natureza:", ["Receita", "Despesa"], index=idx_tipo, key=f"alt_tipo_{id_cat}")
    st.write("")
    
    msg_placeholder = st.empty()
    
    col_vazia, col_canc, col_salv = st.columns([4, 3, 3])
    with col_canc:
        if st.button("Cancelar", type="secondary", use_container_width=True, key=f"alt_btn_canc_{id_cat}"): st.rerun()
    with col_salv:
        if st.button("Salvar", type="primary", use_container_width=True, key=f"alt_btn_salv_{id_cat}"):
            if input_nome.strip():
                alterar_categoria(int(id_cat), input_nome, input_tipo)
                msg_placeholder.success("Categoria atualizada com sucesso!")
                time.sleep(1); st.rerun()
            else: 
                msg_placeholder.error("O campo de nome é obrigatório.")

def excluir_categoria(id_cat):
    db_query("DELETE FROM categorias WHERE id = %s", (id_cat,), is_select=False)

@st.dialog(":material/folder: Excluir categoria")
def modal_exclusao(id_cat, nome_atual):
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
        
        col_vazia, col_btn = st.columns([6, 4])
        with col_btn:
            if st.button("Fechar", type="secondary", use_container_width=True, key=f"exc_btn_fechar_{id_cat}"):
                st.rerun()
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
        
        col_vazia, col_canc, col_conf = st.columns([2, 3, 3])
        with col_canc:
            if st.button("Cancelar", type="secondary", use_container_width=True, key=f"exc_btn_canc_{id_cat}"): st.rerun()
        with col_conf:
            if st.button("Confirmar exclusão", type="primary", use_container_width=True, key=f"exc_btn_conf_{id_cat}"):
                excluir_categoria(int(id_cat))
                msg_placeholder.success("Categoria excluída com sucesso!")
                time.sleep(1); st.rerun()

@st.dialog(":material/folder: Duplicar categoria")
def modal_duplicacao(nome_atual, tipo_atual):
    input_nome = st.text_input("Novo nome da categoria (cópia):", value=f"{nome_atual} (Cópia)", key=f"dup_nome_{nome_atual}")
    idx_tipo = 0 if tipo_atual == "Receita" else 1
    input_tipo = st.selectbox("Natureza:", ["Receita", "Despesa"], index=idx_tipo, key=f"dup_tipo_{nome_atual}")
    st.write("")
    
    msg_placeholder = st.empty()
    
    col_vazia, col_canc, col_salv = st.columns([4, 3, 3])
    with col_canc:
        if st.button("Cancelar", type="secondary", use_container_width=True, key=f"dup_btn_canc_{nome_atual}"): st.rerun()
    with col_salv:
        if st.button("Salvar", type="primary", use_container_width=True, key=f"dup_btn_salv_{nome_atual}"):
            if input_nome.strip():
                salvar_categoria(input_nome, input_tipo)
                msg_placeholder.success("Categoria duplicada com sucesso!")
                time.sleep(1); st.rerun()
            else: 
                msg_placeholder.error("O campo de nome é obrigatório.")

def render_categorias():
    if 'filtro_pesquisa' not in st.session_state: st.session_state.filtro_pesquisa = ""
    if 'filtro_natureza' not in st.session_state: st.session_state.filtro_natureza = "Todas as naturezas"
    if 'mostrar_filtro' not in st.session_state: st.session_state.mostrar_filtro = False

    col_titulo, col_filtrar, col_inserir, col_margem_dir = st.columns([5, 1.5, 1.5, 3])
    
    with col_titulo:
        st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>folder</span> Cadastro de Categorias</h3>", unsafe_allow_html=True)
        
    with col_filtrar:
        if st.button("Filtrar", icon=":material/search:", use_container_width=True):
            st.session_state.mostrar_filtro = not st.session_state.mostrar_filtro
            st.rerun()
            
    with col_inserir:
        if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True): modal_inclusao()

    if st.session_state.mostrar_filtro:
        with st.container(border=True):
            c_pesquisa, c_natureza, c_processar = st.columns([5, 3, 2])
            with c_pesquisa:
                val_pesquisa = st.text_input("Pesquisar nome da categoria:", value=st.session_state.filtro_pesquisa, placeholder="Digite para buscar...")
            with c_natureza:
                opcoes_natureza = ["Todas as naturezas", "Receita", "Despesa"]
                val_natureza = st.selectbox("Natureza:", opcoes_natureza, index=opcoes_natureza.index(st.session_state.filtro_natureza))
            with c_processar:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("Pesquisar", icon=":material/search:", use_container_width=True):
                    st.session_state.filtro_pesquisa = val_pesquisa
                    st.session_state.filtro_natureza = val_natureza
                    st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)

    df_resultado = carregar_dados(st.session_state.filtro_pesquisa, st.session_state.filtro_natureza)
    st.markdown("""
        <div class="cabecalho-grid">
            <div style="display: flex;">
                <div style="flex: 5;">Nome da categoria</div>
                <div style="flex: 2; text-align: center;">Natureza</div>
                <div style="flex: 2; text-align: center;">Ações</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if df_resultado.empty:
        st.info("Nenhuma categoria encontrada na base de dados para este filtro.")
    else:
        with st.container():
            st.markdown("<div class='btn-acao-grid'>", unsafe_allow_html=True)
            for index, row in df_resultado.iterrows():
                id_cat = row['id']
                nome_cat = row['Nome da categoria']
                tipo_cat = row['Natureza']
                col_nome, col_nat, col_edit, col_dup, col_del = st.columns([5, 2, 0.66, 0.66, 0.68], vertical_alignment="center")
                with col_nome: st.markdown(f"<span style='font-weight: 600; color: #1a2a40; font-size: 15px; padding-left: 10px;'>{nome_cat}</span>", unsafe_allow_html=True)
                with col_nat:
                    classe_badge = "badge-receita" if tipo_cat == "Receita" else "badge-despesa"
                    st.markdown(f"<div style='text-align: center;'><span class='{classe_badge}'>{tipo_cat}</span></div>", unsafe_allow_html=True)
                with col_edit:
                    if st.button(" ", icon=":material/edit:", key=f"edit_{id_cat}", help="Editar categoria", use_container_width=True):
                        modal_alteracao(int(id_cat), nome_cat, tipo_cat)
                with col_dup:
                    if st.button(" ", icon=":material/content_copy:", key=f"dup_{id_cat}", help="Duplicar categoria", use_container_width=True):
                        modal_duplicacao(nome_cat, tipo_cat)
                with col_del:
                    if st.button(" ", icon=":material/delete:", key=f"del_{id_cat}", help="Excluir categoria", use_container_width=True):
                        modal_exclusao(int(id_cat), nome_cat)
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

def acao_salvar_novo_classificacao():
    nome = st.session_state.inc_nome_class
    if nome.strip() and st.session_state.inc_cat_pai:
        id_cat = st.session_state.inc_cat_pai[0]
        db_query("INSERT INTO classificacoes (nome, id_categoria) VALUES (%s, %s)", (nome, int(id_cat)), is_select=False)
        st.session_state.inc_nome_class = ""
        st.session_state.msg_class = ("success", f"Classificação '{nome}' registada com sucesso!")
    else: st.session_state.msg_class = ("error", "O campo de nome é obrigatório.")

@st.dialog(":material/account_tree: Nova classificação")
def modal_inclusao_classificacao():
    cats = db_query("SELECT id, nome FROM categorias ORDER BY nome")
    if cats.empty: st.warning("Cadastre uma categoria primeiro."); return
    st.text_input("Nome da classificação:", placeholder="Ex: Despesas da residência...", key="inc_nome_class")
    st.selectbox("Vincular à categoria pai:", options=cats.values.tolist(), format_func=lambda x: x[1], key="inc_cat_pai")
    if "msg_class" in st.session_state:
        if st.session_state.msg_class[0] == "success": st.success(st.session_state.msg_class[1])
        else: st.error(st.session_state.msg_class[1])
        del st.session_state.msg_class; injeção_js_alerta_3s()
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2: 
        if st.button("Cancelar", type="secondary", use_container_width=True, key="btn_canc_cl"): st.rerun()
    with c3: 
        st.button("Salvar", type="primary", use_container_width=True, on_click=acao_salvar_novo_classificacao, key="btn_salv_cl")

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
                db_query("UPDATE classificacoes SET nome = %s, id_categoria = %s WHERE id = %s", (nome, int(cat_pai[0]), int(id_class)), is_select=False)
                msg_placeholder.success("Classificação atualizada com sucesso!")
                time.sleep(1); st.rerun()
            else:
                msg_placeholder.error("O campo de nome é obrigatório.")

@st.dialog(":material/account_tree: Excluir classificação")
def modal_excluir_classificacao(id_class, nome):
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
    
    col_vazia, col_canc, col_conf = st.columns([2, 3, 3])
    with col_canc:
        if st.button("Cancelar", type="secondary", use_container_width=True, key=f"del_canc_cl_{id_class}"): st.rerun()
    with col_conf:
        if st.button("Confirmar exclusão", type="primary", use_container_width=True, key=f"del_conf_cl_{id_class}"):
            db_query("DELETE FROM classificacoes WHERE id = %s", (int(id_class),), is_select=False)
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
                db_query("INSERT INTO classificacoes (nome, id_categoria) VALUES (%s, %s)", (nome, int(cat_pai[0])), is_select=False)
                msg_placeholder.success("Classificação duplicada com sucesso!")
                time.sleep(1); st.rerun()
            else:
                msg_placeholder.error("O campo de nome é obrigatório.")

def render_classificacoes():
    if 'f_cl_pesq' not in st.session_state: st.session_state.f_cl_pesq = ""
    if 'f_cl_cat' not in st.session_state: st.session_state.f_cl_cat = "Todas as Categorias"
    if 'show_f_cl' not in st.session_state: st.session_state.show_f_cl = False
    
    col_titulo, col_filtrar, col_inserir, col_margem_dir = st.columns([5, 1.5, 1.5, 3])
    
    with col_titulo:
        st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>account_tree</span> Cadastro de Classificações</h3>", unsafe_allow_html=True)
        
    with col_filtrar:
        if st.button("Filtrar", icon=":material/search:", use_container_width=True, key="btn_f_cl"):
            st.session_state.show_f_cl = not st.session_state.show_f_cl; st.rerun()
            
    with col_inserir:
        if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True, key="btn_ins_cl"): modal_inclusao_classificacao()
    
    if st.session_state.show_f_cl:
        with st.container(border=True):
            cp, cc, cb = st.columns([5, 3, 2])
            v_p = cp.text_input("Pesquisar classificação:", value=st.session_state.f_cl_pesq, key="inp_f_cl_p")
            
            cats_filtro = db_query("SELECT nome FROM categorias ORDER BY nome")
            lista_filtro = ["Todas as Categorias"] + cats_filtro['nome'].tolist()
            idx_f = lista_filtro.index(st.session_state.f_cl_cat) if st.session_state.f_cl_cat in lista_filtro else 0
            v_c = cc.selectbox("Categoria (Grupo):", options=lista_filtro, index=idx_f, key="inp_f_cl_c")
            
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
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
                if c3.button(" ", icon=":material/edit:", key=f"ed_cl_{row['id']}", help="Editar classificação", use_container_width=True): modal_editar_classificacao(row['id'], row['nome'], row['id_categoria'])
                if c4.button(" ", icon=":material/content_copy:", key=f"cp_cl_{row['id']}", help="Duplicar classificação", use_container_width=True): modal_duplicar_classificacao(row['nome'], row['id_categoria'])
                if c5.button(" ", icon=":material/delete:", key=f"del_cl_{row['id']}", help="Excluir classificação", use_container_width=True): modal_excluir_classificacao(row['id'], row['nome'])
                st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# EXECUÇÃO DO PROJETO
# ==========================================
modulo_atual = st.session_state.modulo_ativo

if modulo_atual == "Categorias":
    render_categorias()
else:
    render_classificacoes()