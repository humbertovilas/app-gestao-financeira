# 📊 Gestão Financeira SaaS - Versão 7.0

Plataforma corporativa de alta performance para controle de fluxo de caixa, gestão estratégica de recorrências e inteligência de faturas. Esta versão consolida a transição definitiva para o modelo SaaS (Software as a Service) com processamento atômico de dados e interface reativa.

## 🚀 Evolução Arquitetural (SaaS Model)
O sistema passou por uma reengenharia completa para maximizar a área útil de trabalho e a fluidez de navegação:
* **Top Navbar Fixa:** Substituição da barra lateral nativa por um menu superior dinâmico (st.popover + st.columns), permitindo que DataGrids e Dashboards ocupem 100% da largura da tela[cite: 118].
* **Roteamento Avançado:** Migração integral para o motor 'st.navigation' e 'st.Page', garantindo isolamento de escopo entre módulos e resolvendo erros de importação e conflitos de variáveis globais.
* **Performance de Dados:** Otimização matricial via biblioteca Pandas, assegurando cálculos de juros, saldos projetados e acumulados com precisão cirúrgica[cite: 12, 13].

## 🛠️ Tecnologias e Infraestrutura
* **Linguagem:** Python 3.x com processamento de dados via Pandas[cite: 12].
* **Interface:** Streamlit com injeção dinâmica de CSS3 e JavaScript (MutationObserver)[cite: 14, 120].
* **Banco de Dados:** PostgreSQL (Hospedado via Neon DB) com conformidade ACID absoluta para evitar corrupção de registros em falhas de rede[cite: 16].
* **Segurança de Identidade:** Criptografia SHA-256 para proteção de credenciais e controle de acesso baseado em perfis (Administrador/Operador).

## ✨ Funcionalidades de Engenharia (Destaques V7)

### 1. Engenharia de Recorrência (Edição e Exclusão em Cascata)
Implementação de um elo lógico via UUID ('codigo_parcelamento') que permite gerenciar séries complexas de lançamentos:
* **Propagação Inteligente:** Ao alterar um registro, o usuário define o alcance (Apenas esta parcela / Esta e as próximas pendentes / Todas as parcelas da série).
* **Motor de Transação em Lote:** Desenvolvimento do método 'executar_transacao_lote' para processar múltiplos registros em um único commit atômico, eliminando a latência de rede entre a aplicação e o banco Neon DB.

### 2. Inteligência em Cartões de Crédito (Alt. A)
* **Cálculo de Ciclo de Fatura:** O sistema projeta vencimentos automáticos baseando-se nos dias de fechamento e vencimento configurados para cada cartão[cite: 103].
* **Brava de Segurança:** Bloqueio automático de intervalos manuais no modo cartão, forçando o padrão de mercado de faturas mensais (30 dias).
* **Fixação de Emissão:** A data de compra (Emissão) permanece íntegra em todas as parcelas, enquanto o vencimento avança matematicamente pelos meses subsequentes, corrigindo ilusões de ótica em grids cronológicos.

### 3. Motor Global de Interface (UI Auto-Styler)
Injeção de um "Vigia JavaScript" que monitora o DOM (Document Object Model) e aplica a identidade visual do projeto automaticamente:
* **Ações Positivas:** Botões como "Salvar" ou "Confirmar" assumem o Verde Esmeralda (#20c997).
* **Consultas:** Botões como "Filtrar" ou "Pesquisar" assumem o Azul Marinho (#1a2a40).
* **Isolamento de Logout:** Rotina de limpeza que remove ativos de CSS da Navbar ao deslogar, garantindo uma tela de login pura e sem vazamentos estéticos.

### 4. Gestão de Identidade (Meu Perfil)
Módulo inédito para autogestão de credenciais, permitindo a atualização de nomes de exibição e alteração de senhas em ambiente isolado com validação de hash em tempo real.

## 📁 Topologia do Projeto
* `/infraestrutura`: Camada de persistência (ProcessoCrud.py) e injeção visual global[cite: 23].
* `/modulos`: Lógica individual de páginas (Agenda, Cartões, Fornecedores, etc.)[cite: 24].
* `MenuPrincipal.py`: Orquestrador central e roteador de segurança[cite: 26].
* `style.css`: Blueprint de layout e definições de badges de status[cite: 118, 119].

## ⚙️ Instalação e Execução
1. Clone o repositório.
2. Instale as dependências: `pip install streamlit pandas psycopg2-binary`.
3. Configure o arquivo `.streamlit/secrets.toml` com sua URL do Neon DB[cite: 21].
4. Inicie o sistema: `streamlit run MenuPrincipal.py`.

---
**Desenvolvido por Humberto** - Foco em robustez, engenharia de dados e UX financeiro de precisão.
