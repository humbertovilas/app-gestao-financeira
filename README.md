Manual master - Sistema financeiro (V7)
Este documento constitui a especificação técnica definitiva e o guia de reconstrução do sistema de Gestão Financeira SaaS. A versão 7 consolida a transição para uma arquitetura de alta performance, navegação moderna e integridade de dados via transações em lote.
1. Visão geral e arquitetura tecnológica
O sistema é uma aplicação de gestão financeira robusta, projetada sob o modelo SaaS (Software as a Service).

Linguagem Core: Python 3.x.
Interface (UI/UX): Streamlit com navegação nativa (st.navigation) e injeção de CSS/JS customizado.
Banco de Dados: PostgreSQL (Neon DB) com conformidade ACID.
Navegação: Modelo Top Navbar fixa (substituindo a sidebar nativa) para maximização da área de dados.
Segurança: Criptografia SHA-256 para senhas e controle de acesso por perfil (Administrador/Usuário).
2. Topologia de diretórios e arquivos
/

├── MenuPrincipal.py          # Orquestrador de rotas e Top Navbar

├── style.css                 # Definições estéticas globais

├── Imagens/                  # Ativos visuais e ícones

│   └── Icones/               # Ícones das classificações

├── infraestrutura/

│   └── ProcessoCrud.py       # Motor de banco e utilitários visuais

└── modulos/

    ├── AgendaFinanceira.py   # Gestão de lançamentos e lote

    ├── CartaoCredito.py      # Gestão de cartões e faturas

    ├── MeuPerfil.py          # Autogestão de credenciais (Novo)

    ├── CadastroUsuario.py    # Gestão administrativa de acessos

    ├── CadastroFornecedor.py # Gestão de fornecedores

    ├── Evento.py             # Eventos financeiros

    ├── Categoria.py          # Categorias pai

    ├── Classificacao.py      # Subcategorias com ícones

    ├── Banco.py              # Cadastro de bancos

    └── ContaBancaria.py      # Gestão de contas correntes
3. Dicionário técnico de módulos
3.1 MenuPrincipal.py
Atua como o roteador central do sistema. Implementa a tela de login isolada e a Top Navbar fixa. Utiliza st.navigation para gerenciar o escopo de cada página de forma independente, resolvendo problemas de importação e vazamento de CSS.
3.2 ProcessoCrud.py
Contém o Motor Global de UI e o Motor de Performance.

Execução em Lote: Método executar_transacao_lote para processamento atômico de múltiplas parcelas.
JavaScript Observer: Motor MutationObserver que vigia o DOM para estilizar botões dinamicamente (Verde Esmeralda para ações, Azul Marinho para consultas).
3.3 AgendaFinanceira.py
Módulo crítico para gestão de fluxo de caixa.

Cascata: Implementa lógica de edição e exclusão propagada baseada no codigo_parcelamento.
Resumo Visual: Cards dinâmicos com saldo anterior e projetado.
3.4 MeuPerfil.py (Novo V7)
Permite ao usuário logado atualizar seu nome de exibição e alterar sua senha com validação criptográfica SHA-256.
4. Regras de negócio e mecanismos de proteção
4.1 Gestão de Parcelamentos
Elo Lógico: Todas as parcelas de uma série compartilham um UUID único (codigo_parcelamento).
Propagação Condicional: Ao editar ou excluir, o usuário escolhe entre: "Apenas esta", "Esta e as próximas pendentes" ou "Todas".
Integridade de Lote: Se uma operação em lote falhar, o sistema realiza o rollback automático para evitar dados corrompidos.
4.2 Motor de Cartão de Crédito
Trava de Intervalo: Em modo "Cartão de Crédito", o campo de intervalo é bloqueado em 30 dias (Regra de mercado).
Projeção de Fatura: O sistema fixa a data de emissão e avança os vencimentos baseando-se nos meses de fatura, considerando o dia de fechamento e vencimento do cartão.
4.3 Segurança e Acesso
Logout Blindado: A rotina de logoff limpa os estados da sessão e remove as injeções de CSS da Navbar para isolar a tela de login.
5. Diretrizes para desenvolvimento futuro
Implementação de Dashboards de indicadores (DRE e Fluxo Mensal).
Integração de notificações automáticas via e-mail para vencimentos.
Exportação de relatórios financeiros em formato PDF/Excel.
6. Apêndice técnico para reconstrução total
6.1 Esquema de banco de dados (SQL)
-- Estrutura Base

CREATE TABLE categorias (id SERIAL PRIMARY KEY, nome TEXT, tipo TEXT);

CREATE TABLE classificacoes (id SERIAL PRIMARY KEY, nome TEXT, id_categoria INTEGER REFERENCES categorias(id), icone TEXT);

CREATE TABLE eventos (id SERIAL PRIMARY KEY, nome TEXT, id_classificacao INTEGER REFERENCES classificacoes(id));

CREATE TABLE usuarios (id SERIAL PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, perfil TEXT, ativo BOOLEAN DEFAULT TRUE);

-- Lançamentos (Atualizado V7)

CREATE TABLE lancamentos (

    id SERIAL PRIMARY KEY,

    data_digitacao DATE DEFAULT CURRENT_DATE,

    data_compra DATE,

    data_vencimento DATE NOT NULL,

    data_efetivacao DATE,

    valor_previsto NUMERIC(15,2) NOT NULL,

    valor_realizado NUMERIC(15,2),

    id_evento INTEGER REFERENCES eventos(id),

    id_classificacao INTEGER REFERENCES classificacoes(id),

    parcela_atual INTEGER DEFAULT 1,

    total_parcelas INTEGER DEFAULT 1,

    status TEXT NOT NULL DEFAULT 'Pendente',

    observacao TEXT,
    id_conta_bancaria INTEGER,
    id_cartao_credito INTEGER,
    id_fornecedor INTEGER REFERENCES fornecedores(id),
    codigo_parcelamento TEXT,
    intervalo INTEGER DEFAULT 30
);
-- Índices de Alta Performance
CREATE INDEX idx_lanc_vencimento ON lancamentos (data_vencimento);
CREATE INDEX idx_lanc_cod_parc ON lancamentos (codigo_parcelamento);
CREATE INDEX idx_lanc_cartao ON lancamentos (id_cartao_credito);
6.2 Proporções de colunas (UI Layout)
Top Navbar: [2.5, 1.2, 1.2, 1.2, 2.5, 1.5]
Grid Agenda Financeira: [1.0, 1.0, 1.1, 2.5, 1.2, 1.0, 1.0, 1.0, 0.5, 0.5, 0.5, 0.5]
Cabeçalhos de Módulo: [5, 1.5, 1.5, 3]
Fim do Documento V7
