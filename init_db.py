import sqlite3
import hashlib
import os

def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# Nome do novo banco de dados
DB_NAME = 'database.db'

# Remove o banco de dados se já existir
if os.path.exists(DB_NAME):
    os.remove(DB_NAME)

# Conecta ao banco de dados
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Cria a tabela escolas se não existir
cursor.execute('''
CREATE TABLE IF NOT EXISTS escolas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    endereco TEXT,
    telefone TEXT
)
''')

# Cria a tabela usuarios se não existir
cursor.execute('''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cpf TEXT NOT NULL,
    senha TEXT NOT NULL,
    escola_id INTEGER,
    tipo_usuario TEXT DEFAULT 'escola',
    FOREIGN KEY (escola_id) REFERENCES escolas(id),
    UNIQUE(cpf, escola_id)
)
''')

# Cria a tabela livros se não existir
cursor.execute('''
CREATE TABLE IF NOT EXISTS livros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    autor TEXT NOT NULL,
    editora TEXT,
    ano TEXT,
    categoria TEXT,
    quantidade INTEGER DEFAULT 0,
    localizacao TEXT,
    codigo_interno TEXT,
    observacoes TEXT,
    disponivel INTEGER DEFAULT 1,
    escola_id INTEGER NOT NULL,
    FOREIGN KEY (escola_id) REFERENCES escolas(id)
)
''')

# Cria a tabela emprestimos se não existir
cursor.execute('''
CREATE TABLE IF NOT EXISTS emprestimos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno TEXT NOT NULL,
    turma TEXT NOT NULL,
    telefone TEXT,
    livro_id INTEGER NOT NULL,
    data_emprestimo DATE NOT NULL,
    data_devolucao DATE NOT NULL,
    data_devolvido DATE,
    escola_id INTEGER NOT NULL,
    FOREIGN KEY (livro_id) REFERENCES livros (id),
    FOREIGN KEY (escola_id) REFERENCES escolas(id)
)
''')

# Insere algumas escolas iniciais se a tabela estiver vazia
cursor.execute('SELECT COUNT(*) FROM escolas')
if cursor.fetchone()[0] == 0:
    cursor.executemany('INSERT INTO escolas (nome, endereco, telefone) VALUES (?, ?, ?)', [
        ('Escola Municipal João da Silva', 'Rua A, 123', '(11) 1234-5678'),
        ('Escola Estadual Maria Santos', 'Av B, 456', '(11) 8765-4321')
    ])
    print('Escolas iniciais criadas')

# Cria o super administrador
senha_admin = criptografar_senha('admin123')
cursor.execute('''
    INSERT INTO usuarios (cpf, senha, tipo_usuario)
    VALUES (?, ?, ?)
''', ('01099080150', senha_admin, 'super_admin'))
print('\nSuper Administrador criado:')
print('CPF: 01099080150')
print('Senha: admin123')

# Insere um usuário inicial para cada escola se a tabela estiver vazia
cursor.execute('SELECT COUNT(*) FROM usuarios WHERE tipo_usuario = "escola"')
if cursor.fetchone()[0] == 0:
    senha_padrao = criptografar_senha('123456')
    # Pega os IDs das escolas criadas
    cursor.execute('SELECT id FROM escolas')
    escolas = cursor.fetchall()
    
    for idx, escola_id in enumerate(escolas, start=1):
        if idx == 1:
            cpf = '12345678910'
            senha = criptografar_senha('123456')
        else:
            cpf = f'admin{escola_id[0]}'
            senha = senha_padrao
        cursor.execute(
            'INSERT INTO usuarios (cpf, senha, escola_id, tipo_usuario) VALUES (?, ?, ?, ?)',
            (cpf, senha, escola_id[0], 'escola')
        )
    print('\nUsuários iniciais criados:')
    print('Para escola 1:')
    print('CPF: 12345678910')
    print('Senha: 123456')
    print('\nPara escola 2:')
    print('CPF: admin2')
    print('Senha: 123456')

# Commit das alterações e fecha a conexão
conn.commit()
conn.close()

print('\nBanco de dados inicializado com sucesso!') 