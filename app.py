from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3  # Corrigido de sqlite
import hashlib
import pandas as pd
from fpdf import FPDF
import io  # Corrigido de lo
from xhtml2pdf import pisa

app = Flask(__name__)

# Restante do seu código...
app.secret_key = 'biblioteca_secret_key'  # Chave secreta para sessões

# Função para conectar ao banco
def get_db_connection():
    conn = sqlite3.connect('database_new.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para criptografar senhas
def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# Página de login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        cpf = request.form['cpf']
        senha = request.form['senha']
        senha_criptografada = criptografar_senha(senha)

        conn = get_db_connection()
        # Primeiro verifica se é o administrador geral
        admin = conn.execute('''
            SELECT cpf, tipo_usuario 
            FROM usuarios 
            WHERE cpf = ? AND senha = ? AND tipo_usuario = 'super_admin'
        ''', (cpf, senha_criptografada)).fetchone()

        if admin:
            session['usuario_cpf'] = admin['cpf']
            session['tipo_usuario'] = admin['tipo_usuario']
            flash('Bem-vindo Administrador Geral!', 'success')
            return redirect(url_for('index'))
        
        # Se não for admin, verifica usuário normal
        usuario = conn.execute('''
            SELECT u.cpf, u.escola_id, e.nome as escola_nome, u.tipo_usuario
            FROM usuarios u 
            JOIN escolas e ON u.escola_id = e.id 
            WHERE u.cpf = ? AND u.senha = ?
        ''', (cpf, senha_criptografada)).fetchone()
        conn.close()

        if usuario:
            session['usuario_cpf'] = usuario['cpf']
            session['escola_id'] = usuario['escola_id']
            session['escola_nome'] = usuario['escola_nome']
            session['tipo_usuario'] = usuario['tipo_usuario']
            flash(f'Bem-vindo! Você está conectado à {usuario["escola_nome"]}', 'success')
            return redirect(url_for('index'))
        else:
            flash('CPF ou Senha inválidos!')

    return render_template('login.html')

# Tela inicial depois de logado
@app.route('/index')
def index():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', usuario_cpf=session['usuario_cpf'])

# Tela de cadastro de novos usuários
@app.route('/cadastro_usuario', methods=['GET', 'POST'])
def cadastro_usuario():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        cpf = request.form['cpf']
        senha = request.form['senha']
        senha_criptografada = criptografar_senha(senha)
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verifica se o CPF já existe
        cursor.execute('SELECT * FROM usuarios WHERE cpf = ?', (cpf,))
        usuario = cursor.fetchone()

        if usuario:
            flash('CPF já cadastrado!')
        else:
            cursor.execute('INSERT INTO usuarios (cpf, senha) VALUES (?, ?)', (cpf, senha_criptografada))
            conn.commit()
            flash('Usuário cadastrado com sucesso!')

        conn.close()
    
    return render_template('cadastro_usuario.html', usuario_cpf=session.get('usuario_cpf'))


# Tela de alterar senha
@app.route('/alterar_senha', methods=['GET', 'POST'])
def alterar_senha():
    if request.method == 'POST':
        cpf = request.form.get('cpf')
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')

        # Remove formatação do CPF
        if cpf:
            cpf = cpf.replace('.', '').replace('-', '')

        # Se o CPF e senha atual foram fornecidos, verifica as credenciais
        if cpf and senha_atual and not nova_senha:
            senha_atual_criptografada = criptografar_senha(senha_atual)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM usuarios WHERE cpf = ? AND senha = ?', 
                         (cpf, senha_atual_criptografada))
            usuario = cursor.fetchone()
            conn.close()

            if usuario:
                session['temp_cpf'] = cpf  # Armazena o CPF temporariamente
                flash('Credenciais verificadas. Por favor, digite sua nova senha.', 'success')
                return render_template('alterar_senha.html', verificado=True)
            else:
                flash('CPF ou senha atual incorretos.')
                return render_template('alterar_senha.html', verificado=False)

        # Se a nova senha foi fornecida, processa a alteração
        elif nova_senha and confirmar_senha and 'temp_cpf' in session:
            if nova_senha == confirmar_senha:
                nova_senha_criptografada = criptografar_senha(nova_senha)
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE usuarios SET senha = ? WHERE cpf = ?', 
                             (nova_senha_criptografada, session['temp_cpf']))
                conn.commit()
                conn.close()
                
                session.pop('temp_cpf', None)  # Remove o CPF temporário
                flash('Senha alterada com sucesso!', 'success')
                return redirect(url_for('index'))
            else:
                flash('A nova senha e a confirmação não coincidem.')
                return render_template('alterar_senha.html', verificado=True)

    return render_template('alterar_senha.html', verificado=False)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Cadastro e listagem de livros
