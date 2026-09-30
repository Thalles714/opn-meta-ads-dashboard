"""Importação manual de exportações Meta da OPN. Sem dependências externas."""
import argparse
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / 'dashboard/private'
PUBLIC = ROOT / 'dashboard/public'
SCHEMA = 2
FIELDS = {
    'spend': ('Valor gasto (BRL)', True),
    'impressions': ('Impressões', False),
    'link_clicks': ('Cliques no link', False),
    'landing_page_views': ('Visualizações da página de destino', False),
    'conversations': ('Conversas por mensagem iniciadas', False),
    'profile_visits': ('Visitas ao perfil do Instagram', False),
    'purchases': ('Compras', False),
    'purchase_value': ('Valor de conversão da compra', True),
    'lead_motor': ('site - lead (clicou motor reserva)', False),
    'lead_whats': ('site - lead (clicou whats)', False),
}
IDS = {'campaign': 'Identificação da campanha', 'adset': 'Identificação do conjunto de anúncios', 'ad': 'Identificação do anúncio'}
NAMES = {'campaign': 'Nome da campanha', 'adset': 'Nome do conjunto de anúncios', 'ad': 'Nome do anúncio'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def load_csv(path):
    raw = path.read_bytes()
    for encoding in ('utf-8-sig', 'cp1252'):
        try:
            content = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f'{path}: codificação não reconhecida')
    sample = content[:4096]
    dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
    reader = csv.DictReader(content.splitlines(), dialect=dialect)
    if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
        raise ValueError(f'{path}: cabeçalhos duplicados')
    return list(reader), hashlib.sha256(raw).hexdigest(), encoding


def number(value, money, line, field):
    if value is None or not value.strip() or value.strip() in ('–', '—', 'N/A'):
        return None
    s = value.strip().replace('\u00a0', '').replace(' ', '')
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        n = Decimal(s)
    except InvalidOperation:
        raise ValueError(f'linha {line}: {field} inválido: {value!r}')
    if not n.is_finite() or n < 0:
        raise ValueError(f'linha {line}: {field} deve ser finito e não negativo')
    if money:
        if n.as_tuple().exponent < -2:
            raise ValueError(f'linha {line}: {field} tem mais de dois centavos')
        return int(n * 100)
    if n != n.to_integral_value():
        raise ValueError(f'linha {line}: {field} deve ser inteiro')
    return int(n)


def parse(rows, since, until):
    required = {'Início dos relatórios', 'Encerramento dos relatórios', 'Indicador de resultados', 'Resultados', 'Configuração de atribuição'} | set(IDS.values()) | set(NAMES.values()) | {v[0] for v in FIELDS.values()}
    if not rows:
        raise ValueError('exportação vazia')
    missing = required - set(rows[0])
    if missing:
        raise ValueError('colunas ausentes: ' + ', '.join(sorted(missing)))
    output = {}
    hierarchy = {'ad': {}, 'adset': {}}
    duplicates = 0
    for line, source in enumerate(rows, 2):
        try:
            day = date.fromisoformat(source['Início dos relatórios'])
            end = date.fromisoformat(source['Encerramento dos relatórios'])
        except ValueError:
            raise ValueError(f'linha {line}: data inválida')
        if day != end:
            raise ValueError(f'linha {line}: detalhamento não diário ou grão ambíguo')
        if not (since <= day <= until):
            raise ValueError(f'linha {line}: data fora do escopo declarado')
        ids = {key: source[column].strip() for key, column in IDS.items()}
        if any(not value or not value.isdecimal() for value in ids.values()):
            raise ValueError(f'linha {line}: IDs ausentes ou inválidos')
        for child, parent in (('ad', 'adset'), ('adset', 'campaign')):
            previous = hierarchy[child].setdefault(ids[child], ids[parent])
            if previous != ids[parent]:
                raise ValueError(f'linha {line}: hierarquia conflitante para {child} {ids[child]}')
        metrics = {key: number(source[column], money, line, column) for key, (column, money) in FIELDS.items()}
        record = {'date': day.isoformat(), **{k+'_id': v for k,v in ids.items()}, **{k+'_name': source[col].strip() for k,col in NAMES.items()},
                  'result_indicator': source['Indicador de resultados'].strip() or None,
                  'results': number(source['Resultados'], False, line, 'Resultados'),
                  'attribution': source['Configuração de atribuição'].strip() or None, **metrics}
        key = f"{record['date']}|{ids['ad']}"
        if key in output:
            if output[key] != record:
                raise ValueError(f'linha {line}: chave diária conflitante {key}')
            duplicates += 1
        output[key] = record
    return output, duplicates


