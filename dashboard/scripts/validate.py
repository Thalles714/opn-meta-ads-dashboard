"""Conferências do snapshot privado, dataset público e exportação por campanha."""
import json
from collections import Counter
from pathlib import Path
from pipeline import ROOT, PRIVATE, PUBLIC, FIELDS, load_csv, number, sums, digest

snapshot = json.loads((PRIVATE/'snapshot.json').read_text(encoding='utf-8'))['rows']
manifest = json.loads((PRIVATE/'manifest.json').read_text(encoding='utf-8'))
public = json.loads((PUBLIC/'data.json').read_text(encoding='utf-8'))
assert digest(snapshot) == manifest['data_hash'] == public['data_hash']
assert len(snapshot) == len(public['rows'])
assert len({(r['date'],r['ad_id']) for r in snapshot}) == len(snapshot)
assert sums(snapshot) == manifest['totals'] == sums(public['rows'])
assert all(not any(k.endswith('_name') or k.endswith('_id') for k in r) for r in public['rows'])

campaign_file = ROOT/'data/raw/meta/2026-01-01_2026-09-29_campaigns_daily.csv'
campaign_rows, _, _ = load_csv(campaign_file)
mapping = {key:column for key,(column,_) in FIELDS.items() if column in campaign_rows[0]}
campaign_totals = {}
for key,column in mapping.items():
    vals = [number(r[column], FIELDS[key][1], i, column) for i,r in enumerate(campaign_rows,2)]
    campaign_totals[key] = sum(v for v in vals if v is not None) if any(v is not None for v in vals) else None

inventory_rows,_,_=load_csv(ROOT/'data/raw/meta/2026-01-01_2026-09-29_campaigns_including_deleted.csv')
inventory_ids={r['Identificação da campanha'] for r in inventory_rows}
daily_ids={r['campaign_id'] for r in snapshot}
report={'source_rows':len(snapshot),'source_distinct':{'campaigns':len(daily_ids),'adsets':len({r['adset_id'] for r in snapshot}),'ads':len({r['ad_id'] for r in snapshot})},
        'campaign_daily_rows':len(campaign_rows),'campaign_daily_distinct':len({r['Identificação da campanha'] for r in campaign_rows}),
        'inventory_distinct':len(inventory_ids),'inventory_only_ids_count':len(inventory_ids-daily_ids),
        'daily_only_ids_count':len(daily_ids-inventory_ids),
        'campaign_comparison':{key:{'ad_level':manifest['totals'][key],'campaign_level':v,'difference':None if v is None or manifest['totals'][key] is None else v-manifest['totals'][key]} for key,v in campaign_totals.items()},
        'data_hash':manifest['data_hash'],'validated':'passed'}
print(json.dumps(report,ensure_ascii=False,indent=2))