@app.route('/livros', methods=['GET', 'POST'])
def livros():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    if request.method == 'POST':
        # Obtém os campos obrigatórios
        titulo = request.form['titulo']
        autor = request.form['autor']
        
        # Obtém os campos opcionais com valores padrão
        editora = request.form.get('editora', '')
        ano = request.form.get('ano', '')
        categoria = request.form.get('categoria', '')
        quantidade = request.form.get('quantidade', '0')
        localizacao = request.form.get('localizacao', '')
        codigo_interno = request.form.get('codigo_interno', '')
        observacoes = request.form.get('observacoes', '')

        # Converte quantidade para número se estiver vazio
        if quantidade == '':
            quantidade = '0'

        escola_id = session.get('escola_id')
        conn.execute('''
            INSERT INTO livros (
                titulo, autor, editora, ano, categoria,
                quantidade, localizacao, codigo_interno, observacoes, disponivel, escola_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        ''', (titulo, autor, editora, ano, categoria, quantidade, localizacao, codigo_interno, observacoes, escola_id))
        
        conn.commit()
        flash('Livro cadastrado com sucesso!', 'success')
        return redirect(url_for('livros'))

    # Verifica se é administrador geral
    if session.get('tipo_usuario') == 'super_admin':
        # Busca todos os livros de todas as escolas
        livros = conn.execute('''
            SELECT l.*, e.nome as escola_nome 
            FROM livros l 
            JOIN escolas e ON l.escola_id = e.id
        ''').fetchall()
    else:
        # Busca apenas os livros da escola do usuário
        escola_id = session.get('escola_id')
        livros = conn.execute('''
            SELECT l.*, e.nome as escola_nome 
            FROM livros l 
            JOIN escolas e ON l.escola_id = e.id 
            WHERE l.escola_id = ?
        ''', (escola_id,)).fetchall()
    
    conn.close()
    return render_template('livros.html', livros=livros, usuario_cpf=session['usuario_cpf'])

# Excluir livro
@app.route('/excluir_livro/<int:id>')
def excluir_livro(id):
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM livros WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('livros'))

