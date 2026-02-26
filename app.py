import os
from flask import Flask, render_template, request, jsonify, redirect, session, send_file
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import pandas as pd
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lava_rapido_secure_secret_2026")

# ---------- CONFIGURACOES DO BANCO DE DADOS ----------
# Esta parte agora tenta pegar a URL do banco do Render. 
# Se não encontrar (rodando local), usa suas configurações padrão.
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    try:
        if DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        else:
            DB_CONFIG = {
                "host": "localhost",
                "database": "lava_rapido_db",
                "user": "postgres",
                "password": "sua_senha_aqui",
                "port": 5432
            }
            conn = psycopg2.connect(**DB_CONFIG)
        
        conn.set_client_encoding('UTF8')
        
        # --- TRECHO NOVO: CRIA A TABELA AUTOMATICAMENTE SE NÃO EXISTIR ---
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lavagens (
                id SERIAL PRIMARY KEY,
                cliente VARCHAR(255) NOT NULL,
                marca VARCHAR(100),
                modelo VARCHAR(100),
                placa VARCHAR(20),
                tipo_lavagem VARCHAR(50),
                valor DECIMAL(10, 2),
                status_pagamento VARCHAR(20) DEFAULT 'Pendente',
                observacoes TEXT,
                data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cursor.close()
        # -------------------------------------------------------------
        
        return conn
    except Exception as e:
        print(f"Erro de conexao com o banco: {e}")
        return None

# ---------- DECORADOR DE AUTENTICACAO ----------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

# ---------- ROTAS DE AUTENTICACAO ----------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('usuario')
        password = request.form.get('senha')
        # Login simplificado conforme solicitado
        if username == 'admin' and password == '1234':
            session['user_id'] = 'admin'
            return redirect('/dashboard')
        else:
            return render_template('login.html', erro="Usuario ou senha invalidos")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------- DASHBOARD PRINCIPAL ----------
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')

# ---------- API - REGISTRO DE LAVAGENS ----------
@app.route('/api/lavagens', methods=['POST'])
@login_required
def registrar_lavagem():
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({"erro": "Falha na conexao com o banco"}), 500
    try:
        cursor = conn.cursor()

        cursor.execute("SET TIMEZONE TO 'America/Sao_Paulo';") # Ou o fuso horário desejado

        query = """
        INSERT INTO lavagens (cliente, marca, modelo, placa, tipo_lavagem,
        valor, status_pagamento, observacoes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data.get('cliente'),
            data.get('marca'),
            data.get('modelo'),
            data.get('placa').upper(),
            data.get('tipo_lavagem'),
            data.get('valor'),
            data.get('status_pagamento', 'Pendente'),
            data.get('observacoes', '')
        ))
        conn.commit()
        return jsonify({"mensagem": "Lavagem registrada com sucesso!"}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 400
    finally:
        conn.close()

# ---------- API - LISTAGEM DE LAVAGENS ----------
@app.route('/api/lavagens', methods=['GET'])
@login_required
def listar_lavagens():
    conn = get_db_connection()
    if not conn:
        return jsonify({"erro": "Falha na conexao com o banco"}), 500
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM lavagens ORDER BY data_registro DESC")
        lavagens = cursor.fetchall()
        # Formata datas para JSON
        for lavagem in lavagens:
            lavagem['data_registro'] = lavagem['data_registro'].strftime('%Y-%m-%d %H:%M:%S')
            lavagem['valor'] = float(lavagem['valor'])
        return jsonify(lavagens)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        conn.close()

# ---------- API - ATUALIZAR PAGAMENTO ----------
@app.route('/api/lavagens/<int:id>/pagar', methods=['PUT'])
@login_required
def atualizar_pagamento(id):
    conn = get_db_connection()
    if not conn:
        return jsonify({"erro": "Falha na conexao com o banco"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE lavagens SET status_pagamento = 'Pago' WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"mensagem": "Status de pagamento atualizado!"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        conn.close()

# ---------- API - EXCLUIR REGISTRO ----------
@app.route('/api/lavagens/<int:id>', methods=['DELETE'])
@login_required
def excluir_lavagem(id):
    conn = get_db_connection()
    if not conn:
        return jsonify({"erro": "Falha na conexao com o banco"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lavagens WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"mensagem": "Registro excluido com sucesso!"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        conn.close()

# ---------- EXPORTACAO EXCEL ----------
@app.route('/exportar')
@login_required
def exportar_excel():
    conn = get_db_connection()
    if not conn:
        return "Erro de conexao com o banco", 500
    try:
        df = pd.read_sql_query("SELECT * FROM lavagens", conn)
        filename = "relatorio_lavagens.xlsx"
        # Usar os.path.join para compatibilidade de SO e garantir que o diretório temporário exista
        temp_dir = '/tmp' # Ou outro diretório temporário adequado no seu ambiente
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        filepath = os.path.join(temp_dir, filename)
        df.to_excel(filepath, index=False)
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return f"Erro ao exportar: {e}", 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
