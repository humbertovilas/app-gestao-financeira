import streamlit as st
import hashlib
import time
from infraestrutura.ProcessoCrud import GerenciadorBanco, UtilitariosVisuais

# ==========================================
# CONFIGURAÇÕES INICIAIS
# ==========================================
UtilitariosVisuais.aplicar_configuracoes_ui()

if 'msg_perfil_sucesso' not in st.session_state:
    st.session_state.msg_perfil_sucesso = ""
if 'msg_perfil_erro' not in st.session_state:
    st.session_state.msg_perfil_erro = ""

def gerar_hash_senha(senha):
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

# ==========================================
# ACESSO A DADOS
# ==========================================
@st.cache_data(show_spinner=False, ttl=60)
def carregar_meus_dados(email):
    query = "SELECT id, nome, email, perfil FROM usuarios WHERE email = %s"
    return GerenciadorBanco.executar_query(query, (email,))

# ==========================================
# CALLBACKS DE AÇÃO
# ==========================================
def salvar_dados_pessoais(id_usuario):
    novo_nome = st.session_state.inp_meu_nome.strip()
    if not novo_nome:
        st.session_state.msg_perfil_erro = "O nome não pode ficar vazio."
        return
    
    try:
        GerenciadorBanco.executar_query("UPDATE usuarios SET nome = %s WHERE id = %s", (novo_nome, id_usuario), is_select=False)
        st.session_state.usuario_logado = novo_nome  # Atualiza a sessão ativa na barra lateral
        st.cache_data.clear()
        st.session_state.msg_perfil_sucesso = "Informações pessoais atualizadas com sucesso!"
    except Exception as e:
        st.session_state.msg_perfil_erro = f"Erro ao atualizar dados: {e}"

def salvar_nova_senha(id_usuario, email):
    senha_atual = st.session_state.inp_senha_atual
    nova_senha = st.session_state.inp_nova_senha
    confirma_senha = st.session_state.inp_confirma_senha

    if not senha_atual or not nova_senha or not confirma_senha:
        st.session_state.msg_perfil_erro = "Preencha todos os campos de senha."
        return
    
    if nova_senha != confirma_senha:
        st.session_state.msg_perfil_erro = "A nova senha e a confirmação não coincidem."
        return

    # Verifica se a senha atual está correta (Criptografia SHA256)
    hash_atual = gerar_hash_senha(senha_atual)
    df_check = GerenciadorBanco.executar_query("SELECT id FROM usuarios WHERE email = %s AND senha = %s", (email, hash_atual))
    
    if df_check.empty:
        st.session_state.msg_perfil_erro = "A senha atual informada está incorreta."
        return

    # Aplica a nova senha
    novo_hash = gerar_hash_senha(nova_senha)
    try:
        GerenciadorBanco.executar_query("UPDATE usuarios SET senha = %s WHERE id = %s", (novo_hash, id_usuario), is_select=False)
        st.cache_data.clear()
        st.session_state.msg_perfil_sucesso = "Sua senha foi alterada com segurança!"
        st.session_state.inp_senha_atual = ""
        st.session_state.inp_nova_senha = ""
        st.session_state.inp_confirma_senha = ""
    except Exception as e:
        st.session_state.msg_perfil_erro = f"Erro ao atualizar senha: {e}"

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
st.markdown("<h3 class='titulo-pagina'><span class='material-symbols-rounded'>person</span> Meu perfil</h3>", unsafe_allow_html=True)
st.markdown("<p style='color: #6c757d; font-size: 14px; margin-bottom: 25px;'>Gerencie suas informações pessoais e credenciais de acesso.</p>", unsafe_allow_html=True)

if st.session_state.msg_perfil_sucesso:
    st.success(st.session_state.msg_perfil_sucesso)
    st.session_state.msg_perfil_sucesso = ""
if st.session_state.msg_perfil_erro:
    st.error(st.session_state.msg_perfil_erro)
    st.session_state.msg_perfil_erro = ""

email_ativo = st.session_state.email_logado
df_dados = carregar_meus_dados(email_ativo)

if not df_dados.empty:
    meu_id = int(df_dados.iloc[0]['id'])
    meu_nome = df_dados.iloc[0]['nome']
    meu_perfil = df_dados.iloc[0]['perfil']

    c1, c2 = st.columns([1, 1], gap="large")

    # BLOCO 1: Informações Pessoais
    with c1:
        st.markdown("#### Informações pessoais")
        with st.container(border=True):
            st.text_input("Nome de exibição:", value=meu_nome, key="inp_meu_nome")
            st.text_input("E-mail corporativo (Login):", value=email_ativo, disabled=True)
            st.text_input("Nível de acesso:", value=meu_perfil, disabled=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("Atualizar dados", type="primary", use_container_width=True, on_click=salvar_dados_pessoais, args=(meu_id,))

    # BLOCO 2: Segurança
    with c2:
        st.markdown("#### Segurança e acesso")
        with st.container(border=True):
            st.text_input("Senha atual:", type="password", key="inp_senha_atual")
            st.text_input("Nova senha:", type="password", key="inp_nova_senha")
            st.text_input("Confirme a nova senha:", type="password", key="inp_confirma_senha")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("Alterar senha", type="primary", use_container_width=True, on_click=salvar_nova_senha, args=(meu_id, email_ativo))
else:
    st.error("Não foi possível carregar os dados do perfil.")