import sqlite3
import hashlib
from getpass import getpass

def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def cadastrar_escola():
    print("\n=== Cadastro de Nova Escola ===\n")
    
    # Coleta os dados da escola
    nome = input("Nome da escola: ")
    endereco = input("Endereço da escola: ")
    telefone = input("Telefone da escola: ")
    
    print("\n=== Dados do Usuário Administrador ===\n")
    cpf = input("CPF do administrador: ")
    
    try:
        senha = getpass("Senha do administrador: ")
        confirmar_senha = getpass("Confirme a senha: ")
        
        if senha != confirmar_senha:
            print("\nERRO: As senhas não coincidem!")
            return
        
        # Conecta ao banco de dados
        conn = sqlite3.connect('database_new.db')
        cursor = conn.cursor()
        
        # Insere a escola
        cursor.execute('''
            INSERT INTO escolas (nome, endereco, telefone)
            VALUES (?, ?, ?)
        ''', (nome, endereco, telefone))
        
        # Pega o ID da escola que acabou de ser inserida
        escola_id = cursor.lastrowid
        
        # Criptografa a senha e insere o usuário administrador
        senha_criptografada = criptografar_senha(senha)
        cursor.execute('''
            INSERT INTO usuarios (cpf, senha, escola_id)
            VALUES (?, ?, ?)
        ''', (cpf, senha_criptografada, escola_id))
        
        # Confirma as alterações
        conn.commit()
        
        print("\n=== Escola cadastrada com sucesso! ===")
        print(f"Nome da escola: {nome}")
        print(f"ID da escola: {escola_id}")
        print("\nDados de acesso do administrador:")
        print(f"CPF: {cpf}")
        print("Senha: [a senha que você definiu]")
        
    except sqlite3.IntegrityError:
        print("\nERRO: CPF já cadastrado para outra escola!")
    except Exception as e:
        print(f"\nERRO ao cadastrar escola: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    while True:
        cadastrar_escola()
        
        continuar = input("\nDeseja cadastrar outra escola? (s/n): ")
        if continuar.lower() != 's':
            break
    
    print("\nPrograma finalizado!") 