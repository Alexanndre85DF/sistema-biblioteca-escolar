import sqlite3
import hashlib
from getpass import getpass

def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def listar_escolas():
    conn = sqlite3.connect('database_new.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome FROM escolas')
    escolas = cursor.fetchall()
    conn.close()
    return escolas

def cadastrar_usuario():
    print("\n=== Cadastro de Novo Usuário ===\n")
    
    # Lista as escolas disponíveis
    escolas = listar_escolas()
    print("Escolas disponíveis:")
    for id, nome in escolas:
        print(f"{id}. {nome}")
    
    # Coleta os dados do usuário
    while True:
        try:
            escola_id = int(input("\nDigite o número da escola: "))
            # Verifica se a escola existe
            if not any(id == escola_id for id, _ in escolas):
                print("Escola não encontrada! Tente novamente.")
                continue
            break
        except ValueError:
            print("Por favor, digite um número válido.")
    
    cpf = input("CPF do usuário: ")
    senha = getpass("Senha do usuário: ")
    confirmar_senha = getpass("Confirme a senha: ")
    
    if senha != confirmar_senha:
        print("\nERRO: As senhas não coincidem!")
        return
    
    try:
        # Conecta ao banco de dados
        conn = sqlite3.connect('database_new.db')
        cursor = conn.cursor()
        
        # Verifica se o CPF já existe para esta escola
        cursor.execute('SELECT * FROM usuarios WHERE cpf = ? AND escola_id = ?', (cpf, escola_id))
        if cursor.fetchone():
            print("\nERRO: CPF já cadastrado para esta escola!")
            return
        
        # Criptografa a senha e insere o usuário
        senha_criptografada = criptografar_senha(senha)
        cursor.execute('''
            INSERT INTO usuarios (cpf, senha, escola_id)
            VALUES (?, ?, ?)
        ''', (cpf, senha_criptografada, escola_id))
        
        # Pega o nome da escola
        cursor.execute('SELECT nome FROM escolas WHERE id = ?', (escola_id,))
        escola_nome = cursor.fetchone()[0]
        
        # Confirma as alterações
        conn.commit()
        
        print("\n=== Usuário cadastrado com sucesso! ===")
        print(f"Escola: {escola_nome}")
        print(f"CPF: {cpf}")
        print("Senha: [a senha que você definiu]")
        
    except sqlite3.IntegrityError:
        print("\nERRO: Erro ao cadastrar usuário!")
    except Exception as e:
        print(f"\nERRO: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    while True:
        cadastrar_usuario()
        
        continuar = input("\nDeseja cadastrar outro usuário? (s/n): ")
        if continuar.lower() != 's':
            break
    
    print("\nPrograma finalizado!") 