def sums(records):
    result = {}
    for field in FIELDS:
        values = [r[field] for r in records if r[field] is not None]
        result[field] = sum(values) if values else None
    return result


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')), encoding='utf-8')
    os.replace(temporary, path)


def merge_records(old, incoming, since, until, mode):
    if mode not in ('complete', 'partial'):
        raise ValueError('modo deve ser complete ou partial')
    merged = {key:record for key,record in old.items() if mode == 'partial' or not (since <= record['date'] <= until)}
    merged.update(incoming)
    return merged


def public_data(records, manifest):
    records = sorted(records, key=lambda r: (r['date'], r['ad_id']))
    ids = {kind: sorted({r[kind+'_id'] for r in records}) for kind in IDS}
    prefix = {'campaign':'C','adset':'S','ad':'A'}
    codes = {kind: {raw: f'{prefix[kind]}{hashlib.sha256(raw.encode()).hexdigest()[:8].upper()}' for raw in items} for kind, items in ids.items()}
    # Nomes são rótulos editáveis: escolha o último nome preenchido de cada ID.
    labels = {kind: {} for kind in IDS}
    for r in records:
        for kind in IDS:
            name = r[kind+'_name']
            if name:
                labels[kind][codes[kind][r[kind+'_id']]] = name
    public_rows = []
    for r in records:
        public_rows.append({'d': r['date'], 'c': codes['campaign'][r['campaign_id']], 's': codes['adset'][r['adset_id']], 'a': codes['ad'][r['ad_id']],
                            't': r['result_indicator'], 'at': r['attribution'], **{key: r[key] for key in FIELDS}})
    catalog = {kind: {codes[kind][raw]: labels[kind].get(codes[kind][raw], codes[kind][raw]) for raw in ids[kind]} for kind in IDS}
    build_id = digest({'schema': SCHEMA, 'data_hash': manifest['data_hash'], 'catalog': catalog})[:12]
    return {'schema': SCHEMA, 'data_hash': manifest['data_hash'], 'build_id': build_id, 'catalog': catalog,
            'source_export_time': manifest['source_export_time'], 'import_time': manifest['import_time'],
            'period': manifest['period'], 'timezone': 'America/Sao_Paulo', 'rows': public_rows,
            'coverage': {'campaigns': len(ids['campaign']), 'adsets': len(ids['adset']), 'ads': len(ids['ad']),
                         'daily_rows': len(records), 'ui_campaigns_observed': 60, 'ui_ads_observed': 103,
                         'inventory_campaigns_exported': 31}}


def run(args):
    since, until = date.fromisoformat(args.since), date.fromisoformat(args.until)
    if since > until:
        raise ValueError('período inicial posterior ao final')
    rows, file_hash, encoding = load_csv(Path(args.input))
    incoming, duplicates = parse(rows, since, until)
    snapshot_path = PRIVATE / 'snapshot.json'
    existing = json.loads(snapshot_path.read_text(encoding='utf-8')) if snapshot_path.exists() else {'rows': []}
    old = {f"{r['date']}|{r['ad_id']}": r for r in existing['rows']}
    merged = merge_records(old, incoming, args.since, args.until, args.mode)
    added = sum(key not in old for key in merged)
    revised = sum(key in old and old[key] != record for key, record in merged.items())
    removed = sum(key not in merged for key in old)
    normalized = sorted(merged.values(), key=lambda r: (r['date'], r['ad_id']))
    data_hash = digest(normalized)
    counts = {kind+'s': len({r[kind+'_id'] for r in normalized}) for kind in IDS}
    manifest = {'schema': SCHEMA, 'data_hash': data_hash, 'input_filename': Path(args.input).name,
                'input_sha256': file_hash, 'encoding': encoding, 'source_export_time': args.export_time,
                'import_time': datetime.now(timezone.utc).isoformat(), 'period': {'since': args.since, 'until': args.until},
                'mode': args.mode, 'account_scope': 'OPN single account', 'source_rows': len(rows),
                'duplicate_rows': duplicates, 'snapshot_rows': len(normalized), **counts,
                'changes': {'added': added, 'revised': revised, 'removed': removed},
                'totals': sums(normalized), 'previous_totals': sums(old.values()), 'validation': 'passed'}
    atomic_json(snapshot_path, {'schema': SCHEMA, 'rows': normalized})
    atomic_json(PRIVATE / 'manifest.json', manifest)
    atomic_json(PUBLIC / 'data.json', public_data(normalized, manifest))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--since', required=True)
    parser.add_argument('--until', required=True)
    parser.add_argument('--mode', choices=('complete', 'partial'), required=True)
    parser.add_argument('--export-time', default=None, help='ISO 8601, se conhecido')
    run(parser.parse_args())
