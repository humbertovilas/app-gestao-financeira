import streamlit as st
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais
import pandas as pd
import hashlib

UtilitariosVisuais.aplicar_configuracoes_ui()
UtilitariosVisuais.inicializar_estados_modal()

def gerar_hash_senha(senha):
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

def carregar_dados(pesquisa=""):
    query = "SELECT id, nome, email, perfil, ativo FROM usuarios"
    params = []
    if pesquisa:
        query += " WHERE nome ILIKE %s OR email ILIKE %s"
        params.extend([f"%{pesquisa}%", f"%{pesquisa}%"])
    query += " ORDER BY nome ASC"
    return GerenciadorBanco.executar_query(query, tuple(params))

def callback_inclusao():
    nome = st.session_state.get(f"inc_nome_usr_{st.session_state.form_reset}", "")
    email = st.session_state.get(f"inc_email_usr_{st.session_state.form_reset}", "")
    senha = st.session_state.get(f"inc_senha_usr_{st.session_state.form_reset}", "")
    perfil = st.session_state.get(f"inc_perfil_usr_{st.session_state.form_reset}", "Operador")
    ativo = st.session_state.get(f"inc_ativo_usr_{st.session_state.form_reset}", True)
    
    if nome.strip() and email.strip() and senha.strip():
        senha_hash = gerar_hash_senha(senha)
        try:
            GerenciadorBanco.executar_query("INSERT INTO usuarios (nome, email, senha, perfil, ativo) VALUES (%s, %s, %s, %s, %s)", (nome, email, senha_hash, perfil, ativo), is_select=False)
            st.session_state.msg_sucesso = True
            st.session_state.form_cleared = True
            st.session_state.form_reset += 1
        except Exception:
            st.session_state.msg_erro = "E-mail já cadastrado no sistema."
    else:
        st.session_state.msg_erro = "Nome, E-mail e Senha são obrigatórios para novos usuários."

def callback_alteracao(id_usr):
    nome = st.session_state.get(f"alt_nome_usr_{st.session_state.form_reset}", "")
    email = st.session_state.get(f"alt_email_usr_{st.session_state.form_reset}", "")
    senha = st.session_state.get(f"alt_senha_usr_{st.session_state.form_reset}", "")
    perfil = st.session_state.get(f"alt_perfil_usr_{st.session_state.form_reset}", "Operador")
    ativo = st.session_state.get(f"alt_ativo_usr_{st.session_state.form_reset}", True)
    
    if nome.strip() and email.strip():
        try:
            if senha.strip():
                senha_hash = gerar_hash_senha(senha)
                GerenciadorBanco.executar_query("UPDATE usuarios SET nome = %s, email = %s, senha = %s, perfil = %s, ativo = %s WHERE id = %s", (nome, email, senha_hash, perfil, ativo, id_usr), is_select=False)
            else:
                GerenciadorBanco.executar_query("UPDATE usuarios SET nome = %s, email = %s, perfil = %s, ativo = %s WHERE id = %s", (nome, email, perfil, ativo, id_usr), is_select=False)
            st.session_state.msg_sucesso = True
            st.session_state.form_cleared = True
            st.session_state.form_reset += 1
        except Exception:
            st.session_state.msg_erro = "E-mail já está em uso por outro cadastro."
    else:
        st.session_state.msg_erro = "Nome e E-mail não podem ficar vazios."

def callback_exclusao(id_usr):
    GerenciadorBanco.executar_query("DELETE FROM usuarios WHERE id = %s", (int(id_usr),), is_select=False)
    st.session_state.msg_sucesso = True
    st.session_state.form_cleared = True
    st.session_state.form_reset += 1

