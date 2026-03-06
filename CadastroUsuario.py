import streamlit as st
import hashlib
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

# Proteção de rota: expulsa quem tentar acessar diretamente a URL sem ser admin
if st.session_state.get("perfil_logado") != "Administrador":
    st.error("Acesso negado. Apenas administradores podem acessar esta página.")
    st.stop()

UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

# ==========================================
# REGRAS DE NEGÓCIO E CONSULTA
# ==========================================
def carregar_dados(pesquisa="", perfil_filtro="Todos os perfis"):
    query = "SELECT id, nome, email, perfil FROM usuarios WHERE ativo = TRUE"
    params = []
    if pesquisa:
        query += " AND (nome ILIKE %s OR email ILIKE %s)"
        params.extend([f"%{pesquisa}%", f"%{pesquisa}%"])
    if perfil_filtro != "Todos os perfis":
        query += " AND perfil = %s"
        params.append(perfil_filtro)
    query += " ORDER BY nome ASC"
    return GerenciadorBanco.executar_query(query, tuple(params))

def gerar_hash(senha):
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

# ==========================================
# CALLBACKS (AÇÕES DE GRAVAÇÃO)
# ==========================================
def callback_inclusao():
    nome = st.session_state.get(f"inc_nome_u_{st.session_state.form_reset}", "")
    email = st.session_state.get(f"inc_email_u_{st.session_state.form_reset}", "")
    senha = st.session_state.get(f"inc_senha_u_{st.session_state.form_reset}", "")
    perfil = st.session_state.get(f"inc_perfil_u_{st.session_state.form_reset}", "Padrão")
    
    if nome.strip() and email.strip() and senha.strip():
        try:
            GerenciadorBanco.executar_query("INSERT INTO usuarios (nome, email, senha, perfil, ativo) VALUES (%s, %s, %s, %s, TRUE)", 
                                            (nome, email, gerar_hash(senha), perfil), is_select=False)
            st.session_state.msg_sucesso = True
            st.session_state.form_cleared = True
            st.session_state.form_reset += 1
        except Exception:
            st.session_state.msg_erro = "Erro: Este e-mail já está em uso no sistema."
    else:
        st.session_state.msg_erro = "Nome, e-mail e senha são obrigatórios."

def callback_alteracao(id_usu):
    nome = st.session_state.get(f"alt_nome_u_{st.session_state.form_reset}", "")
    perfil = st.session_state.get(f"alt_perfil_u_{st.session_state.form_reset}", "Padrão")
    nova_senha = st.session_state.get(f"alt_senha_u_{st.session_state.form_reset}", "")
    
    if nome.strip():
        if nova_senha.strip():
            GerenciadorBanco.executar_query("UPDATE usuarios SET nome = %s, perfil = %s, senha = %s WHERE id = %s", 
                                            (nome, perfil, gerar_hash(nova_senha), id_usu), is_select=False)
        else:
            GerenciadorBanco.executar_query("UPDATE usuarios SET nome = %s, perfil = %s WHERE id = %s", 
                                            (nome, perfil, id_usu), is_select=False)
        
        # Atualiza a sessão se o admin alterou o próprio nome
        if st.session_state.email_logado == GerenciadorBanco.executar_query("SELECT email FROM usuarios WHERE id=%s", (id_usu,)).iloc[0]['email']:
            st.session_state.usuario_logado = nome
            st.session_state.perfil_logado = perfil
            
        st.session_state.msg_sucesso = True
        st.session_state.form_cleared = True
        st.session_state.form_reset += 1
    else:
        st.session_state.msg_erro = "O campo de nome é obrigatório."

def callback_exclusao(id_usu):
    GerenciadorBanco.executar_query("DELETE FROM usuarios WHERE id = %s", (int(id_usu),), is_select=False)
    st.session_state.msg_sucesso = True
    st.session_state.form_cleared = True
    st.session_state.form_reset += 1

# ==========================================
# MODAIS PADRONIZADAS
# ==========================================
@st.dialog(":material/person_add: Novo usuário")
def modal_inclusao():
    UtilitariosVisuais.exibir_mensagens()
    
    val_nome = "" if st.session_state.form_cleared else ""
    val_email = "" if st.session_state.form_cleared else ""
    
    st.text_input("Nome completo:", value=val_nome, key=f"inc_nome_u_{st.session_state.form_reset}")
    st.text_input("E-mail corporativo:", value=val_email, key=f"inc_email_u_{st.session_state.form_reset}")
    
    c1, c2 = st.columns(2)
    with c1: st.text_input("Senha de acesso:", type="password", key=f"inc_senha_u_{st.session_state.form_reset}")
    with c2: st.selectbox("Perfil de acesso:", ["Padrão", "Administrador"], index=0, key=f"inc_perfil_u_{st.session_state.form_reset}")
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_inclusao)

