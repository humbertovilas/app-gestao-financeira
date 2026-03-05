import sqlite3

# ==========================================
# MÓDULO 1: INFRAESTRUTURA
# ==========================================
def inicializar_banco():
    conn = sqlite3.connect('app_financas.db')
    cursor = conn.cursor()
    
    # Cria a tabela de categorias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL
        )
    ''')
    
    # Cria a tabela de lançamentos com separação de entrada/saída
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            evento TEXT,
            classificacao TEXT,
            categoria TEXT,
            entrada REAL DEFAULT 0,
            saida REAL DEFAULT 0,
            saldo REAL DEFAULT 0,
            status TEXT DEFAULT 'Pendente',
            observacao TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# ==========================================
# MÓDULO 2: MOTOR DE CADASTROS (Categorias)
# ==========================================
def salvar_categoria(nome, tipo):
    conn = sqlite3.connect('app_financas.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO categorias (nome, tipo) VALUES (?, ?)', (nome, tipo))
    conn.commit()
    conn.close()
    print(f"\n[SUCESSO] Categoria '{nome}' ({tipo}) registada com sucesso!")

def listar_categorias():
    conn = sqlite3.connect('app_financas.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categorias')
    linhas = cursor.fetchall()
    conn.close()
    
    print("\n--- CATEGORIAS CADASTRADAS ---")
    print(f"{'ID':<3} | {'NOME':<20} | {'NATUREZA'}")
    print("-" * 45)
    for linha in linhas:
        print(f"{linha[0]:<3} | {linha[1]:<20} | {linha[2]}")
    print("-" * 45)

# ==========================================
# MÓDULO 3: LANÇAMENTOS E FLUXO DE CAIXA
# ==========================================
def salvar_lancamento(data, evento, categoria, valor, natureza, status):
    # Lógica de roteamento de valores (Inteligência Financeira)
    entrada = valor if natureza.lower() in ['entrada', 'receita'] else 0
    saida = valor if natureza.lower() in ['saida', 'despesa'] else 0
    
    conn = sqlite3.connect('app_financas.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO lancamentos (data, evento, categoria, entrada, saida, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data, evento, categoria, entrada, saida, status))
    conn.commit()
    conn.close()
    print(f"\n[SUCESSO] Lançamento '{evento}' gravado com sucesso no Livro Caixa!")

def exibir_extrato_financeiro():
    conn = sqlite3.connect('app_financas.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, data, evento, entrada, saida, status FROM lancamentos ORDER BY id ASC')
    linhas = cursor.fetchall()
    conn.close()
    
    saldo_atual = 0
    
    print("\n" + "="*75)
    print(f"{'EXTRATO FINANCEIRO (app_financas)':^75}")
    print("="*75)
    print(f"{'ID':<3} | {'DATA':<10} | {'EVENTO':<18} | {'ENTRADA':<10} | {'SAÍDA':<10} | {'STATUS'}")
    print("-" * 75)
    
    for linha in linhas:
        id_lanc, data, evento, entrada, saida, status = linha
        
        # O Motor Matemático de Saldo Acumulado
        saldo_atual += (entrada - saida)
        
        print(f"{id_lanc:<3} | {data:<10} | {evento:<18} | R$ {entrada:<7.2f} | R$ {saida:<7.2f} | {status}")
        
    print("-" * 75)
    print(f"SALDO TOTAL PROJETADO: R$ {saldo_atual:.2f}")
    print("="*75)

# ==========================================
# CABINE DE COMANDO (Menu Principal Unificado)
# ==========================================
def menu_principal():
    while True:
        print("\n" + "="*45)
        print(f"{'ERP APP_FINANCAS - MENU PRINCIPAL':^45}")
        print("="*45)
        print("1. Cadastrar Categoria")
        print("2. Listar Categorias")
        print("3. Novo Lançamento Financeiro")
        print("4. Ver Extrato e Saldo")
        print("5. Sair")
        
        opcao = input("\nEscolha uma opção (1-5): ")
        
        if opcao == '1':
            nome = input("Nome da Categoria (Ex: Salário, Moradia): ")
            tipo = input("Natureza (Entrada ou Saida): ")
            salvar_categoria(nome, tipo)
        elif opcao == '2':
            listar_categorias()
        elif opcao == '3':
            print("\n--- NOVO LANÇAMENTO ---")
            data = input("Data (DD/MM/AAAA): ")
            evento = input("Evento (Ex: Conta de Luz, Cliente X): ")
            categoria = input("Categoria (Ex: Moradia): ")
            valor_bruto = input("Valor (R$): ")
            valor = float(valor_bruto.replace(',', '.'))
            natureza = input("Natureza do valor (Entrada ou Saida): ")
            status = input("Status (Pendente ou Efetivado): ")
            salvar_lancamento(data, evento, categoria, valor, natureza, status)
        elif opcao == '4':
            exibir_extrato_financeiro()
        elif opcao == '5':
            print("A encerrar o sistema. Até logo!")
            break
        else:
            print("Opção inválida! Tente novamente.")

# ==========================================
# START DO SISTEMA
# ==========================================
if __name__ == "__main__":
    inicializar_banco()
    menu_principal()