@st.dialog(":material/person_add: Novo usuário")
def modal_inclusao():
    UtilitariosVisuais.exibir_mensagens()
    val_nome = "" if st.session_state.form_cleared else ""
    val_email = "" if st.session_state.form_cleared else ""
    st.text_input("Nome completo:", value=val_nome, key=f"inc_nome_usr_{st.session_state.form_reset}")
    st.text_input("E-mail (Login):", value=val_email, key=f"inc_email_usr_{st.session_state.form_reset}")
    st.text_input("Senha provisória:", type="password", key=f"inc_senha_usr_{st.session_state.form_reset}")
    
    c1, c2 = st.columns(2)
    c1.selectbox("Perfil de acesso:", ["Operador", "Administrador"], key=f"inc_perfil_usr_{st.session_state.form_reset}")
    c2.checkbox("Usuário Ativo", value=True, key=f"inc_ativo_usr_{st.session_state.form_reset}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns(3)
    with b2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with b3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_inclusao)

@st.dialog(":material/edit: Editar usuário")
def modal_alteracao(id_usr, nome, email, perfil, ativo):
    UtilitariosVisuais.exibir_mensagens()
    val_nome = "" if st.session_state.form_cleared else nome
    val_email = "" if st.session_state.form_cleared else email
    
    st.text_input("Nome completo:", value=val_nome, key=f"alt_nome_usr_{st.session_state.form_reset}")
    st.text_input("E-mail (Login):", value=val_email, key=f"alt_email_usr_{st.session_state.form_reset}")
    st.text_input("Nova senha (deixe em branco para manter a atual):", type="password", key=f"alt_senha_usr_{st.session_state.form_reset}")
    
    c1, c2 = st.columns(2)
    idx_perfil = 1 if perfil == "Administrador" else 0
    c1.selectbox("Perfil de acesso:", ["Operador", "Administrador"], index=idx_perfil, key=f"alt_perfil_usr_{st.session_state.form_reset}")
    c2.checkbox("Usuário Ativo", value=bool(ativo), key=f"alt_ativo_usr_{st.session_state.form_reset}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns(3)
    with b2:
        if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    with b3:
        st.button("Salvar", type="primary", use_container_width=True, on_click=callback_alteracao, args=(id_usr,))

@st.dialog(":material/delete: Excluir usuário")
def modal_exclusao(id_usr, nome, email):
    UtilitariosVisuais.exibir_mensagens()
    if email == "admin@sistema.com.br" or email == st.session_state.email_logado:
        st.error("Bloqueio de segurança: Não é possível excluir o seu próprio usuário ou o Administrador Mestre.")
        c1, c2 = st.columns(2)
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
    elif not st.session_state.form_cleared:
        html_confirmacao = f"""
        <div style="border-left: 5px solid #e76f51; background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #e9ecef;">
            <div style="color: #1a2a40; font-size: 17px; line-height: 1.6;">
                Tem a certeza que deseja excluir o acesso de <b>{nome}</b>?<br>
                <span style="color: #e76f51;"><i>Esta ação é irreversível.</i></span>
            </div>
        </div>
        """
        st.markdown(html_confirmacao, unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()
        with c3:
            st.button("Confirmar", type="primary", use_container_width=True, on_click=callback_exclusao, args=(id_usr,))
    else:
        c1, c2, c3 = st.columns(3)
        with c2:
            if st.button("Fechar", type="secondary", use_container_width=True): st.rerun()

if 'f_usr_pesq' not in st.session_state: st.session_state.f_usr_pesq = ""
if 'f_usr_perf' not in st.session_state: st.session_state.f_usr_perf = "Todos os perfis"
if 'f_usr_stat' not in st.session_state: st.session_state.f_usr_stat = "Todos os status"
if 'show_f_usr' not in st.session_state: st.session_state.show_f_usr = False

c_titulo, c_filtrar, c_inserir, c_margem = st.columns([5, 1.5, 1.5, 3])
with c_titulo: st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>manage_accounts</span> Gestão de Acessos</h3>", unsafe_allow_html=True)
with c_filtrar:
    if st.button("Filtrar", type="tertiary", icon=":material/search:", use_container_width=True):
        st.session_state.show_f_usr = not st.session_state.show_f_usr; st.rerun()
with c_inserir:
    if st.button("Novo Usuário", type="primary", icon=":material/add:", use_container_width=True): 
        UtilitariosVisuais.preparar_modal(); modal_inclusao()

if st.session_state.show_f_usr:
    with st.container(border=True):
        f1, f2, f3, f_check, f_btn = st.columns([2.5, 1.5, 1.5, 1.5, 1.5], vertical_alignment="bottom")
        v_pesq = f1.text_input("Buscar por nome ou e-mail:", value=st.session_state.f_usr_pesq)
        
        op_perf = ["Todos os perfis", "Administrador", "Operador"]
        idx_perf = op_perf.index(st.session_state.f_usr_perf) if st.session_state.f_usr_perf in op_perf else 0
        v_perf = f2.selectbox("Perfil:", op_perf, index=idx_perf)
        
        op_stat = ["Todos os status", "Ativos", "Inativos"]
        idx_stat = op_stat.index(st.session_state.f_usr_stat) if st.session_state.f_usr_stat in op_stat else 0
        v_stat = f3.selectbox("Status:", op_stat, index=idx_stat)
        
        with f_check:
            auto_refresh = st.checkbox("Refresh automático", value=st.session_state.get('f_usr_auto', False), key='f_usr_auto')
        with f_btn:
            if auto_refresh:
                st.session_state.f_usr_pesq = v_pesq
                st.session_state.f_usr_perf = v_perf
                st.session_state.f_usr_stat = v_stat
                st.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True, disabled=True)
            else:
                if st.button("Pesquisar", type="tertiary", icon=":material/search:", use_container_width=True):
                    st.session_state.f_usr_pesq = v_pesq
                    st.session_state.f_usr_perf = v_perf
                    st.session_state.f_usr_stat = v_stat
                    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

df = carregar_dados(st.session_state.f_usr_pesq)

if not df.empty:
    if st.session_state.f_usr_perf != "Todos os perfis":
        df = df[df['perfil'] == st.session_state.f_usr_perf]
    if st.session_state.f_usr_stat == "Ativos":
        df = df[df['ativo'] == True]
    elif st.session_state.f_usr_stat == "Inativos":
        df = df[df['ativo'] == False]

html_cabecalho = '''
<div class="cabecalho-grid">
    <div style="display: flex;">
        <div style="flex: 3;">Usuário</div>
        <div style="flex: 2.5;">E-mail Corporativo</div>
        <div style="flex: 1.5; text-align: center;">Perfil</div>
        <div style="flex: 1; text-align: center;">Status</div>
        <div style="flex: 1; text-align: center;">Ações</div>
    </div>
</div>
'''
st.markdown(html_cabecalho, unsafe_allow_html=True)

if df.empty:
    st.info("Nenhum usuário encontrado na base de dados.")
else:
    with st.container():
        st.markdown("<div class='btn-acao-grid'>", unsafe_allow_html=True)
        for _, row in df.iterrows():
            id_usr, nome, email, perfil, ativo = row['id'], row['nome'], row['email'], row['perfil'], row['ativo']
            c1, c2, c3, c4, c5, c6 = st.columns([3, 2.5, 1.5, 1, 0.5, 0.5], vertical_alignment="center")
            c1.markdown(f"<span style='font-weight: 600; color: #1a2a40; font-size: 15px; padding-left: 10px;'>{nome}</span>", unsafe_allow_html=True)
            c2.markdown(f"<span style='color: #495057; font-size: 14px;'>{email}</span>", unsafe_allow_html=True)
            c3.markdown(f"<div style='text-align: center; color: #495057; font-size: 14px;'>{perfil}</div>", unsafe_allow_html=True)
            
            badge_stat = "badge-efetivado" if ativo else "badge-pendente"
            lbl_stat = "ATIVO" if ativo else "INATIVO"
            c4.markdown(f"<div style='text-align: center;'><span class='{badge_stat}'>{lbl_stat}</span></div>", unsafe_allow_html=True)
            
            if c5.button(" ", icon=":material/edit:", key=f"eu_{id_usr}", help="Editar Acesso"): 
                UtilitariosVisuais.preparar_modal(); modal_alteracao(int(id_usr), nome, email, perfil, ativo)
            if c6.button(" ", icon=":material/delete:", key=f"xu_{id_usr}", help="Remover Acesso"): 
                UtilitariosVisuais.preparar_modal(); modal_exclusao(int(id_usr), nome, email)
            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)