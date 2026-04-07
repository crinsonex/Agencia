"""
Servidor Flask do dashboard da agencia.
- GET /          → Dashboard completo
- POST /upload   → Upload de arquivo .xlsx
- DELETE /api/files/<name> → Remove um arquivo
- GET /api/data  → Dados em JSON (para charts)
"""
from flask import Flask, request, jsonify, render_template
import os, json, shutil
from werkzeug.utils import secure_filename

# Adiciona a raiz do projeto ao path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.gerar_dashboard import load_all_data, compute_kpis, parse_xlsx

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

ALLOWED = {'.xlsx', '.xls', '.csv'}


def allowed(name):
    return os.path.splitext(name)[1].lower() in ALLOWED


@app.route('/')
def index():
    """Dashboard principal com upload integrado."""
    base = app.config['UPLOAD_FOLDER']
    if not os.path.isdir(base):
        os.makedirs(base, exist_ok=True)

    months = load_all_data(base) if os.listdir(base) else {}

    # Build the data JSON for the frontend
    data_json = json.dumps(months, ensure_ascii=False)

    return render_template('dashboard.html',
                           DATA=data_json,
                           files=list(months.keys()),
                           total_months=len(months))


@app.route('/upload', methods=['POST'])
def upload():
    """Recebe .xlsx via POST (multipart/form-data)."""
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['file']
    if not file.filename or file.filename == '':
        return jsonify({'error': 'Nome de arquivo vazio'}), 400

    if not allowed(file.filename):
        return jsonify({'error': 'Formato nao suportado. Envie .xlsx ou .xls'}), 400

    fname = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], fname)

    # Overwrite if exists
    file.save(path)

    # Parse and return data
    label = os.path.splitext(fname)[0].upper()
    transactions, summary = parse_xlsx(path)
    kpis = compute_kpis(transactions, label)

    from app.gerar_dashboard import MONTH_NAMES
    display = MONTH_NAMES.get(label, label)
    kpis['display'] = display

    data = {
        'meta': {'display': display, 'file': fname},
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
    path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if os.path.exists(path):
        os.remove(path)
        return jsonify({'ok': True, 'message': 'Arquivo removido'})
    return jsonify({'error': 'Arquivo nao encontrado'}), 404


@app.route('/api/data')
def api_data():
    """Dados completos em JSON."""
    base = app.config['UPLOAD_FOLDER']
    if not os.path.isdir(base):
        return jsonify({})
    months = load_all_data(base)
    return jsonify(months)


@app.route('/api/annual')
def api_annual():
    """Dados agregados por mes para grafico anual."""
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