# Cadastro e listagem de empréstimos
@app.route('/emprestimos', methods=['GET', 'POST'])
def emprestimos():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    if request.method == 'POST':
        # Obtém os campos do formulário
        aluno = request.form['aluno']
        turma = request.form['turma']
        telefone = request.form.get('telefone', '')
        livro_id = request.form['livro_id']
        data_emprestimo = request.form['data_emprestimo']
        data_devolucao = request.form['data_devolucao']
        escola_id = session.get('escola_id')

        # Insere o empréstimo
        conn.execute('''
            INSERT INTO emprestimos (
                aluno, turma, telefone, livro_id, 
                data_emprestimo, data_devolucao, escola_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (aluno, turma, telefone, livro_id, data_emprestimo, data_devolucao, escola_id))
        
        # Atualiza o status do livro para indisponível
        conn.execute('UPDATE livros SET disponivel = 0 WHERE id = ?', (livro_id,))
        
        conn.commit()
        flash('Empréstimo cadastrado com sucesso!', 'success')
        return redirect(url_for('emprestimos'))

    # Verifica se é administrador geral
    if session.get('tipo_usuario') == 'super_admin':
        # Busca todos os empréstimos de todas as escolas
        emprestimos = conn.execute('''
            SELECT e.*, l.titulo as livro_titulo, es.nome as escola_nome
            FROM emprestimos e
            JOIN livros l ON e.livro_id = l.id
            JOIN escolas es ON e.escola_id = es.id
            WHERE e.data_devolvido IS NULL
            ORDER BY e.data_emprestimo DESC
        ''').fetchall()
    else:
        # Busca apenas os empréstimos da escola do usuário
        escola_id = session.get('escola_id')
        emprestimos = conn.execute('''
            SELECT e.*, l.titulo as livro_titulo, es.nome as escola_nome
            FROM emprestimos e
            JOIN livros l ON e.livro_id = l.id
            JOIN escolas es ON e.escola_id = es.id
            WHERE e.escola_id = ? AND e.data_devolvido IS NULL
            ORDER BY e.data_emprestimo DESC
        ''', (escola_id,)).fetchall()
    
    # Busca os livros disponíveis para o formulário
    if session.get('tipo_usuario') == 'super_admin':
        livros = conn.execute('''
            SELECT l.*, es.nome as escola_nome
            FROM livros l
            JOIN escolas es ON l.escola_id = es.id
            WHERE l.disponivel = 1
        ''').fetchall()
    else:
        escola_id = session.get('escola_id')
        livros = conn.execute('''
            SELECT l.*, es.nome as escola_nome
            FROM livros l
            JOIN escolas es ON l.escola_id = es.id
            WHERE l.escola_id = ? AND l.disponivel = 1
        ''', (escola_id,)).fetchall()
    
    conn.close()
    return render_template('emprestimos.html', emprestimos=emprestimos, livros=livros, usuario_cpf=session['usuario_cpf'])

# Baixar empréstimo (devolução)
@app.route('/baixar_emprestimo/<int:id>', methods=['POST'])
def baixar_emprestimo(id):
    # Verifica se o usuário está logado
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    # Recupera a escola logada
    escola_id = session.get('escola_id')

    # Abre conexão com o banco e busca o empréstimo
    conn = get_db_connection()
    emprestimo = conn.execute('SELECT * FROM emprestimos WHERE id = ?', (id,)).fetchone()

    # Verifica se o empréstimo existe e pertence à escola logada
    if not emprestimo or emprestimo['escola_id'] != escola_id:
        conn.close()
        flash('Acesso não autorizado ao empréstimo.', 'error')
        return redirect(url_for('emprestimos'))

    # Continua o processo de devolução
    data_devolvido = request.form['data_devolvido']

    conn.execute('UPDATE emprestimos SET data_devolvido = ? WHERE id = ?', (data_devolvido, id))
    conn.execute('UPDATE livros SET disponivel = 1 WHERE id = (SELECT livro_id FROM emprestimos WHERE id = ?)', (id,))

    conn.commit()
    conn.close()

    flash('Empréstimo baixado com sucesso!', 'success')
    return redirect(url_for('emprestimos'))


# Excluir empréstimo
@app.route('/excluir_emprestimo/<int:id>')
def excluir_emprestimo(id):
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM emprestimos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('emprestimos'))

# Tela de relatórios principal
@app.route('/relatorios')
def relatorios():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
    return render_template('relatorios.html', usuario_cpf=session['usuario_cpf'])

# Relatório de livros
@app.route('/relatorios/livros')
def livros_relatorio():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    escola_id = session.get('escola_id')
    conn = get_db_connection()
    livros = conn.execute('SELECT * FROM livros WHERE escola_id = ?', (escola_id,)).fetchall()
    conn.close()
    return render_template('livros_relatorio.html', livros=livros, usuario_cpf=session['usuario_cpf'])

@app.route('/exportar_livros_excel')
def exportar_livros_excel():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    escola_id = session.get('escola_id')
    conn = get_db_connection()
    livros = conn.execute('SELECT * FROM livros WHERE escola_id = ?', (escola_id,)).fetchall()
    conn.close()

    # Converter os resultados para lista de dicionários
    dados = []
    for livro in livros:
        dados.append({
            'ID': livro['id'],
            'Título': livro['titulo'],
            'Autor': livro['autor'],
            'Editora': livro['editora'],
            'Ano': livro['ano'],
            'Categoria': livro['categoria'],
            'Quantidade': livro['quantidade'],
            'Localização': livro['localizacao'],
            'Código Interno': livro['codigo_interno'],
            'Observações': livro['observacoes'],
            'Disponível': 'Sim' if livro['disponivel'] else 'Não'
        })

    df = pd.DataFrame(dados)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'livros_escola_{escola_id}.xlsx'
    )

@app.route('/exportar_livros_pdf')
def exportar_livros_pdf():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    escola_id = session.get('escola_id')
    escola_nome = session.get('escola_nome', 'Escola')
    
    conn = get_db_connection()
    livros = conn.execute('SELECT * FROM livros WHERE escola_id = ?', (escola_id,)).fetchall()
    conn.close()

    html = f"""
    <h1 style='text-align: center;'>Relatório de Livros - {escola_nome}</h1>
    <table border='1' cellspacing='0' cellpadding='5' style='width: 100%; border-collapse: collapse;'>
        <tr style='background-color: #f2f2f2;'>
            <th>ID</th>
            <th>Título</th>
            <th>Autor</th>
            <th>Editora</th>
            <th>Ano</th>
            <th>Categoria</th>
            <th>Quantidade</th>
            <th>Localização</th>
            <th>Código</th>
            <th>Observações</th>
            <th>Disponível</th>
        </tr>
    """
    
    for livro in livros:
        disponivel = 'Sim' if livro['disponivel'] else 'Não'
        html += f"""
        <tr>
            <td>{livro['id']}</td>
            <td>{livro['titulo']}</td>
            <td>{livro['autor']}</td>
            <td>{livro['editora']}</td>
            <td>{livro['ano']}</td>
            <td>{livro['categoria']}</td>
            <td>{livro['quantidade']}</td>
            <td>{livro['localizacao']}</td>
            <td>{livro['codigo_interno']}</td>
            <td>{livro['observacoes']}</td>
            <td>{disponivel}</td>
        </tr>
        """
    html += "</table>"

    # Adicionar CSS para melhorar a aparência
    html = f"""
    <style>
        @page {{
            size: landscape;
            margin: 1cm;
        }}
        table {{
            font-family: Arial, sans-serif;
            font-size: 12px;
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background-color: #f2f2f2;
            padding: 8px;
            text-align: left;
        }}
        td {{
            padding: 8px;
            border: 1px solid #ddd;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        h1 {{
            font-family: Arial, sans-serif;
            color: #333;
            margin-bottom: 20px;
        }}
    </style>
    {html}
    """

    pdf_stream = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=pdf_stream)
    pdf_stream.seek(0)

    return send_file(
        pdf_stream,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'livros_escola_{escola_id}.pdf'
    )

# Relatório de empréstimos em curso
@app.route('/relatorios/emprestimos_curso')
def emprestimos_curso():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    escola_id = session.get('escola_id')
    conn = get_db_connection()
    emprestimos = conn.execute('''
        SELECT e.*, l.titulo FROM emprestimos e
        JOIN livros l ON e.livro_id = l.id
        WHERE e.data_devolvido IS NULL AND e.escola_id = ?
    ''', (escola_id,)).fetchall()
    conn.close()
    return render_template('emprestimos_curso.html', emprestimos=emprestimos, usuario_cpf=session['usuario_cpf'])


# Relatório de empréstimos devolvidos
@app.route('/relatorios/emprestimos_devolvidos')
def emprestimos_devolvidos():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    escola_id = session.get('escola_id')
    conn = get_db_connection()
    emprestimos = conn.execute('''
        SELECT e.*, l.titulo FROM emprestimos e
        JOIN livros l ON e.livro_id = l.id
        WHERE e.data_devolvido IS NOT NULL AND e.escola_id = ?
    ''', (escola_id,)).fetchall()
    conn.close()
    return render_template('emprestimos_devolvidos.html', emprestimos=emprestimos, usuario_cpf=session['usuario_cpf'])

def formatar_data(data):
    if not data:
        return ''
    partes = data.split('-')
    if len(partes) != 3:
        return data
    return f"{partes[2]}/{partes[1]}/{partes[0]}"

@app.route('/exportar_emprestimos_curso_excel')
def exportar_emprestimos_curso_excel():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    escola_id = session.get('escola_id')
    conn = get_db_connection()
    emprestimos = conn.execute('''
        SELECT e.aluno, e.turma, e.telefone, l.titulo, e.data_emprestimo, e.data_devolucao 
        FROM emprestimos e
        JOIN livros l ON e.livro_id = l.id
        WHERE e.data_devolvido IS NULL AND e.escola_id = ?
    ''', (escola_id,)).fetchall()
    conn.close()

    # Converter os resultados para lista de dicionários
    dados = []
    for e in emprestimos:
        dados.append({
            'Aluno': e[0],
            'Turma': e[1],
            'Telefone': e[2],
            'Livro': e[3],
            'Data Empréstimo': formatar_data(e[4]),
            'Data para Devolução': formatar_data(e[5])
        })

    df = pd.DataFrame(dados)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'emprestimos_curso_escola_{escola_id}.xlsx'
    )

@app.route('/exportar_emprestimos_curso_pdf')
def exportar_emprestimos_curso_pdf():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    escola_id = session.get('escola_id')
    escola_nome = session.get('escola_nome', 'Escola')
    
    conn = get_db_connection()
    emprestimos = conn.execute('''
        SELECT e.aluno, e.turma, e.telefone, l.titulo, e.data_emprestimo, e.data_devolucao 
        FROM emprestimos e
        JOIN livros l ON e.livro_id = l.id
        WHERE e.data_devolvido IS NULL AND e.escola_id = ?
    ''', (escola_id,)).fetchall()
    conn.close()

    html = f"""
    <h1 style='text-align: center;'>Relatório de Empréstimos em Curso - {escola_nome}</h1>
    <table border='1' cellspacing='0' cellpadding='5' style='width: 100%; border-collapse: collapse;'>
        <tr style='background-color: #f2f2f2;'>
            <th>Aluno</th>
            <th>Turma</th>
            <th>Telefone</th>
            <th>Livro</th>
            <th>Data Empréstimo</th>
            <th>Data para Devolução</th>
        </tr>
    """
    
    for e in emprestimos:
        html += f"""
        <tr>
            <td>{e[0]}</td>
            <td>{e[1]}</td>
            <td>{e[2]}</td>
            <td>{e[3]}</td>
            <td>{formatar_data(e[4])}</td>
            <td>{formatar_data(e[5])}</td>
        </tr>
        """
    html += "</table>"

    # Adicionar CSS para melhorar a aparência
    html = f"""
    <style>
        @page {{
            size: landscape;
            margin: 1cm;
        }}
        table {{
            font-family: Arial, sans-serif;
            font-size: 12px;
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background-color: #f2f2f2;
            padding: 8px;
            text-align: left;
        }}
        td {{
            padding: 8px;
            border: 1px solid #ddd;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        h1 {{
            font-family: Arial, sans-serif;
            color: #333;
            margin-bottom: 20px;
        }}
    </style>
    {html}
    """

    pdf_stream = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=pdf_stream)
    pdf_stream.seek(0)

    return send_file(
        pdf_stream,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'emprestimos_curso_escola_{escola_id}.pdf'
    )

@app.route('/exportar_emprestimos_devolvidos_excel')
def exportar_emprestimos_devolvidos_excel():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    escola_id = session.get('escola_id')
    conn = get_db_connection()
    emprestimos = conn.execute('''
        SELECT e.aluno, e.turma, e.telefone, l.titulo, e.data_emprestimo, e.data_devolucao, e.data_devolvido
        FROM emprestimos e
        JOIN livros l ON e.livro_id = l.id
        WHERE e.data_devolvido IS NOT NULL AND e.escola_id = ?
    ''', (escola_id,)).fetchall()
    conn.close()

    # Converter os resultados para lista de dicionários
    dados = []
    for e in emprestimos:
        dados.append({
            'Aluno': e[0],
            'Turma': e[1],
            'Telefone': e[2],
            'Livro': e[3],
            'Data Empréstimo': formatar_data(e[4]),
            'Data para Devolução': formatar_data(e[5]),
            'Data Devolvido': formatar_data(e[6])
        })

    df = pd.DataFrame(dados)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'emprestimos_devolvidos_escola_{escola_id}.xlsx'
    )

@app.route('/exportar_emprestimos_devolvidos_pdf')
def exportar_emprestimos_devolvidos_pdf():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    escola_id = session.get('escola_id')
    escola_nome = session.get('escola_nome', 'Escola')
    
    conn = get_db_connection()
    emprestimos = conn.execute('''
        SELECT e.aluno, e.turma, e.telefone, l.titulo, e.data_emprestimo, e.data_devolucao, e.data_devolvido 
        FROM emprestimos e
        JOIN livros l ON e.livro_id = l.id
        WHERE e.data_devolvido IS NOT NULL AND e.escola_id = ?
    ''', (escola_id,)).fetchall()
    conn.close()

    html = f"""
    <h1 style='text-align: center;'>Relatório de Empréstimos Devolvidos - {escola_nome}</h1>
    <table border='1' cellspacing='0' cellpadding='5' style='width: 100%; border-collapse: collapse;'>
        <tr style='background-color: #f2f2f2;'>
            <th>Aluno</th>
            <th>Turma</th>
            <th>Telefone</th>
            <th>Livro</th>
            <th>Data Empréstimo</th>
            <th>Data para Devolução</th>
            <th>Data Devolvido</th>
        </tr>
    """
    
    for e in emprestimos:
        html += f"""
        <tr>
            <td>{e[0]}</td>
            <td>{e[1]}</td>
            <td>{e[2]}</td>
            <td>{e[3]}</td>
            <td>{formatar_data(e[4])}</td>
            <td>{formatar_data(e[5])}</td>
            <td>{formatar_data(e[6])}</td>
        </tr>
        """
    html += "</table>"

    # Adicionar CSS para melhorar a aparência
    html = f"""
    <style>
        @page {{
            size: landscape;
            margin: 1cm;
        }}
        table {{
            font-family: Arial, sans-serif;
            font-size: 12px;
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background-color: #f2f2f2;
            padding: 8px;
            text-align: left;
        }}
        td {{
            padding: 8px;
            border: 1px solid #ddd;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        h1 {{
            font-family: Arial, sans-serif;
            color: #333;
            margin-bottom: 20px;
        }}
    </style>
    {html}
    """

    pdf_stream = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=pdf_stream)
    pdf_stream.seek(0)

    return send_file(
        pdf_stream,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'emprestimos_devolvidos_escola_{escola_id}.pdf'
    )

@app.route('/relatorio_excel')
def relatorio_excel():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))

    escola_id = session.get('escola_id')
    conn = get_db_connection()

    emprestimos = conn.execute('''
        SELECT e.id, e.aluno, e.turma, e.telefone, l.titulo AS livro,
               e.data_emprestimo, e.data_devolucao
        FROM emprestimos e
        JOIN livros l ON e.livro_id = l.id
        WHERE e.escola_id = ?
    ''', (escola_id,)).fetchall()

    conn.close()

    # Converte os dados para DataFrame
    df = pd.DataFrame(emprestimos, columns=[
        'ID', 'Aluno', 'Turma', 'Telefone', 'Livro',
        'Data do Empréstimo', 'Data da Devolução'
    ])

    # Gera o Excel em memória
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Empréstimos')

    output.seek(0)

    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     download_name='relatorio_emprestimos.xlsx',
                     as_attachment=True)

# Gerenciar escolas
@app.route('/gerenciar_escolas')
def gerenciar_escolas():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
        
    if session.get('tipo_usuario') != 'super_admin':
        flash('Apenas o administrador geral pode gerenciar escolas!', 'error')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    escolas = conn.execute('SELECT * FROM escolas').fetchall()
    conn.close()
    
    return render_template('gerenciar_escolas.html', escolas=escolas)

# Gerenciar usuários
@app.route('/gerenciar_usuarios')
def gerenciar_usuarios():
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
        
    if session.get('tipo_usuario') != 'super_admin':
        flash('Apenas o administrador geral pode gerenciar usuários!', 'error')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    usuarios = conn.execute('''
        SELECT u.*, e.nome as escola_nome 
        FROM usuarios u 
        LEFT JOIN escolas e ON u.escola_id = e.id
    ''').fetchall()
    conn.close()
    
    return render_template('gerenciar_usuarios.html', usuarios=usuarios)

# Excluir usuário
@app.route('/excluir_usuario/<cpf>')
def excluir_usuario(cpf):
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
        
    if session.get('tipo_usuario') != 'super_admin':
        flash('Apenas o administrador geral pode excluir usuários!', 'error')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    try:
        # Verifica se o usuário existe
        usuario = conn.execute('SELECT * FROM usuarios WHERE cpf = ?', (cpf,)).fetchone()
        if not usuario:
            flash('Usuário não encontrado!', 'error')
            return redirect(url_for('index'))
            
        # Não permite excluir o super admin
        if usuario['tipo_usuario'] == 'super_admin':
            flash('Não é possível excluir o administrador geral!', 'error')
            return redirect(url_for('index'))
            
        # Exclui o usuário
        conn.execute('DELETE FROM usuarios WHERE cpf = ?', (cpf,))
        conn.commit()
        flash('Usuário excluído com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir usuário: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('gerenciar_usuarios'))

# Excluir escola
@app.route('/excluir_escola/<int:id>')
def excluir_escola(id):
    if 'usuario_cpf' not in session:
        return redirect(url_for('login'))
        
    if session.get('tipo_usuario') != 'super_admin':
        flash('Apenas o administrador geral pode excluir escolas!', 'error')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    try:
        # Verifica se a escola existe
        escola = conn.execute('SELECT * FROM escolas WHERE id = ?', (id,)).fetchone()
        if not escola:
            flash('Escola não encontrada!', 'error')
            return redirect(url_for('index'))
            
        # Exclui todos os usuários da escola
        conn.execute('DELETE FROM usuarios WHERE escola_id = ?', (id,))
        
        # Exclui todos os livros da escola
        conn.execute('DELETE FROM livros WHERE escola_id = ?', (id,))
        
        # Exclui todos os empréstimos da escola
        conn.execute('DELETE FROM emprestimos WHERE escola_id = ?', (id,))
        
        # Exclui a escola
        conn.execute('DELETE FROM escolas WHERE id = ?', (id,))
        
        conn.commit()
        flash('Escola e todos os seus dados foram excluídos com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir escola: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('gerenciar_escolas'))

# Rodar o servidor
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
