"""
Gera dashboard a partir dos arquivos xlsx da agencia.
Módulo principal — le os dados e monta os KPIs.
Dependência: pip install pandas openpyxl
"""

import pandas as pd
import os, glob, json, re

MONTH_NAMES = {
    'JANEIRO': 'Janeiro', 'FEVEREIRO': 'Fevereiro', 'MARCO': 'Marco',
    'ABRIL': 'Abril', 'MAIO': 'Maio', 'JUNHO': 'Junho',
    'JULHO': 'Julho', 'AGOSTO': 'Agosto', 'SETEMBRO': 'Setembro',
    'OUTUBRO': 'Outubro', 'NOVEMBRO': 'Novembro', 'DEZEMBRO': 'Dezembro',
}


def _money(val):
    """Converte valor da planilha para float. NaN → 0."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace('R$', '').replace('.', '').replace(',', '.').strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _parse_csv_text(path):
    """
    CSV desorganizado — pode vir tudo em uma única coluna:
    - Linhas com '2447758 Giulia  RES329488PAGO  R$ 13.899,98 ...'
    - Linhas quebradas: '2430459 Giulia  RES051439-' seguida de 'PAGO  R$ 6.882,29 ...'
    - Status grudado no produto
    - Seção de resumo/comissão separada
    """
    with open(path, 'r', encoding='utf-8-sig') as f:
        lines = f.read().splitlines()

    transactions = []
    summary = []
    pending_line = None  # guarda linha anterior incompleta (e.g., RES051439-)
    in_summary = False   # após a linha 'Comissão' tudo é resumo

    for raw_line in lines:
        line = raw_line.strip().strip('"').strip()
        if not line:
            continue

        if 'Comissão' in line or line.startswith('Obs.') or line.strip().startswith('\x0c'):
            in_summary = True
            summary.append(line)
            continue

        # Pular linha de cabeçalho (começa com 'Id')
        if line.lower().startswith('id'):
            continue

        # Quando a linha indica resumo ou nomes de colaboradores ou rótulos de R$
        if in_summary or line.startswith('R$') or line.startswith('Giulia') or line.startswith('Amanda') or line.startswith('Juliana') or line.startswith('Sofia') or line.startswith('723,') or line.startswith('(erro)'):
            summary.append(line)
            continue

        # Detectar continuação de linha quebrada (ex: PAGO, PENDENTE ou R$)
        line_stripped = line
        if pending_line is not None:
            # Junta linha pendente + linha atual
            line = pending_line + ' ' + line
            pending_line = None
            in_summary = False

        # Identificar ID no início
        cols = line.split()
        if not cols:
            continue

        first = cols[0]
        cleaned = first.replace('.', '').replace('-', '')
        is_id = (re.match(r'^[A-Z]*\d{5,}$', cleaned)
                 or re.match(r'^[A-Z]{3,}$', cleaned))

        if not is_id:
            summary.append(line)
            continue

        # Remover o nome (segundo token)
        rest = line
        rest = rest[len(first):].strip()
        parts = rest.split(None, 1)
        if not parts:
            continue
        nome = parts[0].strip()
        rest = parts[1] if len(parts) > 1 else ''

        # Status pode estar grudado no produto
        status = ''
        for kw in ['PAGO', 'PENDENTE']:
            if kw in rest:
                status = kw
                rest = rest.replace(kw, '', 1)
                break

        # Verificar se a linha não tem valores monetários — provavelmente está quebrada
        has_money = re.search(r'R\$', rest)
        if not has_money and rest.strip().endswith('-'):
            pending_line = line
            continue

        # Extrair todos os valores monetários
        money_vals = re.findall(r'R\$\s*[\d.,]+', rest)

        # Nome do produto = texto antes do primeiro R$
        r_match = re.search(r'R\$', rest)
        produto = rest[:r_match.start()].strip() if r_match else rest.strip()

        t = {
            'id': first,
            'nome': nome,
            'produto': produto,
            'status': status,
            'total': _money(money_vals[0]) if len(money_vals) > 0 else 0.0,
            'taxa': _money(money_vals[1]) if len(money_vals) > 1 else 0.0,
            'liquido': _money(money_vals[2]) if len(money_vals) > 2 else 0.0,
            'comissao': 0.0,
            'obs': '',
        }
        transactions.append(t)

    return transactions, summary


def parse_xlsx(path):
    """
    Colunas do arquivo Excel:
      0=Id  1=Nome  2=Produto  3=Status  4=Total  5=Taxa  6=Total s/ taxas
      7=Comissao  8=Obs  9=Total(sum)  10=Total s/ taxas(sum)  11=A pagar
    """
    ext = os.path.splitext(path)[1].lower()

    # CSV: pode vir como coluna única com dados separados por múltiplos espaços
    if ext == '.csv':
        return _parse_csv_text(path)

    df = pd.read_excel(path, header=None)
    transactions = []
    summary = []

    for _, row in df.iterrows():
        if all(pd.isna(v) for v in row.values):
            continue

        vals = [v for v in row.values]
        first = str(vals[0]).strip() if pd.notna(vals[0]) else ''

        if 'Id' in first or 'id' in first:
            continue

        cleaned = first.replace('.', '').replace('-', '')
        is_id = (re.match(r'^[A-Z]*\d{5,}$', cleaned)
                 or re.match(r'^[A-Z]{3,}$', cleaned))

        if not is_id:
            parts = []
            for v in vals:
                if pd.notna(v):
                    parts.append(str(v).strip())
            summary.append(' | '.join(parts))
            continue

        status = str(vals[3]).strip() if len(vals) > 3 and pd.notna(vals[3]) else ''

        t = {
            'id': first,
            'nome': str(vals[1]).strip() if pd.notna(vals[1]) else '',
            'produto': str(vals[2]).strip() if pd.notna(vals[2]) else '',
            'status': status,
            'total': _money(vals[4]) if len(vals) > 4 else 0.0,
            'taxa': _money(vals[5]) if len(vals) > 5 else 0.0,
            'liquido': _money(vals[6]) if len(vals) > 6 else 0.0,
            'comissao': _money(vals[7]) if len(vals) > 7 else 0.0,
            'obs': str(vals[8]).strip() if len(vals) > 8 and pd.notna(vals[8]) else '',
        }
        transactions.append(t)

        total_ag = _money(vals[9]) if len(vals) > 9 else 0
        a_pagar = _money(vals[11]) if len(vals) > 11 else 0
        obs_text = t['obs']
        if obs_text or total_ag > 0 or a_pagar > 0:
            parts = []
            if obs_text:
                parts.append(obs_text)
            if total_ag > 0:
                parts.append(f"Total agencia: R$ {total_ag:,.2f}")
            if a_pagar > 0:
                parts.append(f"A pagar: R$ {a_pagar:,.2f}")
            if parts:
                summary.append(f"[{t['nome']}] " + ' | '.join(parts))

    return transactions, summary


def compute_kpis(transactions, month_name=''):
    kpis = {
        'total': 0.0, 'taxas': 0.0, 'liquido': 0.0,
        'comissoes': 0.0, 'pagos': 0, 'pendentes': 0,
        'display': month_name,
        'vendedores': {}, 'produtos': {},
    }
    for t in transactions:
        tt = t['total']; tx = t['taxa']; ll = t['liquido']
        kpis['total'] += tt
        kpis['taxas'] += tx
        kpis['liquido'] += ll
        kpis['comissoes'] += t.get('comissao', 0)

        st = t.get('status', '').upper()
        if 'PAGO' in st:
            kpis['pagos'] += 1
        elif 'PENDENTE' in st:
            kpis['pendentes'] += 1

        nome = t['nome']
        if nome:
            if nome not in kpis['vendedores']:
                kpis['vendedores'][nome] = {
                    'total': 0, 'taxas': 0, 'liquido': 0,
                    'comissao': 0, 'count': 0, 'pagos': 0, 'pendentes': 0,
                }
            v = kpis['vendedores'][nome]
            v['total'] += tt; v['taxas'] += tx; v['liquido'] += ll
            v['comissao'] += t.get('comissao', 0)
            v['count'] += 1
            if 'PAGO' in st:
                v['pagos'] += 1
            elif 'PENDENTE' in st:
                v['pendentes'] += 1

        prod = t['produto'] or 'N/A'
        if len(prod) > 40:
            prod = prod[:37] + '...'
        kpis['produtos'][prod] = kpis['produtos'].get(prod, 0) + tt

    return kpis


def load_all_data(base_dir=None):
    """Varre pasta por arquivos de dados (.xlsx, .xls, .csv)."""
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dados')
        if not os.path.isdir(base_dir):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    months = {}
    patterns = ['*.xlsx', '*.xls', '*.csv']
    files = []
    for p in patterns:
        files.extend(glob.glob(os.path.join(base_dir, p)))

    for path in sorted(set(files)):
        label = os.path.splitext(os.path.basename(path))[0].upper()
        display = MONTH_NAMES.get(label, label)
        transactions, summary = parse_xlsx(path)
        kpis = compute_kpis(transactions, display)

        months[label] = {
            'meta': {'display': display, 'file': os.path.basename(path)},
            'kpi': kpis,
            'transactions': transactions,
            'summary': summary,
        }
    return months


if __name__ == '__main__':
    # Import do builder apenas quando rodado diretamente
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from build import build_all

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    months = load_all_data(base)

    if not months:
        print('Nenhum arquivo .xlsx encontrado.')
    else:
        output = build_all(months, base)
        print(f'Dashboard gerado: {output}')
        for label, data in months.items():
            k = data['kpi']
            print(f"  {k['display']}: {len(data['transactions'])} transacoes | "
                  f"Bruto: R$ {k['total']:,.2f} | Liquido: R$ {k['liquido']:,.2f} | "
                  f"Pagos: {k['pagos']} | Pendentes: {k['pendentes']}")