from flask import Flask, render_template, request, redirect, send_file, session, url_for
import sqlite3
import openpyxl
import os

app = Flask(__name__)
app.secret_key = 'chave_secreta_segura'

# -------------------- CONEXÃO --------------------
def get_db_connection():
    conn = sqlite3.connect('ferramentas.db')
    conn.row_factory = sqlite3.Row
    return conn

# -------------------- LOGIN --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        senha = request.form['senha']
        if senha == 'Geo@#07981':
            session['logado'] = True
            return redirect('/')
        else:
            return render_template('login.html', erro='Senha incorreta.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# -------------------- PÁGINA INICIAL --------------------
@app.route('/')
def index():
    try:
        conn = get_db_connection()
        ferramentas_estoque = conn.execute('SELECT * FROM ferramentas WHERE status = "estoque"').fetchall()
        ferramentas_uso = conn.execute('SELECT * FROM ferramentas WHERE status = "uso"').fetchall()
        conn.close()
        return render_template('index.html', ferramentas_estoque=ferramentas_estoque, ferramentas_uso=ferramentas_uso)
    except sqlite3.OperationalError as e:
        erro = str(e)
        return render_template('index.html', ferramentas_estoque=[], ferramentas_uso=[], erro=erro)

# -------------------- ADICIONAR --------------------
@app.route('/adicionar', methods=['POST'])
def adicionar():
    if not session.get('logado'):
        return redirect('/login')

    nome = request.form['nome']
    status = request.form['status']
    local = request.form['local']
    tecnico = request.form['tecnico']
    quantidade = int(request.form['quantidade'])
    idgeo = request.form['idgeo']

    conn = get_db_connection()
    existente = conn.execute('SELECT * FROM ferramentas WHERE nome = ? AND status = ?', (nome, status)).fetchone()

    if existente:
        nova_qtd = existente['quantidade'] + quantidade
        conn.execute('UPDATE ferramentas SET quantidade = ? WHERE id = ?', (nova_qtd, existente['id']))
    else:
        conn.execute('''INSERT INTO ferramentas (nome, status, local, tecnico, quantidade, idgeo)
                        VALUES (?, ?, ?, ?, ?, ?)''', (nome, status, local, tecnico, quantidade, idgeo))

    if status == 'uso':
        ferramenta_estoque = conn.execute('SELECT * FROM ferramentas WHERE nome = ? AND status = "estoque"', (nome,)).fetchone()
        if ferramenta_estoque:
            nova_qtd_estoque = ferramenta_estoque['quantidade'] - quantidade
            conn.execute('UPDATE ferramentas SET quantidade = ? WHERE id = ?', (nova_qtd_estoque, ferramenta_estoque['id']))

    conn.commit()
    conn.close()
    return redirect('/')

# -------------------- EDITAR --------------------
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if not session.get('logado'):
        return redirect('/login')

    conn = get_db_connection()
    ferramenta = conn.execute('SELECT * FROM ferramentas WHERE id = ?', (id,)).fetchone()

    if request.method == 'POST':
        nome = ferramenta['nome']
        status_anterior = ferramenta['status']
        quantidade_antiga = ferramenta['quantidade']
        novo_status = request.form['status']
        quantidade_nova = int(request.form['quantidade'])
        local = request.form['local']
        tecnico = request.form['tecnico']
        idgeo = request.form['idgeo']

        # Lógica de atualização
        if status_anterior == 'estoque' and novo_status == 'uso':
            existente_uso = conn.execute('''SELECT * FROM ferramentas 
                                             WHERE nome = ? AND status = 'uso' AND local = ? AND tecnico = ? AND idgeo = ?''',
                                             (nome, local, tecnico, idgeo)).fetchone()
            if existente_uso:
                nova_qtd = existente_uso['quantidade'] + quantidade_nova
                conn.execute('UPDATE ferramentas SET quantidade = ? WHERE id = ?', (nova_qtd, existente_uso['id']))
            else:
                conn.execute('''INSERT INTO ferramentas (nome, status, local, tecnico, quantidade, idgeo)
                                VALUES (?, 'uso', ?, ?, ?, ?)''', (nome, local, tecnico, quantidade_nova, idgeo))
            restante = quantidade_antiga - quantidade_nova
            conn.execute('UPDATE ferramentas SET quantidade = ? WHERE id = ?', (restante, id))

        elif status_anterior == 'uso' and novo_status == 'estoque':
            existente_estoque = conn.execute('SELECT * FROM ferramentas WHERE nome = ? AND status = "estoque"', (nome,)).fetchone()
            if existente_estoque:
                nova_qtd = existente_estoque['quantidade'] + quantidade_nova
                conn.execute('UPDATE ferramentas SET quantidade = ? WHERE id = ?', (nova_qtd, existente_estoque['id']))
                conn.execute('DELETE FROM ferramentas WHERE id = ?', (id,))
            else:
                conn.execute('''UPDATE ferramentas SET status = 'estoque', local = '', tecnico = '', idgeo = '' WHERE id = ?''', (id,))

        elif status_anterior == 'uso' and novo_status == 'uso':
            existente_uso = conn.execute('''SELECT * FROM ferramentas WHERE nome = ? AND status = 'uso' AND local = ? AND tecnico = ? AND idgeo = ?''',
                                         (nome, local, tecnico, idgeo)).fetchone()
            if existente_uso:
                nova_qtd = existente_uso['quantidade'] + quantidade_nova
                conn.execute('UPDATE ferramentas SET quantidade = ? WHERE id = ?', (nova_qtd, existente_uso['id']))
                conn.execute('DELETE FROM ferramentas WHERE id = ?', (id,))
            else:
                conn.execute('''UPDATE ferramentas SET local = ?, tecnico = ?, idgeo = ?, quantidade = ? WHERE id = ?''',
                             (local, tecnico, idgeo, quantidade_nova, id))

        else:
            conn.execute('''UPDATE ferramentas SET quantidade = ?, local = ?, tecnico = ?, idgeo = ? WHERE id = ?''',
                         (quantidade_nova, local, tecnico, idgeo, id))

        conn.commit()
        conn.close()
        return redirect('/')

    conn.close()
    return render_template('editar.html', ferramenta=ferramenta)

# -------------------- DELETAR --------------------
@app.route('/deletar/<int:id>')
def deletar(id):
    if not session.get('logado'):
        return redirect('/login')

    conn = get_db_connection()
    conn.execute('DELETE FROM ferramentas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/')

# -------------------- DEVOLVER --------------------
@app.route('/devolver/<int:id>')
def devolver(id):
    if not session.get('logado'):
        return redirect('/login')

    conn = get_db_connection()
    ferramenta = conn.execute('SELECT * FROM ferramentas WHERE id = ?', (id,)).fetchone()
    if ferramenta:
        existente = conn.execute('SELECT * FROM ferramentas WHERE nome = ? AND status = "estoque"', (ferramenta['nome'],)).fetchone()
        if existente:
            nova_qtd = existente['quantidade'] + ferramenta['quantidade']
            conn.execute('UPDATE ferramentas SET quantidade = ? WHERE id = ?', (nova_qtd, existente['id']))
            conn.execute('DELETE FROM ferramentas WHERE id = ?', (ferramenta['id'],))
        else:
            conn.execute('UPDATE ferramentas SET status = "estoque", local = "", tecnico = "", idgeo = "" WHERE id = ?', (ferramenta['id'],))

    conn.commit()
    conn.close()
    return redirect('/')

# -------------------- RELATÓRIOS --------------------
@app.route('/relatorios', methods=['GET'])
def relatorios():
    conn = get_db_connection()
    ferramenta = request.args.get('ferramenta', '').lower()
    tecnico = request.args.get('tecnico', '').lower()
    projeto = request.args.get('projeto', '').lower()
    idgeo = request.args.get('idgeo', '').lower()

    query = '''SELECT nome, quantidade, status, local, tecnico, idgeo FROM ferramentas WHERE status = 'uso' '''
    params = []
    if ferramenta:
        query += ' AND LOWER(nome) LIKE ?'
        params.append(f'%{ferramenta}%')
    if tecnico:
        query += ' AND LOWER(tecnico) LIKE ?'
        params.append(f'%{tecnico}%')
    if projeto:
        query += ' AND LOWER(local) LIKE ?'
        params.append(f'%{projeto}%')
    if idgeo:
        query += ' AND LOWER(idgeo) LIKE ?'
        params.append(f'%{idgeo}%')

    ferramentas = conn.execute(query, params).fetchall()
    nomes_ferramentas = [row['nome'] for row in conn.execute("SELECT DISTINCT nome FROM ferramentas WHERE status = 'uso'")]
    tecnicos = [row['tecnico'] for row in conn.execute("SELECT DISTINCT tecnico FROM ferramentas WHERE status = 'uso' AND tecnico != ''")]
    locais = [row['local'] for row in conn.execute("SELECT DISTINCT local FROM ferramentas WHERE status = 'uso' AND local != ''")]
    idgeos = [row['idgeo'] for row in conn.execute("SELECT DISTINCT idgeo FROM ferramentas WHERE status = 'uso' AND idgeo != ''")]

    conn.close()
    return render_template('relatorios.html', ferramentas=ferramentas, nomes_ferramentas=nomes_ferramentas, tecnicos=tecnicos, locais=locais, idgeos=idgeos)

# -------------------- RELATÓRIO ESTOQUE --------------------
@app.route('/relatorio_estoque', methods=['GET', 'POST'])
def relatorio_estoque():
    conn = get_db_connection()
    nome_filtro = ''
    if request.method == 'POST':
        nome_filtro = request.form.get('nome', '').lower()
        query = "SELECT nome, quantidade FROM ferramentas WHERE status = 'estoque'"
        params = []
        if nome_filtro:
            query += " AND LOWER(nome) LIKE ?"
            params.append(f"%{nome_filtro}%")
        ferramentas_estoque = conn.execute(query, params).fetchall()
    else:
        ferramentas_estoque = conn.execute("SELECT nome, quantidade FROM ferramentas WHERE status = 'estoque'").fetchall()

    nomes = [row['nome'] for row in conn.execute("SELECT DISTINCT nome FROM ferramentas WHERE status = 'estoque'")]
    conn.close()
    return render_template('relatorio_estoque.html', ferramentas_estoque=ferramentas_estoque, nomes=nomes)

# -------------------- EXPORTAÇÃO --------------------
@app.route('/exportar_excel')
def exportar_excel():
    ferramenta = request.args.get('ferramenta', '').lower()
    tecnico = request.args.get('tecnico', '').lower()
    projeto = request.args.get('projeto', '').lower()
    idgeo = request.args.get('idgeo', '').lower()

    query = '''SELECT nome, quantidade, status, local, tecnico, idgeo FROM ferramentas WHERE status = 'uso' '''
    params = []
    if ferramenta:
        query += ' AND LOWER(nome) LIKE ?'
        params.append(f'%{ferramenta}%')
    if tecnico:
        query += ' AND LOWER(tecnico) LIKE ?'
        params.append(f'%{tecnico}%')
    if projeto:
        query += ' AND LOWER(local) LIKE ?'
        params.append(f'%{projeto}%')
    if idgeo:
        query += ' AND LOWER(idgeo) LIKE ?'
        params.append(f'%{idgeo}%')

    conn = sqlite3.connect('ferramentas.db')
    cursor = conn.cursor()
    dados = cursor.execute(query, params).fetchall()
    conn.close()

    if not dados:
        return "Nenhum dado encontrado para exportar."

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Nome", "Quantidade", "Status", "Projeto", "Técnico", "IDGEO"])
    for linha in dados:
        ws.append(linha)

    nome_arquivo = "relatorio_projetos.xlsx"
    wb.save(nome_arquivo)
    return send_file(nome_arquivo, as_attachment=True)

@app.route('/exportar_estoque')
def exportar_estoque():
    conn = get_db_connection()
    ferramentas = conn.execute('SELECT * FROM ferramentas WHERE status = "estoque"').fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Estoque'
    ws.append(['ID', 'Nome', 'Quantidade', 'Local', 'Técnico', 'IDGEO'])
    for f in ferramentas:
        ws.append([f['id'], f['nome'], f['quantidade'], f['local'], f['tecnico'], f['idgeo']])

    caminho_arquivo = os.path.join(os.path.expanduser("~"), "relatorio_estoque.xlsx")
    wb.save(caminho_arquivo)
    return send_file(caminho_arquivo, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

#  git add .
#  git commit -m "Programa funcionando com servidor e senha"
#  git push