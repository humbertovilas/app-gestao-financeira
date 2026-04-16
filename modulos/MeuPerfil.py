import streamlit as st
import hashlib
from infraestrutura.ProcessoCrud import GerenciadorBanco

# ==========================================
# FUNÇÕES DE APOIO E SEGURANÇA
# ==========================================
def gerar_hash_senha(senha):
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

def carregar_meus_dados(email):
    query = "SELECT id, nome, email, perfil FROM usuarios WHERE email = %s"
    return GerenciadorBanco.executar_query(query, (email,))

# ==========================================
# INTERFACE PRINCIPAL DO MÓDULO
# ==========================================
def renderizar_meu_perfil():
    st.markdown("### :material/person: Meu perfil")
    st.markdown("<p style='color: #6c757d; font-size: 14px; margin-bottom: 25px;'>Gerencie suas informações pessoais e credenciais de acesso.</p>", unsafe_allow_html=True)
    
    # Validação de sessão ativa
    email_logado = st.session_state.get("email_logado", "")
    if not email_logado:
        st.error("Sessão expirada ou usuário não está logado.")
        return

    # Busca os dados fresquinhos do banco
    df = carregar_meus_dados(email_logado)
    
    if not df.empty:
        usr = df.iloc[0]
        
        c1, c2 = st.columns(2, gap="large")
        
        # BLOCO 1: Informações Pessoais
        with c1:
            st.markdown("#### Dados pessoais")
            with st.container(border=True):
                novo_nome = st.text_input("Seu nome completo:", value=usr['nome'])
                st.text_input("E-mail corporativo (Acesso):", value=usr['email'], disabled=True)
                st.text_input("Nível de permissão:", value=usr['perfil'], disabled=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("Atualizar nome", type="primary", use_container_width=True):
                    if not novo_nome.strip():
                        st.error("O nome não pode ficar vazio.")
                    else:
                        query_update = "UPDATE usuarios SET nome = %s WHERE id = %s"
                        GerenciadorBanco.executar_query(query_update, (novo_nome, usr['id']), is_select=False)
                        
                        # Atualiza a sessão para refletir o novo nome imediatamente na Navbar
                        st.session_state.usuario_logado = novo_nome
                        st.success("Nome atualizado com sucesso!")
                        st.rerun()

        # BLOCO 2: Segurança (Alteração de Senha)
        with c2:
            st.markdown("#### Segurança e acesso")
            with st.container(border=True):
                s_atual = st.text_input("Senha atual:", type="password")
                s_nova = st.text_input("Nova senha:", type="password")
                s_conf = st.text_input("Confirme a nova senha:", type="password")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("Alterar minha senha", type="primary", use_container_width=True):
                    if not s_atual or not s_nova or not s_conf:
                        st.error("Por favor, preencha todos os campos de senha.")
                    else:
                        hash_atual = gerar_hash_senha(s_atual)
                        check = GerenciadorBanco.executar_query("SELECT id FROM usuarios WHERE email = %s AND senha = %s", (email_logado, hash_atual))
                        
                        if check.empty:
                            st.error("A senha atual informada está incorreta.")
                        elif s_nova != s_conf:
                            st.error("As novas senhas não coincidem.")
                        else:
                            novo_hash = gerar_hash_senha(s_nova)
                            GerenciadorBanco.executar_query("UPDATE usuarios SET senha = %s WHERE id = %s", (novo_hash, usr['id']), is_select=False)
                            st.success("Senha alterada com sucesso! Utilize-a no próximo login.")

# ==========================================
# GATILHO DE EXECUÇÃO
# ==========================================
if __name__ == "__main__":
    renderizar_meu_perfil()
else:
    renderizar_meu_perfil()