"""Download public Hyperliquid metadata and Anthropic OHLCV; no credentials needed."""
import concurrent.futures as cf
import csv
import datetime as dt
import json
from pathlib import Path
import requests

OUT = Path('data')
OUT.mkdir(exist_ok=True)
URL = 'https://api.hyperliquid.xyz/info'

def info(payload):
    r = requests.post(URL, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2), encoding='utf-8')

def iso(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).isoformat()

def main():
    now = dt.datetime.now(dt.timezone.utc)
    end = int(now.timestamp()*1000)
    dexes = info({'type':'perpDexs'})
    save('perp_dexes.json', dexes)
    names = [''] + [x['name'] for x in dexes if x]
    def metadata(dex):
        return dex, info({'type':'metaAndAssetCtxs', 'dex':dex})
    all_meta = dict(cf.ThreadPoolExecutor(max_workers=4).map(metadata, names))
    save('all_metadata.json', all_meta)
    matches = []
    for dex, (meta, contexts) in all_meta.items():
        print('DEX', dex or '(native)', 'assets', len(meta['universe']))
        for market, ctx in zip(meta['universe'], contexts):
            if any(s in market['name'].upper() for s in ('ANTH','CLAUDE')) or market['name'].split(':')[-1] == 'ANT':
                item = {'dex':dex, 'market':market, 'context':ctx, 'observed_at':now.isoformat()}
                matches.append(item)
                print(json.dumps(item))
    save('snapshot.json', matches)
    def candles(item):
        coin = item['market']['name']
        for interval in ('1d','1h'):
            rows = info({'type':'candleSnapshot','req':{'coin':coin,'interval':interval,'startTime':0,'endTime':end}})
            rows.sort(key=lambda x:x['t'])
            name = coin.replace(':','_')+'_'+interval
            save(name+'.json',rows)
            with (OUT/(name+'.csv')).open('w',newline='',encoding='utf-8') as f:
                w=csv.writer(f)
                w.writerow(['time_utc','end_utc','open','high','low','close','volume_contract_units','trades'])
                for x in rows:
                    w.writerow([iso(x['t']),iso(x['T']),x['o'],x['h'],x['l'],x['c'],x['v'],x['n']])
            print(coin,interval,len(rows),'first',iso(rows[0]['t']) if rows else None,'last',iso(rows[-1]['t']) if rows else None)
    list(cf.ThreadPoolExecutor(max_workers=4).map(candles,matches))

if __name__ == '__main__':
    main()
