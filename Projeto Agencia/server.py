"""
Servidor Flask do dashboard da agencia.
- GET /          → Dashboard completo
- POST /upload   → Upload de arquivo .xlsx
- DELETE /api/files/<name> → Remove um arquivo
- GET /api/data  → Dados em JSON (para charts)
- POST /api/login → Login (cria sessão)
- POST /api/logout → Logout
- GET /api/me → Usuário atual
- GET /api/users → Listar usuários (admin)
- POST /api/users → Criar usuário (admin)
- PUT /api/users/<username>/role → Alterar papel
- PUT /api/users/<username>/password → Resetar senha
- DELETE /api/users/<username> → Remover usuário
"""
from flask import Flask, request, jsonify, send_from_directory, session
import os, json, datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# Adiciona a raiz do projeto ao path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Persistência de arquivos (anexar sem sobrescrever)
from persist.filelib import append_text, append_csv

from app.gerar_dashboard import load_all_data, compute_kpis, parse_xlsx
from app.models import db, User

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(PROJECT_DIR)

app = Flask(__name__, static_folder=ROOT_DIR, template_folder='templates')
app.config['UPLOAD_FOLDER'] = os.path.join(PROJECT_DIR, 'dados')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ju-basilio-secret-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(PROJECT_DIR, 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24 * 7  # 1 semana

db.init_app(app)

# Arquivo JSON para metadados de upload (quem fez upload de cada arquivo)
UPLOAD_META_FILE = os.path.join(app.config['UPLOAD_FOLDER'], 'upload_metadata.json')

def load_upload_meta():
    """Carrega metadados de uploads."""
    if not os.path.exists(UPLOAD_META_FILE):
        return {}
    try:
        with open(UPLOAD_META_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print('Erro ao ler metadados de upload:', e)
        return {}

def save_upload_meta(meta):
    """Salva metadados de uploads."""
    try:
        os.makedirs(os.path.dirname(UPLOAD_META_FILE), exist_ok=True)
        with open(UPLOAD_META_FILE, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print('Erro ao salvar metadados de upload:', e)
        return False

# Inicializar banco na primeira execução (dentro do contexto da app)
with app.app_context():
    db.create_all()
    # Criar admin padrão se não houver nenhum usuário
    if User.query.count() == 0:
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin'),
            role='admin',
            is_first_login=True
        )
        db.session.add(admin)
        db.session.commit()
        print('[OK] Usuário admin criado (usuário: admin, senha: admin)')
    else:
        print('[OK] Banco de usuários carregado')

ALLOWED = {'.xlsx', '.xls', '.csv'}

def allowed(name):
    return os.path.splitext(name)[1].lower() in ALLOWED

def init_db():
    """Inicializa banco e cria admin padrão se não existir."""
    with app.app_context():
        db.create_all()
        # Criar admin padrão se não existir
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin'),
                role='admin',
                is_first_login=True
            )
            db.session.add(admin)
            db.session.commit()
            print('[OK] Usuário admin criado (senha: admin)')
        else:
            print('[OK] Usuário admin já existe')

def get_current_user():
    """Retorna o usuário da sessão atual."""
    if 'username' not in session:
        return None
    return User.query.filter_by(username=session['username']).first()

def require_auth(roles=None):
    """Decorator para exigir autenticação e opcionalmente permissões."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Não autorizado'}), 401
            if roles and user.role not in roles:
                return jsonify({'error': 'Permissão insuficiente'}), 403
            return f(user, *args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

@app.route('/')
def index():
    """Serve o index.html estático com login."""
    return send_from_directory(ROOT_DIR, 'index.html')


# ============ ENDPOINTS DE AUTENTICAÇÃO ============

@app.route('/api/login', methods=['POST'])
def login():
    """Login do usuário."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados não fornecidos'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Usuário e senha são obrigatórios'}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    if not user.check_password(password):
        return jsonify({'error': 'Senha incorreta'}), 401

    # Login OK - criar sessão
    session['username'] = user.username
    session.permanent = True  # Usa configuração de PERMANENT_SESSION_LIFETIME

    return jsonify({
        'ok': True,
        'user': user.to_dict(),
        'message': 'Login OK'
    })

@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout do usuário."""
    session.clear()
    return jsonify({'ok': True, 'message': 'Logout OK'})

@app.route('/api/me', methods=['GET'])
def me():
    """Retorna dados do usuário atual."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Não autorizado'}), 401
    return jsonify({'user': user.to_dict()})


# ============ ENDPOINTS DE GESTÃO DE USUÁRIOS ============

@app.route('/api/users', methods=['GET'])
@require_auth(roles=['admin'])
def list_users(current_user):
    """Lista todos os usuários (admin only)."""
    users = User.query.all()
    return jsonify({
        'users': [u.to_dict() for u in users]
    })


@app.route('/api/users', methods=['POST'])
@require_auth(roles=['admin'])
def create_user(current_user):
    """Cria novo usuário (admin only)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados não fornecidos'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'viewer')

    # Validações
    if not username or len(username) < 2:
        return jsonify({'error': 'Nome de usuário deve ter pelo menos 2 caracteres'}), 400
    if not password or len(password) < 3:
        return jsonify({'error': 'Senha deve ter pelo menos 3 caracteres'}), 400
    if role not in User.ROLES:
        return jsonify({'error': f'Papel inválido. Use: {User.ROLES}'}), 400

    # Verificar se já existe
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Usuário já existe'}), 409

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role=role,
        is_first_login=True
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'ok': True,
        'user': user.to_dict(),
        'message': f'Usuário {username} criado'
    })


@app.route('/api/users/<username>/role', methods=['PUT'])
@require_auth(roles=['admin'])
def change_user_role(current_user, username):
    """Altera papel de um usuário."""
    if username == 'admin':
        return jsonify({'error': 'Não pode alterar papel do admin'}), 403

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    data = request.get_json()
    new_role = data.get('role')
    if new_role not in User.ROLES:
        return jsonify({'error': f'Papel inválido. Use: {User.ROLES}'}), 400

    user.role = new_role
    db.session.commit()

    return jsonify({
        'ok': True,
        'user': user.to_dict(),
        'message': f'Papel de {username} alterado para {new_role}'
    })


@app.route('/api/users/<username>/password', methods=['PUT'])
@require_auth()
def change_user_password(current_user, username):
    """Altera senha de um usuário."""
    # Admin pode resetar qualquer senha, usuário só a sua própria
    if current_user.username != username and current_user.role != 'admin':
        return jsonify({'error': 'Sem permissão'}), 403

    data = request.get_json()
    new_password = data.get('password', '').strip()
    if not new_password or len(new_password) < 3:
        return jsonify({'error': 'Senha inválida'}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    user.password_hash = generate_password_hash(new_password)
    user.is_first_login = False
    db.session.commit()

    return jsonify({
        'ok': True,
        'message': f'Senha de {username} atualizada'
    })


@app.route('/api/users/<username>', methods=['DELETE'])
@require_auth(roles=['admin'])
def delete_user(current_user, username):
    """Remove um usuário."""
    if username == 'admin':
        return jsonify({'error': 'Não pode remover admin'}), 403

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({
        'ok': True,
        'message': f'Usuário {username} removido'
    })


@app.route('/api/users/<username>/first-login', methods=['POST'])
def first_login_change_password(username):
    """Altera senha no primeiro acesso (usuário pode fazer sem estar autenticado previamente)."""
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    if not user.is_first_login:
        return jsonify({'error': 'Primeiro login já foi realizado'}), 400

    data = request.get_json()
    new_password = data.get('password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()

    if not new_password or not confirm_password:
        return jsonify({'error': 'Senhas são obrigatórias'}), 400
    if new_password != confirm_password:
        return jsonify({'error': 'Senhas não coincidem'}), 400
    if len(new_password) < 6:
        return jsonify({'error': 'Senha deve ter pelo menos 6 caracteres'}), 400
    if not any(c.isupper() for c in new_password):
        return jsonify({'error': 'Senha deve ter pelo menos uma letra maiúscula'}), 400
    if not any(c.isdigit() for c in new_password):
        return jsonify({'error': 'Senha deve ter pelo menos um número'}), 400
    # Verifica se contém o username
    if username.lower() in new_password.lower():
        return jsonify({'error': 'Senha não pode conter seu nome de usuário'}), 400

    user.password_hash = generate_password_hash(new_password)
    user.is_first_login = False
    db.session.commit()

    # Auto-login após mudança
    session['username'] = user.username
    session.permanent = True

    return jsonify({
        'ok': True,
        'user': user.to_dict(),
        'message': 'Senha alterada com sucesso'
    })


@app.route('/upload', methods=['POST'])
def upload():
    """Recebe .xlsx via POST (multipart/form-data)."""
    # Verificar autenticação
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Não autorizado. Faça login primeiro.'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['file']
    if not file.filename or file.filename == '':
        return jsonify({'error': 'Nome de arquivo vazio'}), 400

    if not allowed(file.filename):
        return jsonify({'error': 'Formato não suportado. Envie .xlsx ou .xls'}), 400

    fname = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], fname)

    # Sobrescrever se já existir
    file.save(path)

    # Salvar metadado de upload
    meta = load_upload_meta()
    label = os.path.splitext(fname)[0].upper()
    meta[label] = {'uploadedBy': user.username, 'uploadedAt': datetime.datetime.utcnow().isoformat()}
    save_upload_meta(meta)

    # Persistência adicional: gravar upload em CSV
    log_csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'upload_log.csv')
    append_csv(log_csv_path, [fname, user.username, datetime.datetime.utcnow().isoformat()], header=not os.path.exists(log_csv_path))

    # Parse e retorna dados
    transactions, summary = parse_xlsx(path)
    kpis = compute_kpis(transactions, label)

    from app.gerar_dashboard import MONTH_NAMES
    display = MONTH_NAMES.get(label, label)
    kpis['display'] = display

    data = {
        'meta': {'display': display, 'file': fname, 'uploadedBy': user.username},
        'kpi': kpis,
        'transactions': transactions,
        'summary': summary,
    }

    return jsonify({
        'ok': True,
        'month': label,
        'data': data,
        'message': f'{display} importado com sucesso — {len(transactions)} transacoes'
    })


@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Remove um arquivo de dados."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Não autorizado'}), 401

    # Verifica permissão: só admin pode deletar (por enquanto)
    if user.role != 'admin':
        return jsonify({'error': 'Sem permissão'}), 403

    path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if os.path.exists(path):
        os.remove(path)
        # Remover metadado de upload
        meta = load_upload_meta()
        label = os.path.splitext(filename)[0].upper()
        if label in meta:
            del meta[label]
            save_upload_meta(meta)
        return jsonify({'ok': True, 'message': 'Arquivo removido'})
    return jsonify({'error': 'Arquivo não encontrado'}), 404


@app.route('/api/data')
def api_data():
    """Dados completos em JSON, com uploader."""
    base = app.config['UPLOAD_FOLDER']
    if not os.path.isdir(base):
        return jsonify({})
    months = load_all_data(base)
    # Adicionar uploadedBy de cada mês
    upload_meta = load_upload_meta()
    for key, data in months.items():
        if key in upload_meta:
            data['meta']['uploadedBy'] = upload_meta[key].get('uploadedBy')
        else:
            data['meta']['uploadedBy'] = None
    return jsonify(months)


@app.route('/api/annual')
def api_annual():
    """Dados agregados por mês para gráfico anual."""
    base = app.config['UPLOAD_FOLDER']
    if not os.path.isdir(base):
        return jsonify({'months': [], 'sellers': {}})

    months = load_all_data(base)
    chart_data = []
    all_sellers = {}

    MONTH_ORDER = [
        'JANEIRO', 'FEVEREIRO', 'MARCO', 'ABRIL', 'MAIO', 'JUNHO',
        'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'
    ]

    sorted_keys = sorted(months.keys(), key=lambda k: MONTH_ORDER.index(k) if k in MONTH_ORDER else 99)

    for key in sorted_keys:
        m = months[key]
        k = m.get('kpi', {})
        chart_data.append({
            'month': key,
            'display': k.get('display', key),
            'total': k.get('total', 0),
            'taxas': k.get('taxas', 0),
            'liquido': k.get('liquido', 0),
            'comissoes': k.get('comissoes', 0),
            'pagos': k.get('pagos', 0),
            'pendentes': k.get('pendentes', 0),
            'vendas_total': k.get('pagos', 0) + k.get('pendentes', 0),
        })
        for seller, sv in k.get('vendedores', {}).items():
            if seller not in all_sellers:
                all_sellers[seller] = {}
            all_sellers[seller][key] = sv.get('total', 0)

    return jsonify({'months': chart_data, 'sellers': all_sellers})


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    print('Dashboard Agencia — http://localhost:' + str(port))
    print('Pasta de dados: ' + app.config['UPLOAD_FOLDER'])
    app.run(debug=True, host='0.0.0.0', port=port)