@st.dialog(":material/manage_accounts: Editar usuário")
def modal_alteracao(id_usu, nome_atual, email_atual, perfil_atual):
    UtilitariosVisuais.exibir_mensagens()
    
    val_nome = "" if st.session_state.form_cleared else nome_atual
    idx_perfil = 0 if st.session_state.form_cleared else (0 if perfil_atual == "Padrão" else 1)
    
    st.text_input("Nome completo:", value=val_nome, key=f"alt_nome_u_{st.session_state.form_reset}")
    st.text_input("E-mail corporativo (Não editável):", value=email_atual, disabled=True)
    
    c1, c2 = st.columns(2)
    with c1: st.text_input("Nova senha (deixe em branco para manter):", type="password", key=f"alt_senha_u_{st.session_state.form_reset}")
    with c2: st.selectbox("Perfil de acesso:", ["Padrão", "Administrador"], index=idx_perfil, key=f"alt_perfil_u_{st.session_state.form_reset}")
    
    c1, c2, c3 = st.columns([4, 3, 3])
    with c2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with c3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_alteracao, args=(id_usu,))

@st.dialog(":material/person_remove: Excluir usuário")
def modal_exclusao(id_usu, nome_atual, email_atual):
    UtilitariosVisuais.exibir_mensagens()
    
    if email_atual == st.session_state.email_logado:
        st.error("Ação bloqueada: Você não pode excluir a sua própria conta enquanto estiver logado.")
        c1, c2 = st.columns([7, 3])
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
        return

    if not st.session_state.form_cleared:
        html_confirmacao = f"""
        <div style="border-left: 5px solid #457b9d; background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #e9ecef;">
            <div style="color: #1a2a40; font-size: 17px; line-height: 1.6;">
                Tem a certeza que deseja remover o acesso do usuário <b>{nome_atual}</b>?<br>
                <span style="color: #e76f51;"><i>Esta ação é irreversível.</i></span>
            </div>
        </div>
        """
        st.markdown(html_confirmacao, unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 3, 3])
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
        with c3:
            st.button("Confirmar", type="primary", use_container_width=True, on_click=callback_exclusao, args=(id_usu,))
    else:
        c1, c2 = st.columns([7, 3])
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()

# ==========================================
# CONSTRUÇÃO DA TELA (VIEW)
# ==========================================
if 'f_usu_pesq' not in st.session_state: st.session_state.f_usu_pesq = ""
if 'f_usu_perf' not in st.session_state: st.session_state.f_usu_perf = "Todos os perfis"
if 'show_f_usu' not in st.session_state: st.session_state.show_f_usu = False

c_titulo, c_filtrar, c_inserir, c_margem = st.columns([5, 1.5, 1.5, 3])
with c_titulo: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>manage_accounts</span> Controle de Acessos</h3>", unsafe_allow_html=True)
with c_filtrar:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True):
        st.session_state.show_f_usu = not st.session_state.show_f_usu; st.rerun()
with c_inserir:
    if st.button("Inserir", type="primary", icon=":material/add:", use_container_width=True): 
        UtilitariosVisuais.preparar_modal()
        modal_inclusao()

if st.session_state.show_f_usu:
    with st.container(border=True):
        cp, cn, cb = st.columns([5, 3, 2])
        v_pesq = cp.text_input("Pesquisar nome ou e-mail:", value=st.session_state.f_usu_pesq)
        op_perf = ["Todos os perfis", "Administrador", "Padrão"]
        v_perf = cn.selectbox("Perfil de acesso:", op_perf, index=op_perf.index(st.session_state.f_usu_perf))
        cb.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if cb.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True):
            st.session_state.f_usu_pesq, st.session_state.f_usu_perf = v_pesq, v_perf; st.rerun()
st.markdown("<br>", unsafe_allow_html=True)

df = carregar_dados(st.session_state.f_usu_pesq, st.session_state.f_usu_perf)
st.markdown('<div class="cabecalho-grid"><div style="display: flex;"><div style="flex: 4;">Usuário</div><div style="flex: 3;">E-mail corporativo</div><div style="flex: 2; text-align: center;">Perfil</div><div style="flex: 1.5; text-align: center;">Ações</div></div></div>', unsafe_allow_html=True)

if df.empty:
    st.info("Nenhum usuário encontrado na base de dados.")
else:
    with st.container():
        st.markdown("<div class='btn-acao-grid'>", unsafe_allow_html=True)
        for _, row in df.iterrows():
            id_usu, nome, email, perfil = row['id'], row['nome'], row['email'], row['perfil']
            c1, c2, c3, c4, c5 = st.columns([4, 3, 2, 0.75, 0.75], vertical_alignment="center")
            c1.markdown(f"<span style='font-weight: 600; color: #1a2a40; font-size: 15px; padding-left: 10px;'>{nome}</span>", unsafe_allow_html=True)
            c2.markdown(f"<span style='color: #495057; font-size: 14px;'>{email}</span>", unsafe_allow_html=True)
            badge = "badge-receita" if perfil == "Administrador" else "badge-neutro"
            c3.markdown(f"<div style='text-align: center;'><span class='{badge}'>{perfil}</span></div>", unsafe_allow_html=True)
            if c4.button(" ", icon=":material/edit:", key=f"eu_{id_usu}", help="Editar", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_alteracao(int(id_usu), nome, email, perfil)
            if c5.button(" ", icon=":material/delete:", key=f"xu_{id_usu}", help="Excluir", use_container_width=True): 
                UtilitariosVisuais.preparar_modal(); modal_exclusao(int(id_usu), nome, email)
            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)