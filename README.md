# 📊 Gestão Financeira SaaS

Plataforma corporativa de controle de fluxo de caixa e gestão de recorrências, desenvolvida com foco em alta performance, experiência do usuário (UX) e integridade de dados.

## 🚀 Sobre o Projeto
O sistema foi concebido para oferecer uma experiência de software como serviço (SaaS), eliminando a complexidade de planilhas e oferecendo um motor financeiro inteligente capaz de gerenciar parcelamentos complexos e faturas de cartão de crédito com latência zero.

## 🛠️ Tecnologias Utilizadas
* **Linguagem:** Python 3.x
* **Interface:** Streamlit (Arquitetura de navegação nativa)
* **Banco de Dados:** PostgreSQL (Hospedado via Neon DB)
* **Estilização:** CSS3 e Injeção dinâmica de JavaScript (MutationObserver)
* **Segurança:** Criptografia SHA-256 para credenciais

## ✨ Funcionalidades de Destaque

### 1. Engenharia de Recorrência (Edição em Cascata)
O sistema utiliza um elo estrutural via UUID para agrupar parcelas. Isso permite que o usuário realize alterações em lote com três níveis de propagação:
* Alteração individual de parcela.
* Propagação para parcelas futuras pendentes (Manutenção do fluxo projetado).
* Sobrescrita integral de histórico.

### 2. Motor de Performance (Zero Latency)
Diferente de sistemas convencionais que realizam múltiplas chamadas ao banco, este projeto implementa um **Motor de Transação em Lote**. Todas as operações de parcelamento são empacotadas em um único commit atômico, garantindo velocidade instantânea e integridade dos dados.

### 3. Gestão Inteligente de Cartões
* **Cálculo de Ciclo de Fatura:** O sistema projeta vencimentos baseando-se no dia de fechamento e vencimento configurados.
* **Trava de Segurança:** Bloqueio automático de intervalos manuais em modo cartão, forçando o padrão de mercado de faturas mensais.

### 4. Interface SaaS Moderna
* **Top Navbar:** Navegação superior limpa, maximizando o espaço para grids de dados.
* **Motor Visual:** Padronização automática de botões de ação e consulta via vigia JavaScript global.
* **Isolamento de Sessão:** Sistema de logout com limpeza de DOM, evitando vazamentos de interface.

## ⚙️ Como Executar

### Pré-requisitos
* Python instalado (versão 3.8 ou superior).
* Acesso a uma instância PostgreSQL (recomendado Neon.tech).

### Instalação
1. Clone o repositório:
   ```bash
   git clone [https://github.com/seu-usuario/seu-repositorio.git](https://github.com/seu-usuario/seu-repositorio.git)
