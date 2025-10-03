from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'chave_muito_secreta_para_flash' 

# --- Configuração do Banco de Dados ---
NOME_DO_BANCO = "cadastro_moderno_completo.db"

def conectar_banco():
    return sqlite3.connect(NOME_DO_BANCO)

def criar_tabela():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pessoas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            idade TEXT,
            email TEXT UNIQUE NOT NULL,
            telefone TEXT,
            cidade TEXT
        );
    """)
    conn.commit()
    conn.close()

# Garante que a tabela seja criada ao iniciar o app
criar_tabela()


# --- Rotas da Aplicação ---

@app.route('/', methods=['GET', 'POST'])
def index():
    """C: Rota para o cadastro de novas pessoas (Create)."""
    if request.method == 'POST':
        nome = request.form.get('nome').strip().title()
        idade = request.form.get('idade').strip()
        email = request.form.get('email').strip().lower()
        telefone = request.form.get('telefone').strip()
        cidade = request.form.get('cidade').strip().title()
        
        if not nome or not email:
            flash('Nome e E-mail são obrigatórios!', 'error')
            return redirect(url_for('index'))

        try:
            conn = conectar_banco()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pessoas (nome, idade, email, telefone, cidade)
                VALUES (?, ?, ?, ?, ?);
            """, (nome, idade, email, telefone, cidade))
            conn.commit()
            flash(f'Pessoa "{nome}" cadastrada com sucesso!', 'success')
            
        except sqlite3.IntegrityError:
            flash(f'Erro: O e-mail "{email}" já está cadastrado.', 'error')
            
        except Exception as e:
            flash(f'Erro inesperado ao salvar: {e}', 'error')
            
        finally:
            if conn: conn.close()
            
        return redirect(url_for('index'))
        
    return render_template('index.html')


@app.route('/buscar', methods=['GET'])
def buscar():
    """R: Rota para a busca de pessoas (Read)."""
    query = request.args.get('query', '').strip()
    resultados = []

    if query:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, nome, idade, email, telefone, cidade FROM pessoas WHERE nome LIKE ?", 
                       ('%' + query + '%',))
        
        resultados = cursor.fetchall()
        conn.close()

        if not resultados:
             flash(f'Nenhum resultado encontrado para "{query}".', 'info')

    return render_template('busca.html', resultados=resultados, query=query)


@app.route('/deletar_selecionados', methods=['POST'])
def deletar_selecionados():
    """D: Rota para deletar múltiplos registros (Delete)."""
    
    ids_para_deletar = request.form.getlist('selecionados') 
    query_origem = request.form.get('query_origem', '')
    
    if not ids_para_deletar:
        flash('Nenhum registro foi selecionado para exclusão.', 'info')
        return redirect(url_for('buscar', query=query_origem))

    conn = None
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        
        placeholders = ', '.join('?' * len(ids_para_deletar))
        
        # 1. Busca os nomes antes de deletar (para a mensagem de sucesso)
        cursor.execute(f"SELECT nome FROM pessoas WHERE id IN ({placeholders})", ids_para_deletar)
        nomes_deletados = [row[0] for row in cursor.fetchall()]

        # 2. Deleta os registros
        cursor.execute(f"DELETE FROM pessoas WHERE id IN ({placeholders})", ids_para_deletar)
        conn.commit()
        
        num_deletados = len(nomes_deletados)
        flash(f'{num_deletados} registros foram excluídos ({", ".join(nomes_deletados)}).', 'success')
        
    except Exception as e:
        flash(f'Erro ao deletar os registros: {e}', 'error')
        
    finally:
        if conn:
            conn.close()
            
    return redirect(url_for('buscar', query=query_origem))


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    """U: Rota para carregar e salvar a edição de um registro (Update)."""
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # --- Rota POST (Salvar as Alterações) ---
    if request.method == 'POST':
        nome = request.form.get('nome').strip().title()
        idade = request.form.get('idade').strip()
        email = request.form.get('email').strip().lower()
        telefone = request.form.get('telefone').strip()
        cidade = request.form.get('cidade').strip().title()
        
        if not nome or not email:
            flash('Nome e E-mail são obrigatórios!', 'error')
            conn.close()
            return redirect(url_for('editar', id=id)) 
        
        try:
            cursor.execute("""
                UPDATE pessoas 
                SET nome = ?, idade = ?, email = ?, telefone = ?, cidade = ?
                WHERE id = ?;
            """, (nome, idade, email, telefone, cidade, id))
            
            conn.commit()
            flash(f'Registro ID {id} de "{nome}" atualizado com sucesso!', 'success')
            return redirect(url_for('buscar'))
            
        except sqlite3.IntegrityError:
            flash(f'Erro: O e-mail "{email}" já está cadastrado em outro registro.', 'error')
            return redirect(url_for('editar', id=id))
            
        except Exception as e:
            flash(f'Erro inesperado ao atualizar: {e}', 'error')
            return redirect(url_for('editar', id=id))
            
        finally:
            conn.close()

    # --- Rota GET (Carregar o Registro) ---
    else:
        cursor.execute("SELECT id, nome, idade, email, telefone, cidade FROM pessoas WHERE id = ?", (id,))
        pessoa = cursor.fetchone()
        conn.close()

        if pessoa is None:
            flash(f'Registro ID {id} não encontrado.', 'error')
            return redirect(url_for('buscar'))
            
        # O resultado (pessoa) é passado para preencher o formulário
        return render_template('editar.html', pessoa=pessoa)


