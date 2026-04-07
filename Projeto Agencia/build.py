"""
Lê app/gerar_dashboard.py (dados), templates/dashboard.html (estrutura),
static/style.css e static/script.js — monta o dashboard final.
"""
import os, json


def build_all(months_data, project_dir=None):
    if project_dir is None:
        project_dir = os.path.dirname(os.path.abspath(__file__))

    # Read template
    tpl_path = os.path.join(project_dir, 'templates', 'dashboard.html')
    with open(tpl_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Read CSS
    css_path = os.path.join(project_dir, 'static', 'style.css')
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()

    # Read JS
    js_path = os.path.join(project_dir, 'static', 'script.js')
    with open(js_path, 'r', encoding='utf-8') as f:
        js = f.read()

    # Serialize data
    data_json = json.dumps(months_data, ensure_ascii=False)

    # Replace placeholders
    html = html.replace('{{CSS}}', css)
    html = html.replace('{{JS}}', js)
    html = html.replace('{{DATA}}', data_json)

    # Write final output
    output_path = os.path.join(project_dir, 'dashboard.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_path
